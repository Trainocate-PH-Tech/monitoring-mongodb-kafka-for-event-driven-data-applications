# Module 3: Kafka Monitoring and Maintenance

This 75-minute module turns the Kafka outline into evidence-driven labs using the existing single-node KRaft broker.

## Learning Objectives

- Prove broker, leader, replica, topic, partition, disk, and throughput health.
- Explain lag from committed and end offsets.
- Review retention, compaction, and lifecycle changes safely.
- Distinguish pressure, stalled consumers, and partition skew.
- Design Kafka alerts with an owner and response.

## Walkthroughs

| Outline bullet | Walkthrough |
| --- | --- |
| Brokers, topics, partitions, replicas, throughput, disk | [01 - Broker and Topic Health](01-Broker-and-Topic-Health.md) |
| Lag, offsets, and consumer groups | [02 - Consumer Lag](02-Consumer-Lag.md) |
| Retention, compaction, and lifecycle | [03 - Topic Lifecycle](03-Topic-Lifecycle.md) |
| Pressure, stalls, and uneven partitions | [04 - Failure Signatures](04-Failure-Signatures.md) |
| Alerting practices | [05 - Logging and Alerting](05-Logging-and-Alerting.md) |

Complete [Exercises.md](Exercises.md), then compare with [Exercises-Solutions.md](Exercises-Solutions.md).

## Setup

```bash
source .venv/bin/activate
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
python demo/setup_demo.py --reset
```

**Expected output:** both services become healthy and setup ends `[ready]` with a three-partition empty order topic. **Meaning:** Kafka labs begin from known topic state.

Python monitoring:

```bash
python demo/monitor_kafka.py
```

**Expected output:** a partition table followed by `total_end_offsets`, `total_lag`, and `partition_skew_ratio`. Immediately after reset, totals and skew are zero. **Meaning:** the helper summarizes structure, backlog, and distribution.

The same evidence is available through scripts in `/opt/kafka/bin` inside the Kafka container. Exact partition numbers and offsets vary; assess invariants and movement.

## Isolated Lifecycle Topic

Walkthrough 03 uses `workshop-lifecycle` only. Delete it after the walkthrough:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --delete --if-exists --topic workshop-lifecycle
```

**Expected output:** deletion succeeds silently or reports no error when already absent. **Meaning:** only the isolated lifecycle topic is cleaned up.

This lab has one broker and replication factor one. It can show metadata and failure symptoms, but not failover, ISR loss between replicas, or a zero-downtime rolling restart.
