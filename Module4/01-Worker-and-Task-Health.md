# Walkthrough 01: Worker, Connector, Task, Status, and Error States

## Worker Health

The REST root proves the worker API is available; the plugin endpoint proves plugin discovery:

```bash
curl -fsS http://localhost:8083/ | jq
curl -fsS http://localhost:8083/connector-plugins | jq
python demo/connect_admin.py plugins
docker compose -f connect/docker-compose.yml ps
```

A healthy REST endpoint does not prove any connector or task exists.

## Deploy and Inspect

```bash
python demo/connect_admin.py apply Module4/connectors/source.json
python demo/connect_admin.py apply Module4/connectors/sink.json
python demo/connect_admin.py wait workshop-mongo-source
python demo/connect_admin.py wait workshop-mongo-sink
python demo/connect_admin.py list
```

Equivalent REST calls:

```bash
curl -fsS http://localhost:8083/connectors?expand=status\&expand=info | jq
curl -fsS http://localhost:8083/connectors/workshop-mongo-source/status | jq
curl -fsS http://localhost:8083/connectors/workshop-mongo-sink/status | jq
```

Read connector and every task state. A connector can be `RUNNING` while a task is `FAILED`; task-level inspection is mandatory.

## Pause, Resume, and Restart

```bash
curl -fsS -X PUT http://localhost:8083/connectors/workshop-mongo-sink/pause
curl -fsS http://localhost:8083/connectors/workshop-mongo-sink/status | jq
curl -fsS -X PUT http://localhost:8083/connectors/workshop-mongo-sink/resume
curl -fsS -X POST 'http://localhost:8083/connectors/workshop-mongo-sink/restart?includeTasks=true&onlyFailed=false' | jq
```

Pause is an operational control; restart reloads the same configuration and does not repair a bad value.

## Logs

```bash
docker compose -f connect/docker-compose.yml logs --tail=200 connect \
  | grep -E 'workshop-mongo|ERROR|WARN|Exception' || true
```

Record worker availability, connector state, task state, trace/error text, and the last known successful data movement as separate evidence.
