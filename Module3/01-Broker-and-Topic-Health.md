# Walkthrough 01: Brokers, Topics, Partitions, Replicas, Throughput, and Disk

## Goal

Establish evidence that the broker can serve every partition and quantify a short workload.

## Metadata Baseline

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --describe --topic workshop-orders
```

Every partition needs a valid leader. In this one-broker lab, replicas and ISR each contain broker 1.

## Produce and Measure

Capture start time and offsets, produce 2,000 records, then capture end time and offsets:

```bash
date -u +%s
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9092 \
  --topic workshop-orders

python demo/producer.py --repeat 100 --interval-ms 0

date -u +%s
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9092 \
  --topic workshop-orders
```

Throughput for this observation is `offset delta / elapsed seconds`. It is an application-level estimate, not the broker byte-rate metric a production monitoring system would scrape.

## Python and Disk Evidence

```bash
python demo/monitor_kafka.py
docker compose -f kafka/docker-compose.yml exec kafka du -sh /var/lib/kafka/data
docker compose -f kafka/docker-compose.yml stats --no-stream kafka
```

The Python table shows leader, replica/ISR counts, committed offsets, end offsets, lag, and skew. A group with no commits is displayed from offset zero.

## Interpretation

Topic health, broker process health, throughput, and disk are separate signals. A healthy leader does not prove a consumer is current; growing offsets do not prove MongoDB received data.
