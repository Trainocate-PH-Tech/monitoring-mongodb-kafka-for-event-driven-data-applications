# Walkthrough 02: Maintainable Source and Sink Configuration

## Review Before Deployment

```bash
jq . Module4/connectors/source.json
jq . Module4/connectors/sink.json
```

Confirm connector class, tasks, MongoDB URI, database/collection scope, topic naming, converters, error policy, and DLQ. The source watches only `connector_source`; the sink writes only `connector_sink`, preventing a change-stream loop.

Validate each config against its plugin before applying:

```bash
jq '.config + {name: .name}' Module4/connectors/source.json \
| curl -fsS -X PUT -H 'Content-Type: application/json' --data-binary @- \
  http://localhost:8083/connector-plugins/com.mongodb.kafka.connect.MongoSourceConnector/config/validate \
| jq '{error_count, configs: [.configs[] | select(.value.errors | length > 0)]}'

jq '.config + {name: .name}' Module4/connectors/sink.json \
| curl -fsS -X PUT -H 'Content-Type: application/json' --data-binary @- \
  http://localhost:8083/connector-plugins/com.mongodb.kafka.connect.MongoSinkConnector/config/validate \
| jq '{error_count, configs: [.configs[] | select(.value.errors | length > 0)]}'
```

## Apply Through Either Interface

Python applies idempotently using POST for a new connector and PUT for an existing one:

```bash
python demo/connect_admin.py apply Module4/connectors/source.json
python demo/connect_admin.py apply Module4/connectors/sink.json
```

Native creation example:

```bash
curl -fsS -X POST -H 'Content-Type: application/json' \
  --data-binary @Module4/connectors/source.json \
  http://localhost:8083/connectors | jq
```

Use POST only when the connector is absent. Update an existing connector with its config object:

```bash
jq '.config' Module4/connectors/sink.json \
| curl -fsS -X PUT -H 'Content-Type: application/json' --data-binary @- \
  http://localhost:8083/connectors/workshop-mongo-sink/config | jq
```

## Maintainability Review

- Use a narrow database/collection and explicit topic.
- Keep config in version control and review diffs.
- Define `tasks.max` deliberately; actual parallelism depends on connector and partitions.
- State error tolerance, logging, retries, and DLQ rather than relying on defaults.
- Externalize credentials in production; the lab URI is intentionally unauthenticated.
- Capture config validation and current task status before and after a change.
