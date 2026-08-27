"""Publish dummy order events to Kafka."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from confluent_kafka import KafkaException, Producer

from settings import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


DATA_FILE = Path(__file__).parent / "data" / "orders.jsonl"


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return number


def non_negative_float(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value cannot be negative")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repeat",
        type=positive_integer,
        default=1,
        help="number of times to publish the complete dummy dataset (default: 1)",
    )
    parser.add_argument(
        "--interval-ms",
        type=non_negative_float,
        default=50,
        help="pause between events in milliseconds; use 0 for a burst (default: 50)",
    )
    parser.add_argument(
        "--key-mode",
        choices=("customer", "hot"),
        default="customer",
        help="key by customer or force every event onto one hot partition",
    )
    parser.add_argument(
        "--inject-invalid",
        action="store_true",
        help="append one intentionally malformed JSON record",
    )
    parser.add_argument(
        "--duplicate-first",
        action="store_true",
        help="publish the first event twice with the same order_id and event_id",
    )
    parser.add_argument("--topic", default=KAFKA_TOPIC)
    parser.add_argument("--bootstrap-servers", default=KAFKA_BOOTSTRAP_SERVERS)
    return parser.parse_args()


def load_templates() -> list[dict]:
    orders = []
    with DATA_FILE.open(encoding="utf-8") as data_file:
        for line_number, line in enumerate(data_file, start=1):
            if not line.strip():
                continue
            try:
                orders.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on {DATA_FILE}:{line_number}: {error}") from error
    if not orders:
        raise ValueError(f"No orders found in {DATA_FILE}")
    return orders


def main() -> int:
    args = parse_args()
    try:
        templates = load_templates()
    except (OSError, ValueError) as error:
        print(f"[error] {error}")
        return 1

    producer = Producer({"bootstrap.servers": args.bootstrap_servers})
    run_id = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-"
        f"{uuid4().hex[:8]}"
    )
    counts = {"delivered": 0, "failed": 0}
    duplicate_sent = False

    def delivery_report(error, message) -> None:
        if error is not None:
            counts["failed"] += 1
            print(f"[error] Delivery failed: {error}")
        else:
            counts["delivered"] += 1

    def publish(key: bytes, payload: bytes) -> None:
        while True:
            try:
                producer.produce(
                    args.topic,
                    key=key,
                    value=payload,
                    on_delivery=delivery_report,
                )
                break
            except BufferError:
                producer.poll(0.5)
        producer.poll(0)

    try:
        for repeat_number in range(1, args.repeat + 1):
            for template in templates:
                event = dict(template)
                event["event_type"] = "order.created"
                event["event_id"] = str(uuid4())
                event["order_id"] = (
                    f"{template['sample_order_id']}-{run_id}-{repeat_number:03d}"
                )
                event["created_at"] = datetime.now(timezone.utc).isoformat()
                event.pop("sample_order_id")
                payload = json.dumps(event, separators=(",", ":")).encode("utf-8")

                key = (
                    event["customer_id"].encode("utf-8")
                    if args.key_mode == "customer"
                    else b"HOT-CUSTOMER"
                )
                publish(key, payload)
                if args.duplicate_first and not duplicate_sent:
                    publish(key, payload)
                    duplicate_sent = True
                if args.interval_ms:
                    time.sleep(args.interval_ms / 1_000)

        if args.inject_invalid:
            publish(b"INVALID-RECORD", b'{"event_type":"order.created","order_id":')
            print("[inject] Published one malformed JSON record")
    except (KafkaException, KeyError) as error:
        print(f"[error] Publishing stopped: {error}")
        return 1
    finally:
        remaining = producer.flush(10)

    expected = (
        len(templates) * args.repeat
        + int(args.duplicate_first)
        + int(args.inject_invalid)
    )
    print(
        f"[done] expected={expected} delivered={counts['delivered']} "
        f"failed={counts['failed']} unflushed={remaining} topic={args.topic}"
    )
    return 0 if counts["failed"] == 0 and remaining == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
