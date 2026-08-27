# Module 3 Exercise Solutions

Exact offsets and partition assignments vary.

## Solution 1: Topic Health Report

Use `kafka-topics.sh --describe`, two `kafka-get-offsets.sh` samples around the producer run, `du`, container stats, and `monitor_kafka.py`. All partitions need leaders and ISR. Estimate records/second from the total offset delta. This omits payload bytes, request latency, percentiles, retries, and broker/network metrics.

## Solution 2: Classify Lag

- Fixed end offsets + advancing commits + falling lag: backlog draining.
- Fixed or advancing end offsets + fixed commits + nonzero lag: stalled or blocked consumer.
- End and commits both advance, but end grows faster: throughput deficit.

Correlate group membership, consumer output, rebalances, and MongoDB health. Recovery is proven only when offset movement is sustainable and lag returns to the expected range.

## Solution 3: Partition Skew

`python demo/producer.py --repeat 50 --key-mode hot --interval-ms 0` concentrates the batch. The helper reports `max partition end / average partition end`; near 3.0 is maximum skew across three partitions. Customer keys spread the five keys across more than one partition. Extra consumers beyond three cannot own a partition and do not increase parallelism.

## Solution 4: Lifecycle Change Review

Thirty-second deletion risks losing replay/backlog data. Compaction is meaningful only for keyed latest-state semantics and does not preserve every order event. Test on the isolated topic. Roll back with:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-lifecycle --alter \
  --delete-config cleanup.policy,retention.ms,min.cleanable.dirty.ratio
```

Validate effective settings, replay requirements, lag, and disk forecast—not just command success.

## Solution 5: Restart and Persistence

Record end offsets and group commits, run `docker compose -f kafka/docker-compose.yml restart kafka`, wait for health, and repeat. The named volume preserves both. Production additionally requires replica/ISR health, controlled one-broker-at-a-time work, leader availability, controller health, client recovery, and abort thresholds. This lab has a real outage during restart.

## Solution 6: Kafka Alert Checklist

Strong answers separate no leader, ISR loss, stalled commits, sustained rate deficit, disk exhaustion forecast, skew, and configuration drift. “Lag > 0” alone is not a page. Each alert includes topic/group/partition evidence, a persistence duration, severity, owner, and first diagnostic action.
