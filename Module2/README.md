# Module 2: MongoDB Monitoring and Maintenance

This 75-minute module turns every MongoDB bullet in the course outline into a runnable investigation using the Northwind order workload.

## Learning Objectives

- Measure database, collection, index, and storage growth.
- Interpret profiler evidence and `executionStats` without guessing from latency alone.
- propose, validate, and roll back an index change.
- Prove replica health and backup restore readiness.
- Turn MongoDB signals into actionable alerts.

## Walkthroughs

| Outline bullet | Walkthrough |
| --- | --- |
| Database, collection, index, and storage growth | [01 - Growth Indicators](01-Growth-Indicators.md) |
| Slow-query signals and query plans | [02 - Slow Queries and Plans](02-Slow-Queries-and-Plans.md) |
| Indexes for changing workloads | [03 - Index Maintenance](03-Index-Maintenance.md) |
| Replication, backups, restore readiness, capacity | [04 - Replication, Backup, and Capacity](04-Replication-Backup-and-Capacity.md) |
| Logging and alerting | [05 - Logging and Alerting](05-Logging-and-Alerting.md) |

Complete [Exercises.md](Exercises.md) before consulting [Exercises-Solutions.md](Exercises-Solutions.md).

## Setup and Reset

From the repository root, activate `.venv`, start MongoDB and Kafka, and create a known dataset:

```bash
source .venv/bin/activate
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
python demo/setup_demo.py --reset
python demo/producer.py --repeat 5 --interval-ms 0
python demo/consumer.py --max-messages 100
```

The Python path uses `monitor_mongodb.py` and `inspect_mongodb.py`. The native path uses `mongosh`, `mongodump`, `mongorestore`, and Docker logs. Both inspect the same `workshop.orders` collection.

Reset between destructive walkthroughs with `python demo/setup_demo.py --reset`. Walkthrough 04 uses the isolated database `workshop_restore`; never restore over `workshop`.

## Completion Evidence

Students should retain a baseline, fault evidence, change record, rollback command, post-change validation, and an alert recommendation. Command success alone is not operational validation.
