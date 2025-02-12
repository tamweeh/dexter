import json
from confluent_kafka import Producer

from dexter import get_logger
from dexter.utils import kafka_brokers

logger = get_logger(log_name=__name__.split('.')[-1])

conf = {
    'bootstrap.servers': kafka_brokers(),
    'compression.type': 'gzip'
}

headers = [
    ('producerid', 'dexter')
]

producer = Producer(conf)

def delivery_callback(err, msg):
    if err:
        logger.error(f"Message failed delivery: {err}")
    else:
        logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def send_message(topic, key, value):
    try:
        producer.produce(topic, key=key, value=json.dumps(value, ensure_ascii=False), headers=headers, callback=delivery_callback)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
    finally:
        producer.flush()
