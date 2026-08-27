"""Shared defaults for the workshop demo."""

import os


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "workshop-orders")
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", f"{KAFKA_TOPIC}-dlq")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "workshop-order-processor")

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true",
)
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "workshop")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "orders")

CUSTOMER_INDEX_NAME = "customer_id_1"
