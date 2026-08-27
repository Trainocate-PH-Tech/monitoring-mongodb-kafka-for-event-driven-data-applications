"""Capture Kafka topic distribution and consumer-group lag evidence."""

import argparse

from confluent_kafka import Consumer, KafkaException, TopicPartition

from settings import KAFKA_BOOTSTRAP_SERVERS, KAFKA_GROUP_ID, KAFKA_TOPIC


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-servers", default=KAFKA_BOOTSTRAP_SERVERS)
    parser.add_argument("--topic", default=KAFKA_TOPIC)
    parser.add_argument("--group-id", default=KAFKA_GROUP_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    consumer = Consumer({
        "bootstrap.servers": args.bootstrap_servers,
        "group.id": args.group_id,
        "enable.auto.commit": False,
        "session.timeout.ms": 6000,
    })
    try:
        metadata = consumer.list_topics(args.topic, timeout=5)
        topic = metadata.topics.get(args.topic)
        if topic is None or topic.error is not None:
            raise KafkaException(topic.error if topic else f"Unknown topic {args.topic}")
        partitions = [TopicPartition(args.topic, number) for number in sorted(topic.partitions)]
        committed = consumer.committed(partitions, timeout=5)
        totals = {"end": 0, "lag": 0}
        ends = []
        print("partition leader replicas isr committed end lag")
        for partition, group_offset in zip(partitions, committed):
            details = topic.partitions[partition.partition]
            _low, high = consumer.get_watermark_offsets(partition, timeout=5, cached=False)
            current = group_offset.offset if group_offset.offset >= 0 else 0
            lag = max(high - current, 0)
            ends.append(high)
            totals["end"] += high
            totals["lag"] += lag
            print(
                f"{partition.partition} {details.leader} "
                f"{len(details.replicas)} {len(details.isrs)} {current} {high} {lag}"
            )
        average = totals["end"] / len(ends) if ends else 0
        skew = (max(ends) / average) if average else 0
        print(f"total_end_offsets: {totals['end']}")
        print(f"total_lag: {totals['lag']}")
        print(f"partition_skew_ratio: {skew:.2f}")
    except KafkaException as error:
        print(f"[error] Kafka monitoring failed: {error}")
        return 1
    finally:
        consumer.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
