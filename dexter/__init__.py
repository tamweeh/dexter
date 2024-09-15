import os

from .logger import get_logger
log = get_logger(log_name='init')
os.makedirs('logs', mode=0o777, exist_ok=True)
# os.makedirs('data', mode=0o777, exist_ok=True)

from . import utils
from . import logger
from . import models
from . import run
from . import parser
from . import producer

try:
    client = utils.redis_connection()
    if client.ping():
        log.info("Connected to Redis successfully!")
    client.set('test_key', 'Hello, Redis!')
    value = client.get('test_key')
    if value:
        log.info(f"Retrieved value: {value.decode('utf-8')}")
        client.delete('test_key')
        log.info("Key deleted successfully.")
except Exception as e:
    log.error(e)
    log.critical("Redis connection is needed to run this service")
    exit(1)

