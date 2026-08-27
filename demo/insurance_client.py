"""A minimal Kafka-to-MongoDB insurance transaction client for Lab 1."""

import argparse
import json
import signal
import time
from datetime import datetime, timezone

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from pymongo import MongoClient
from pymongo.errors import PyMongoError


DEFAULT_TOPIC = "insurance-transactions-lab1"
DEFAULT_GROUP = "insurance-mongodb-writer-lab1"
DEFAULT_KAFKA = "localhost:9092"
DEFAULT_MONGODB = (
    "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"
)


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return number


def non_negative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value cannot be negative")
    return number


def build_transaction(number: int) -> dict:
    """Return a deterministic transaction so replay demonstrates an upsert."""
    transaction_types = ("premium.payment", "claim.payment", "refund.payment")
    return {
        "event_type": "insurance.transaction.recorded",
        "transaction_id": f"LAB1-TXN-{number:03d}",
        "policy_id": f"POL-{((number - 1) % 4) + 1001}",
        "customer_id": f"CUST-{((number - 1) % 6) + 501}",
        "transaction_type": transaction_types[(number - 1) % len(transaction_types)],
        "amount": round(75.0 + number * 19.25, 2),
        "currency": "USD",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def produce(args: argparse.Namespace) -> int:
    producer = Producer({"bootstrap.servers": args.bootstrap_servers})
    delivered = 0
    failed = 0

    def delivery_report(transaction_id: str):
        def report(error, message) -> None:
            nonlocal delivered, failed
            if error is not None:
                failed += 1
                print(f"[failed] transaction={transaction_id} error={error}")
                return
            delivered += 1
            print(
                f"[delivered] transaction={transaction_id} "
                f"partition={message.partition()} offset={message.offset()}"
            )

        return report

    for number in range(1, args.count + 1):
        event = build_transaction(number)
        producer.produce(
            args.topic,
            key=event["policy_id"].encode("utf-8"),
            value=json.dumps(event, separators=(",", ":")).encode("utf-8"),
            on_delivery=delivery_report(event["transaction_id"]),
        )
        producer.poll(0)
        if args.interval_ms:
            time.sleep(args.interval_ms / 1_000)

    unflushed = producer.flush(10)
    print(
        f"[done] delivered={delivered} failed={failed} "
        f"unflushed={unflushed} topic={args.topic}"
    )
    return 0 if failed == 0 and unflushed == 0 else 1


def consume(args: argparse.Namespace) -> int:
    running = True

    def stop(_signum, _frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    mongo = MongoClient(args.mongodb_uri, serverSelectionTimeoutMS=5_000)
    collection = mongo["insurance"]["transactions"]
    consumer = Consumer(
        {
            "bootstrap.servers": args.bootstrap_servers,
            "group.id": args.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    processed = 0

    try:
        mongo.admin.command("ping")
        consumer.subscribe([args.topic])
        print(
            f"[ready] topic={args.topic} group={args.group_id} "
            "sink=insurance.transactions"
        )

        while running and processed < args.max_messages:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise RuntimeError(message.error())

            event = json.loads(message.value().decode("utf-8"))
            for required in ("transaction_id", "policy_id", "amount", "currency"):
                if required not in event:
                    raise ValueError(f"record is missing {required!r}")

            if args.delay_ms:
                time.sleep(args.delay_ms / 1_000)

            document = {
                **event,
                "kafka_partition": message.partition(),
                "kafka_offset": message.offset(),
                "processed_at": datetime.now(timezone.utc),
            }
            result = collection.replace_one(
                {"transaction_id": event["transaction_id"]},
                document,
                upsert=True,
            )
            consumer.commit(message=message, asynchronous=False)
            processed += 1
            action = "inserted" if result.upserted_id is not None else "updated"
            print(
                f"[stored] transaction={event['transaction_id']} action={action} "
                f"partition={message.partition()} offset={message.offset()}"
            )
    finally:
        consumer.close()
        mongo.close()

    print(f"[done] processed={processed}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    producer_parser = subparsers.add_parser("produce", help="publish transactions")
    producer_parser.add_argument("--count", type=positive_integer, default=12)
    producer_parser.add_argument("--interval-ms", type=non_negative_integer, default=0)
    producer_parser.add_argument("--topic", default=DEFAULT_TOPIC)
    producer_parser.add_argument("--bootstrap-servers", default=DEFAULT_KAFKA)
    producer_parser.set_defaults(function=produce)

    consumer_parser = subparsers.add_parser(
        "consume", help="consume transactions and upsert them into MongoDB"
    )
    consumer_parser.add_argument("--max-messages", type=positive_integer, default=12)
    consumer_parser.add_argument("--delay-ms", type=non_negative_integer, default=750)
    consumer_parser.add_argument("--topic", default=DEFAULT_TOPIC)
    consumer_parser.add_argument("--group-id", default=DEFAULT_GROUP)
    consumer_parser.add_argument("--bootstrap-servers", default=DEFAULT_KAFKA)
    consumer_parser.add_argument("--mongodb-uri", default=DEFAULT_MONGODB)
    consumer_parser.set_defaults(function=consume)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return args.function(args)
    except (
        json.JSONDecodeError,
        KafkaException,
        PyMongoError,
        RuntimeError,
        ValueError,
        OSError,
    ) as error:
        print(f"[error] {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
