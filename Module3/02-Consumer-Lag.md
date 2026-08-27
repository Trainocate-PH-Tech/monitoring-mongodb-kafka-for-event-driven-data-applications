# Walkthrough 02: Consumer Lag, Offset Movement, and Group Behavior

## Goal

Use offset movement to distinguish backlog, progress, and a stall.

## Create Backlog

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 20 --interval-ms 0
python demo/monitor_kafka.py
```

**Expected output:** the producer delivers 400; the monitor reports `total_end_offsets: 400` and `total_lag: 400` for a group with no commits. **Meaning:** Kafka has a complete backlog while the consumer is stopped.

Native group evidence:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

**Expected output:** before the group first commits, Kafka may report that the group does not exist; afterward it prints partition rows with offsets and lag. **Meaning:** topic data can exist before consumer-group state exists.

If the group has never committed, the CLI may say it does not exist. The Python snapshot treats its starting offset as zero; after the consumer starts, both show committed state.

## Observe Movement

Start a slow consumer in terminal 1:

```bash
python demo/consumer.py --delay-ms 100
```

**Expected output:** progress lines appear at a controlled rate until 400 records are processed. **Meaning:** committed offsets should move steadily rather than remaining stalled.

In terminal 2, take the same snapshot every few seconds. You should see:

- log-end offsets remain fixed after the producer stops;
- committed offsets increase;
- lag decreases toward zero;
- group membership exists while the process runs.

Describe membership and assignments:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe --members --verbose
```

**Expected output:** while running, one consumer member owns the three partitions; after exit, Kafka reports no active members while committed offsets remain. **Meaning:** membership is temporary, but group progress is durable.

## Diagnosis Rules

| End offsets | Committed offsets | Likely interpretation |
| --- | --- | --- |
| Increasing | Increasing equally | Consumer is keeping up |
| Increasing | Increasing more slowly | Consumer throughput deficit |
| Fixed | Increasing | Backlog is draining |
| Increasing/fixed | Fixed | Stopped, blocked, failed, or rebalancing consumer |

Lag is a symptom; correlate it with process output, MongoDB latency, rebalances, and partition distribution before choosing a recovery.
