import os
import redis
from dotenv import load_dotenv
load_dotenv()

def get_timezone():
    return os.getenv('TZ')

def user_credentials():
    return os.getenv('X_USER'), os.getenv('X_PASSWORD'), os.getenv('X_EMAIL')

def x_api():
    return os.getenv('X_DECK')

def dexter_columns_host():
    return os.getenv('DEXTER_COLUMNS_HOST')

def redis_connection():
    return redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('REDIS_DB'))


def kafka_brokers():
    return os.getenv('KAFKA_BROKERS')