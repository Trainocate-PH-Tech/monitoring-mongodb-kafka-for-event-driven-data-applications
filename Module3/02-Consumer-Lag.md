# Walkthrough 02: Consumer Lag, Offset Movement, and Group Behavior

## Goal

Use offset movement to distinguish backlog, progress, and a stall.

## Create Backlog

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 20 --interval-ms 0
python demo/monitor_kafka.py
```

Native group evidence:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

If the group has never committed, the CLI may say it does not exist. The Python snapshot treats its starting offset as zero; after the consumer starts, both show committed state.

## Observe Movement

Start a slow consumer in terminal 1:

```bash
python demo/consumer.py --delay-ms 100
```

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

## Diagnosis Rules

| End offsets | Committed offsets | Likely interpretation |
| --- | --- | --- |
| Increasing | Increasing equally | Consumer is keeping up |
| Increasing | Increasing more slowly | Consumer throughput deficit |
| Fixed | Increasing | Backlog is draining |
| Increasing/fixed | Fixed | Stopped, blocked, failed, or rebalancing consumer |

Lag is a symptom; correlate it with process output, MongoDB latency, rebalances, and partition distribution before choosing a recovery.
