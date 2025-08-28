import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import os

from lark.settings import IS_PROD
from util.log_util import logger

bootstrap_servers = ['b-1.cn-test-2.swcvvp.c2.kafka.cn-northwest-1.amazonaws.com.cn:9092',
                     'b-2.cn-test-2.swcvvp.c2.kafka.cn-northwest-1.amazonaws.com.cn:9092']
if IS_PROD:
    bootstrap_servers = ['b-2.us-prod-1.4obvix.c1.kafka.us-west-2.amazonaws.com:9092',
                         'b-1.us-prod-1.4obvix.c1.kafka.us-west-2.amazonaws.com:9092',
                         'b-3.us-prod-1.4obvix.c1.kafka.us-west-2.amazonaws.com:9092']
TOPIC_APPROVAL_EVENT = 'lark_approval_event'

# Initialize producer as None
producer = None

# Try to connect to Kafka, but don't fail if unavailable
try:
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=3
    )
    logger.info("Successfully connected to Kafka")
except Exception as e:
    logger.warning(f"Failed to connect to Kafka: {e}. Continuing without Kafka support.")

def on_send_success(record_metadata):
    logger.info('[kafka] send, topic: {}, partition: {}, offset: []'
                .format(record_metadata.topic, record_metadata.partition, record_metadata.offset))

def on_send_error(exception):
    logger.error('[kafka] send error: {}'.format(exception))

def produce_json(topic, dict_data, key=None):
    if producer is None:
        logger.warning("Kafka producer not available. Skipping message production.")
        return
        
    future = producer.send(topic, dict_data, key=bytes(key.encode('utf-8')) if key else None)
    try:
        record_metadata = future.get(timeout=10)
        on_send_success(record_metadata)
    except KafkaError as e:
        logger.error(f"Failed to send message to Kafka: {e}")
        on_send_error(e)

def consume_json(topic, group_id):
    if producer is None:
        logger.warning("Kafka consumer not available. Skipping message consumption.")
        return
        
    try:
        consumer = KafkaConsumer(
            topic, 
            group_id=group_id,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        for message in consumer:
            print("%s:%d:%d: key=%s value=%s" % (
                message.topic, message.partition,
                message.offset, message.key, message.value
            ))
    except Exception as e:
        logger.error(f"Failed to consume messages from Kafka: {e}")

if __name__ == '__main__':
    msg = {
        "uuid": "5f223b7d013a3e0fb248ae944e2610b6",
        "event": {
            "app_id": "cli_a0000e444df89014",
            "approval_code": "EC64F0BB-21AC-4033-AC88-3B007E4317BE",
            "generate_type": "",
            "instance_code": "7083A360-62BF-4DE9-B15D-E840AB753E77",
            "open_id": "ou_29b9ab6fb4b9810ca1ec3f56ec9c18c9",
            "operate_time": "1646107466794",
            "status": "PENDING",
            "task_id": "7069977736147763201",
            "tenant_key": "2c7e7fb8450f175e",
            "type": "approval_task",
            "user_id": "bge585f5"
        },
        "token": "LtYBwfDC04BwiQBqe66RebmVcWaTJ5u3",
        "ts": "555-123-4567.691036",
        "type": "event_callback"
    }
    print(msg)
    del msg['token']
    print(msg)

