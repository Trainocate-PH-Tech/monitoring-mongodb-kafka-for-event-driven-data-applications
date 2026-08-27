"""A minimal Kafka-to-MongoDB insurance transaction client for the labs."""

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


def build_transaction(number: int, id_prefix: str = "LAB1-TXN") -> dict:
    """Return a deterministic transaction so replay demonstrates an upsert."""
    transaction_types = ("premium.payment", "claim.payment", "refund.payment")
    return {
        "event_type": "insurance.transaction.recorded",
        "transaction_id": f"{id_prefix}-{number:03d}",
        "policy_id": f"POL-{((number - 1) % 4) + 1001}",
        "customer_id": f"CUST-{((number - 1) % 6) + 501}",
        "transaction_type": transaction_types[(number - 1) % len(transaction_types)],
        "amount": round(75.0 + number * 19.25, 2),
        "currency": "USD",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def produce(args: argparse.Namespace) -> int:
    if args.inject_invalid_after is not None and args.inject_invalid_after > args.count:
        print("[error] --inject-invalid-after cannot exceed --count")
        return 1

    producer = Producer({"bootstrap.servers": args.bootstrap_servers})
    delivered = 0
    failed = 0
    expected = args.count + int(args.inject_invalid_after is not None)

    def delivery_report(transaction_id: str, always_report: bool = False):
        def report(error, message) -> None:
            nonlocal delivered, failed
            if error is not None:
                failed += 1
                print(f"[failed] transaction={transaction_id} error={error}")
                return
            delivered += 1
            if (
                always_report
                or delivered == 1
                or delivered % args.report_every == 0
                or delivered == expected
            ):
                print(
                    f"[delivered] count={delivered} transaction={transaction_id} "
                    f"partition={message.partition()} offset={message.offset()}"
                )

        return report

    def publish_invalid() -> None:
        producer.produce(
            args.topic,
            key=b"POL-1001",
            value=b'{"event_type":"insurance.transaction.recorded","transaction_id":',
            on_delivery=delivery_report("INVALID-JSON", always_report=True),
        )
        producer.poll(0)

    if args.inject_invalid_after == 0:
        publish_invalid()

    for number in range(1, args.count + 1):
        event = build_transaction(number, args.id_prefix)
        producer.produce(
            args.topic,
            key=event["policy_id"].encode("utf-8"),
            value=json.dumps(event, separators=(",", ":")).encode("utf-8"),
            on_delivery=delivery_report(event["transaction_id"]),
        )
        producer.poll(0)
        if args.inject_invalid_after == number:
            publish_invalid()
        if args.interval_ms:
            time.sleep(args.interval_ms / 1_000)

    unflushed = producer.flush(10)
    print(
        f"[done] expected={expected} delivered={delivered} failed={failed} "
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
    collection = mongo[args.mongodb_database][args.mongodb_collection]
    consumer = Consumer(
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
    consumed = 0
    processed = 0
    rejected = 0
    last_message_at = time.monotonic()

    def send_to_dlq(message, error: Exception) -> None:
        delivery_errors = []

        def delivered(kafka_error, _message) -> None:
            if kafka_error is not None:
                delivery_errors.append(kafka_error)

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
        if remaining or delivery_errors:
            raise KafkaException(
                delivery_errors[0] if delivery_errors else "DLQ delivery timed out"
            )

    try:
        mongo.admin.command("ping")
        consumer.subscribe([args.topic])
        print(
            f"[ready] topic={args.topic} group={args.group_id} "
            f"sink={args.mongodb_database}.{args.mongodb_collection}"
        )

        while running and consumed < args.max_messages:
            message = consumer.poll(1.0)
            if message is None:
                if (
                    consumed > 0
                    and args.idle_timeout_seconds > 0
                    and time.monotonic() - last_message_at >= args.idle_timeout_seconds
                ):
                    print(
                        f"[idle] no records received for "
                        f"{args.idle_timeout_seconds}s; stopping"
                    )
                    break
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise RuntimeError(message.error())
            last_message_at = time.monotonic()

            try:
                event = json.loads(message.value().decode("utf-8"))
                if not isinstance(event, dict):
                    raise ValueError("record must be a JSON object")
                for required in (
                    "transaction_id",
                    "policy_id",
                    "amount",
                    "currency",
                ):
                    if required not in event:
                        raise ValueError(f"record is missing {required!r}")
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
                location = (
                    f"topic={message.topic()} partition={message.partition()} "
                    f"offset={message.offset()}"
                )
                if args.on_error == "stop":
                    raise ValueError(
                        f"invalid insurance transaction at {location}; "
                        f"offset was not committed: {error}"
                    ) from error

                send_to_dlq(message, error)
                consumer.commit(message=message, asynchronous=False)
                consumed += 1
                rejected += 1
                print(
                    f"[dlq] {location} destination={args.dlq_topic} "
                    "source_offset_committed=true"
                )
                continue

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
            consumed += 1
            processed += 1
            action = "inserted" if result.upserted_id is not None else "updated"
            if (
                processed == 1
                or processed % args.report_every == 0
                or consumed == args.max_messages
            ):
                print(
                    f"[stored] count={processed} "
                    f"transaction={event['transaction_id']} action={action} "
                    f"partition={message.partition()} offset={message.offset()}"
                )
    finally:
        if dlq_producer is not None:
            dlq_producer.flush(5)
        consumer.close()
        mongo.close()

    print(
        f"[done] consumed={consumed} processed={processed} rejected={rejected}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    producer_parser = subparsers.add_parser("produce", help="publish transactions")
    producer_parser.add_argument("--count", type=positive_integer, default=12)
    producer_parser.add_argument("--interval-ms", type=non_negative_integer, default=0)
    producer_parser.add_argument(
        "--id-prefix", default="LAB1-TXN",
        help="transaction ID prefix (default: LAB1-TXN)",
    )
    producer_parser.add_argument(
        "--report-every", type=positive_integer, default=1,
        help="print progress after this many acknowledgements (default: 1)",
    )
    producer_parser.add_argument(
        "--inject-invalid-after",
        type=non_negative_integer,
        help="publish malformed JSON after this many valid records",
    )
    producer_parser.add_argument("--topic", default=DEFAULT_TOPIC)
    producer_parser.add_argument("--bootstrap-servers", default=DEFAULT_KAFKA)
    producer_parser.set_defaults(function=produce)

    consumer_parser = subparsers.add_parser(
        "consume", help="consume transactions and upsert them into MongoDB"
    )
    consumer_parser.add_argument("--max-messages", type=positive_integer, default=12)
    consumer_parser.add_argument("--delay-ms", type=non_negative_integer, default=750)
    consumer_parser.add_argument(
        "--idle-timeout-seconds",
        type=non_negative_integer,
        default=0,
        help="exit after this many idle seconds after processing starts; 0 disables",
    )
    consumer_parser.add_argument(
        "--report-every", type=positive_integer, default=1,
        help="print progress after this many stored records (default: 1)",
    )
    consumer_parser.add_argument("--topic", default=DEFAULT_TOPIC)
    consumer_parser.add_argument("--group-id", default=DEFAULT_GROUP)
    consumer_parser.add_argument("--bootstrap-servers", default=DEFAULT_KAFKA)
    consumer_parser.add_argument("--mongodb-uri", default=DEFAULT_MONGODB)
    consumer_parser.add_argument("--mongodb-database", default="insurance")
    consumer_parser.add_argument("--mongodb-collection", default="transactions")
    consumer_parser.add_argument(
        "--on-error", choices=("stop", "dlq"), default="stop",
        help="stop or publish invalid records to a DLQ (default: stop)",
    )
    consumer_parser.add_argument(
        "--dlq-topic", default=f"{DEFAULT_TOPIC}-dlq",
        help=f"dead-letter topic (default: {DEFAULT_TOPIC}-dlq)",
    )
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
