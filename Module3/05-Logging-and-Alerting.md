# Walkthrough 05: Kafka Logging and Alerting Practices

## Diagnostic Bundle

```bash
docker compose -f kafka/docker-compose.yml ps
docker compose -f kafka/docker-compose.yml logs --since=10m kafka
python demo/monitor_kafka.py
docker compose -f kafka/docker-compose.yml exec kafka du -sh /var/lib/kafka/data
docker compose -f kafka/docker-compose.yml stats --no-stream kafka
```

**Expected output:** Kafka is `Up (healthy)`, recent logs contain normal startup/request activity unless a fault occurred, the monitor prints offsets/lag/skew, and disk/container stats print current resource values. **Meaning:** the bundle spans availability, errors, backlog, distribution, storage, and process load.

Capture topic configuration separately because lifecycle risk is not visible from process health.

## Alert Matrix

| Signal | Condition | Owner and first action |
| --- | --- | --- |
| Leader availability | Any expected partition has no leader | Kafka owner: inspect broker and controller health |
| ISR/replicas | ISR below approved replica count | Kafka owner: protect redundancy and stop risky maintenance |
| Consumer progress | Sustained lag with no committed-offset movement | Consumer owner: inspect membership and worker errors |
| Throughput deficit | Lag grows while both end and committed offsets move | Application/platform: compare rates and downstream latency |
| Disk forecast | Projected log-dir exhaustion inside response window | Kafka/platform: identify topic growth and add capacity |
| Partition skew | One partition persistently dominates bytes/records or lag | Producer/data owner: review keys and partition count |
| Lifecycle drift | Effective topic settings differ from approved policy | Kafka owner: review and roll back unauthorized override |

Use a duration to avoid paging on brief rebalances. Include topic, group, partition, current/end offsets, lag duration, and a runbook link in consumer alerts.

## Completion Check

Explain why “consumer lag > 0” is usually a poor page and replace it with two alerts: one for a stalled group and one for a sustained throughput deficit.
