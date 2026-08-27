"""Check dependencies and create or reset the resources used by the demo."""

import argparse
import time

from confluent_kafka import KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_DLQ_TOPIC,
    KAFKA_TOPIC,
    MONGODB_COLLECTION,
    MONGODB_DATABASE,
    MONGODB_URI,
)


TOPICS = ((KAFKA_TOPIC, 3), (KAFKA_DLQ_TOPIC, 1))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete and recreate only the workshop topics and orders collection",
    )
    return parser.parse_args()


def check_mongodb(reset: bool) -> None:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5_000)
    try:
        reply = client.admin.command("ping")
        if reply.get("ok") != 1.0:
            raise RuntimeError(f"Unexpected MongoDB ping response: {reply}")
        print("[ok] MongoDB is reachable")
        if reset:
            client[MONGODB_DATABASE][MONGODB_COLLECTION].drop()
            print(
                f"[reset] Dropped MongoDB collection "
                f"{MONGODB_DATABASE}.{MONGODB_COLLECTION}"
            )
    finally:
        client.close()


def wait_until_deleted(admin: AdminClient, topic: str, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if topic not in admin.list_topics(timeout=5).topics:
            return
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for Kafka topic {topic!r} to be deleted")


def wait_until_ready(
    admin: AdminClient, topic: str, expected_partitions: int, timeout: float = 15
) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        metadata = admin.list_topics(timeout=5)
        topic_metadata = metadata.topics.get(topic)
        if (
            topic_metadata is not None
            and topic_metadata.error is None
            and len(topic_metadata.partitions) == expected_partitions
        ):
            return len(topic_metadata.partitions)
        time.sleep(0.5)
    raise RuntimeError(
        f"Timed out waiting for Kafka topic {topic!r} "
        f"to have {expected_partitions} partitions"
    )


def prepare_kafka(reset: bool) -> None:
    admin = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
    metadata = admin.list_topics(timeout=5)

    if reset:
        existing = [topic for topic, _partitions in TOPICS if topic in metadata.topics]
        if existing:
            futures = admin.delete_topics(existing, operation_timeout=10)
            for topic, future in futures.items():
                future.result(timeout=10)
                wait_until_deleted(admin, topic)
                print(f"[reset] Deleted Kafka topic {topic!r}")
        metadata = admin.list_topics(timeout=5)

    missing = [
        NewTopic(topic, num_partitions=partitions, replication_factor=1)
        for topic, partitions in TOPICS
        if topic not in metadata.topics
    ]
    if missing:
        futures = admin.create_topics(missing)
        for topic, future in futures.items():
            future.result(timeout=10)
            partitions = next(count for name, count in TOPICS if name == topic)
            print(f"[ok] Created Kafka topic {topic!r} with {partitions} partitions")

    for topic, expected_partitions in TOPICS:
        actual_partitions = wait_until_ready(admin, topic, expected_partitions)
        print(f"[ok] Kafka topic {topic!r} is ready ({actual_partitions} partitions)")


def main() -> int:
    args = parse_args()
    try:
        check_mongodb(args.reset)
        prepare_kafka(args.reset)
    except (KafkaException, PyMongoError, RuntimeError) as error:
        print(f"[error] Demo setup failed: {error}")
        print("Start MongoDB and Kafka with the commands in README.md, then try again.")
        return 1

    print("[ready] The workshop demo is ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
