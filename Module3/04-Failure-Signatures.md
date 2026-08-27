# Walkthrough 04: Broker Pressure, Stalled Consumers, and Uneven Partitions

## Goal

Generate three different symptoms and identify the evidence that separates them.

## A. Uneven Partitions

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 50 --interval-ms 0 --key-mode hot
python demo/monitor_kafka.py
```

One partition should contain nearly all 1,000 events and the skew ratio should be close to three for a three-partition topic. This is a key-cardinality problem, not a broker outage.

Reset and compare customer keying:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 50 --interval-ms 0 --key-mode customer
python demo/monitor_kafka.py
```

## B. Stalled Consumer

With a backlog present, leave the consumer stopped. Take two snapshots ten seconds apart. End and committed offsets remain unchanged; lag stays nonzero. Start the consumer and prove committed offsets resume.

## C. Throughput Deficit

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 50 --interval-ms 0
python demo/consumer.py --delay-ms 250
```

While it runs, publish another burst from a second terminal and watch lag. Both producer and consumer offsets move, but end offsets grow faster.

## Broker-Pressure Evidence

```bash
docker compose -f kafka/docker-compose.yml stats --no-stream kafka
docker compose -f kafka/docker-compose.yml exec kafka du -sh /var/lib/kafka/data
docker compose -f kafka/docker-compose.yml logs --tail=200 kafka \
  | grep -Ei 'error|warn|disk|timeout|thrott|under.replicated' || true
```

The laptop-scale burst may not create actual CPU or disk saturation. Report the workload shape and measured resource values; do not claim pressure without evidence.

## Recovery Principle

Fix key selection for skew, restore or unblock a stalled process, and add sustainable processing capacity for throughput deficits. Restarting the broker corrects none of those root causes.
