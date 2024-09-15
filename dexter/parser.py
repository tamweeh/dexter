import pytz
from datetime import datetime as dt

from dexter.logger import get_logger
from dexter.models import UserData, AccountMention, Entities, PostData
from dexter.producer import send_message
from dexter.utils import get_timezone

logger = get_logger(log_name=__name__.split('.')[-1])
LOCAL_TIME = pytz.timezone(get_timezone())


def _convert_datetime(created_at: str) -> tuple[str, str]:
    utc_time = dt.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
    local_dt = utc_time.replace(tzinfo=pytz.utc).astimezone(LOCAL_TIME)
    return local_dt.strftime('%Y-%m-%d %H:%M:%S'), utc_time.strftime('%Y-%m-%d %H:%M:%S')


def _parse_posts(posts: list, rule: str, file_name: str = './data/parsed_tweets.jsonl'):
    for post in posts:
        if str(post.get('entryId', '')).startswith('tweet'):
            try:
                # Extract relevant parts of the tweet data
                result = post.get('content', {}).get('itemContent', {}).get('tweet_results', {}).get('result', {})
                post_content = result.get('tweet', {}) if result.get('__typename') == 'TweetWithVisibilityResults' else result
                legacy_data = post_content.get('legacy', {})

                # User details
                user_content = post_content.get('core', {}).get('user_results', {}).get('result', {}).get('legacy', {})
                user_data = UserData(
                    user_id=post_content.get('core', {}).get('user_results', {}).get('result', {}).get('rest_id', ''),
                    username=user_content.get('screen_name', ''),
                    display_name=user_content.get('name', ''),
                    followers=user_content.get('followers_count', 0),
                    verified=user_content.get('verified', False),
                    verified_type='none' if not user_content.get('verified') else 'blue',
                    posts_count=user_content.get('statuses_count', 0),
                    account_mentions=[
                        AccountMention(
                            username=mention.get('screen_name', ''),
                            display_name=mention.get('name', ''),
                            id_str=mention.get('id_str', '')
                        ) for mention in legacy_data.get('entities', {}).get('user_mentions', [])
                    ]
                )

                # Entities: hashtags, URLs, media
                entities = Entities(
                    hashtags=[hashtag.get('text') for hashtag in legacy_data.get('entities', {}).get('hashtags', [])],
                    urls=[url.get('expanded_url') for url in legacy_data.get('entities', {}).get('urls', [])],
                    media_urls=[media.get('media_url_https') for media in legacy_data.get('extended_entities', {}).get('media', [])]
                )

                # Post type logic
                post_type = (
                    'quoted' if legacy_data.get('is_quote_status', False)
                    else 'reply' if legacy_data.get('in_reply_to_status_id_str')
                    else 'retweet' if post_content.get('retweeted_status_result')
                    else 'post'
                )
                local_time, utc = _convert_datetime(legacy_data.get('created_at'))

                # Create a PostData model
                post_data = PostData(
                    posted_date_utc=utc,
                    post_id=legacy_data.get('id_str'),
                    text=legacy_data.get('full_text', ''),
                    local_posted=local_time,
                    post_type=post_type,
                    language=legacy_data.get('lang', 'en'),
                    likes=legacy_data.get('favorite_count', 0),
                    retweets=legacy_data.get('retweet_count', 0),
                    quotes=legacy_data.get('quote_count', 0),
                    conversation_id=legacy_data.get('conversation_id_str'),
                    user_data=user_data,
                    entities=entities,
                    rule=rule,
                    data_provider='dexter',
                    collection_time=dt.now().strftime('%Y-%m-%d_%H-%M-%S')
                )

                # send_message(topic='posts', key=post_data.language, value=post_data.model_dump())
                yield post_data
            except Exception as e:
                print(post)
                logger.error(f"{e}", exc_info=True)