"""Consume order events from Kafka and persist them to MongoDB."""

import argparse
import json
import signal
import time
from datetime import datetime, timezone

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_DLQ_TOPIC,
    KAFKA_GROUP_ID,
    KAFKA_TOPIC,
    MONGODB_COLLECTION,
    MONGODB_DATABASE,
    MONGODB_URI,
)


class InvalidEventError(RuntimeError):
    """Raised when the configured policy is to stop on an invalid event."""


def non_negative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value cannot be negative")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delay-ms",
        type=non_negative_integer,
        default=0,
        help="artificial processing delay per event in milliseconds (default: 0)",
    )
    parser.add_argument(
        "--max-messages",
        type=non_negative_integer,
        default=0,
        help="stop after examining this many records; 0 runs until Ctrl+C (default: 0)",
    )
    parser.add_argument(
        "--on-error",
        choices=("stop", "skip", "dlq"),
        default="stop",
        help="action for an invalid record (default: stop)",
    )
    parser.add_argument("--dlq-topic", default=KAFKA_DLQ_TOPIC)
    parser.add_argument("--group-id", default=KAFKA_GROUP_ID)
    parser.add_argument("--topic", default=KAFKA_TOPIC)
    parser.add_argument("--bootstrap-servers", default=KAFKA_BOOTSTRAP_SERVERS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    running = True

    def request_shutdown(_signum, _frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5_000)
    kafka = Consumer(
        {
            "bootstrap.servers": args.bootstrap_servers,
            "group.id": args.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    dlq_producer = (
        Producer({"bootstrap.servers": args.bootstrap_servers})
        if args.on_error == "dlq"
        else None
    )
    processed = 0
    rejected = 0
    consumed = 0

    def send_to_dlq(message, error: Exception) -> None:
        delivery_error = []

        def delivered(kafka_error, _message) -> None:
            if kafka_error is not None:
                delivery_error.append(kafka_error)

        dlq_producer.produce(
            args.dlq_topic,
            key=message.key(),
            value=message.value(),
            headers=[
                ("source_topic", message.topic()),
                ("source_partition", str(message.partition())),
                ("source_offset", str(message.offset())),
                ("error", str(error)[:500]),
            ],
            on_delivery=delivered,
        )
        remaining = dlq_producer.flush(10)
        if remaining or delivery_error:
            raise KafkaException(
                delivery_error[0] if delivery_error else "DLQ delivery timed out"
            )

    try:
        mongo.admin.command("ping")
        orders = mongo[MONGODB_DATABASE][MONGODB_COLLECTION]
        kafka.subscribe([args.topic])
        print(
            f"[ready] Consuming {args.topic!r} as group {args.group_id!r}; "
            "press Ctrl+C to stop"
        )

        while running and (args.max_messages == 0 or consumed < args.max_messages):
            message = kafka.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(message.error())

            try:
                event = json.loads(message.value().decode("utf-8"))
                if args.delay_ms:
                    time.sleep(args.delay_ms / 1_000)

                quantity = int(event["quantity"])
                unit_price = float(event["unit_price"])
                document = {
                    **event,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_amount": round(quantity * unit_price, 2),
                    "status": "received",
                    "processed_at": datetime.now(timezone.utc),
                }
                orders.replace_one(
                    {"order_id": document["order_id"]}, document, upsert=True
                )
                kafka.commit(message=message, asynchronous=False)
                processed += 1
                consumed += 1
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                location = f"partition={message.partition()} offset={message.offset()}"
                if args.on_error == "stop":
                    raise InvalidEventError(
                        f"Invalid event at {location}; offset was not committed: {error}"
                    ) from error
                if args.on_error == "dlq":
                    send_to_dlq(message, error)
                    print(f"[dlq] Sent invalid event at {location} to {args.dlq_topic!r}")
                else:
                    print(f"[skip] Discarded invalid event at {location}: {error}")
                kafka.commit(message=message, asynchronous=False)
                rejected += 1
                consumed += 1
                continue

            if processed == 1 or processed % 10 == 0:
                print(
                    f"[progress] processed={processed} "
                    f"partition={message.partition()} offset={message.offset()}"
                )
    except (InvalidEventError, KafkaException, PyMongoError) as error:
        print(f"[error] Consumer stopped: {error}")
        return 1
    finally:
        if dlq_producer is not None:
            dlq_producer.flush(5)
        kafka.close()
        mongo.close()

    print(f"[done] consumed={consumed} processed={processed} rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
