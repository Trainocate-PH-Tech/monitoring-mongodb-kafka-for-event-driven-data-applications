# Module 4: Kafka Connect and MongoDB Connector Operations

This 90-minute module replaces the earlier worker analogy with a real distributed Kafka Connect worker and the official MongoDB source and sink connectors.

## Learning Objectives

- Inspect worker, connector, and task health through REST and logs.
- Review connector configuration for maintainability.
- Diagnose failed tasks, malformed records, retries, and DLQ behavior.
- Trace and reconcile MongoDB → Kafka → MongoDB movement.
- Plan safe credential, configuration, and version changes.

## Walkthroughs

| Outline bullet | Walkthrough |
| --- | --- |
| Worker, task, status, and errors | [01 - Worker and Task Health](01-Worker-and-Task-Health.md) |
| Maintainable source/sink configuration | [02 - Connector Configuration](02-Connector-Configuration.md) |
| Failures, malformed data, retry, DLQ | [03 - Failures and DLQ](03-Failures-and-DLQ.md) |
| Validate source and sink data movement | [04 - Trace and Reconcile](04-Trace-and-Reconcile.md) |
| Credentials, changes, and upgrades | [05 - Operational Changes](05-Operational-Changes.md) |

Complete [Exercises.md](Exercises.md) before using [Exercises-Solutions.md](Exercises-Solutions.md).

## Start the Environment

The Connect Compose project joins the existing Kafka and MongoDB networks, so start those first:

```bash
source .venv/bin/activate
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
docker compose -f connect/docker-compose.yml up -d --build --wait
```

Verify REST and installed plugins:

```bash
python demo/connect_admin.py plugins
curl -fsS http://localhost:8083/connector-plugins | jq
```

Expected plugin classes include `MongoSourceConnector` and `MongoSinkConnector`.

## Scoped Reset

Stop producing records, then remove only Module 4 connectors and data:

```bash
for connector in workshop-mongo-source workshop-mongo-sink; do
  if curl -fsS "http://localhost:8083/connectors/$connector/status" >/dev/null 2>&1; then
    curl -fsS -X PUT "http://localhost:8083/connectors/$connector/stop" >/dev/null
    for attempt in $(seq 1 20); do
      state=$(curl -fsS "http://localhost:8083/connectors/$connector/status" \
        | jq -r '.connector.state')
      if [ "$state" = "STOPPED" ]; then break; fi
      sleep 0.5
    done
    if [ "$state" != "STOPPED" ]; then
      echo "Timed out stopping $connector" >&2
      exit 1
    fi
    curl -fsS -X DELETE "http://localhost:8083/connectors/$connector/offsets" \
      >/dev/null
    curl -fsS -X DELETE "http://localhost:8083/connectors/$connector" \
      >/dev/null
  fi
done

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.connector_source.drop(); db.connector_sink.drop()'

for topic in workshop-cdc.workshop.connector_source workshop-connect-dlq; do
  docker compose -f kafka/docker-compose.yml exec kafka \
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
    --delete --if-exists --topic "$topic"
done
```

The reset explicitly stops each connector and clears its framework-managed offsets before deletion. The worker’s internal config, offset, and status topics remain in Kafka because other connectors could share them. Offset resets and collection/topic recreation are destructive teaching controls, not a production replay procedure.

## Lab Resources

| Resource | Name |
| --- | --- |
| Source connector | `workshop-mongo-source` |
| Sink connector | `workshop-mongo-sink` |
| Source collection | `workshop.connector_source` |
| Sink collection | `workshop.connector_sink` |
| CDC topic | `workshop-cdc.workshop.connector_source` |
| DLQ topic | `workshop-connect-dlq` |
| REST API | `http://localhost:8083` |

Connect is single-worker and unsecured for local instruction. Production requires authentication, TLS, authorization, redundant workers, protected configuration, and a supported upgrade process.
