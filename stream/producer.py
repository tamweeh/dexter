import json
from confluent_kafka import Producer

conf = {
    'bootstrap.servers': 'broker:29092',
    'compression.type': 'gzip'
}
headers = [
    ('producerid', 'dexter')
]

producer = Producer(conf)

def delivery_callback(err, msg):
    if err:
        print(f"Message failed delivery: {err}")
    # else:
    #     print(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

def produce_to_kafka(topic: str, data: dict, key: str):
    json_data = json.dumps(data, ensure_ascii=False)
    producer.produce(topic, value=json_data, key=key ,callback=delivery_callback, headers=headers)
    producer.flush()
