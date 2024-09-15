import pyfiglet
from termcolor import colored

from dexter import get_logger
from dexter.utils import user_credentials
from dexter.run import get_stream

logger = get_logger(log_name='main')

def welcome(username, font='starwars'):
    try:
        ascii_art = pyfiglet.figlet_format("DEXTER", font=font)
        colored_ascii = colored(ascii_art, color="yellow", attrs=["blink"])
        print(colored_ascii)
        user_message = f"User: {username}"
        colored_user = colored(user_message, color="yellow", attrs=["bold"])
        print(colored_user)
    except Exception as e:
        logger.error(f"Error displaying welcome message: {e}")

if __name__ == '__main__':
    try:
        USERNAME, PASSWORD, EMAIL = user_credentials()
        welcome(USERNAME)

        get_stream(user=USERNAME, password=PASSWORD, email=EMAIL)
    except Exception as e:
        logger.error(f"Error during execution: {e}")
