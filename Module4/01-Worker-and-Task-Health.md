# Walkthrough 01: Worker, Connector, Task, Status, and Error States

## Worker Health

The REST root proves the worker API is available; the plugin endpoint proves plugin discovery:

```bash
curl -fsS http://localhost:8083/ | jq
curl -fsS http://localhost:8083/connector-plugins | jq
python demo/connect_admin.py plugins
docker compose -f connect/docker-compose.yml ps
```

**Expected output:** REST root reports Kafka `version: 4.3.1`; plugin output lists Mongo source/sink version `3.0.0`; Compose shows Connect `Up (healthy)`. **Meaning:** the worker and plugins are available, but no connector status has yet been proven.

A healthy REST endpoint does not prove any connector or task exists.

## Deploy and Inspect

```bash
python demo/connect_admin.py apply Module4/connectors/source.json
python demo/connect_admin.py apply Module4/connectors/sink.json
python demo/connect_admin.py wait workshop-mongo-source
python demo/connect_admin.py wait workshop-mongo-sink
python demo/connect_admin.py list
```

**Expected output:** apply returns each connector's effective config; both waits return connector and task state `RUNNING`; list contains `workshop-mongo-source` and `workshop-mongo-sink`. **Meaning:** both deployed connectors have an active task on the worker.

Equivalent REST calls:

```bash
curl -fsS http://localhost:8083/connectors?expand=status\&expand=info | jq
curl -fsS http://localhost:8083/connectors/workshop-mongo-source/status | jq
curl -fsS http://localhost:8083/connectors/workshop-mongo-sink/status | jq
```

**Expected output:** expanded JSON shows each connector's class/config and status; individual status objects show connector `RUNNING` and task 0 `RUNNING`. **Meaning:** native REST evidence agrees with the Python helper.

Read connector and every task state. A connector can be `RUNNING` while a task is `FAILED`; task-level inspection is mandatory.

## Pause, Resume, and Restart

```bash
curl -fsS -X PUT http://localhost:8083/connectors/workshop-mongo-sink/pause
curl -fsS http://localhost:8083/connectors/workshop-mongo-sink/status | jq
curl -fsS -X PUT http://localhost:8083/connectors/workshop-mongo-sink/resume
curl -fsS -X POST 'http://localhost:8083/connectors/workshop-mongo-sink/restart?includeTasks=true&onlyFailed=false' | jq
```

**Expected output:** pause/resume calls usually have empty bodies; status transitions through `PAUSED` then `RUNNING`; restart may show task `RESTARTING` before returning to `RUNNING`. **Meaning:** lifecycle controls change task execution without changing connector configuration.

Pause is an operational control; restart reloads the same configuration and does not repair a bad value.

## Logs

```bash
docker compose -f connect/docker-compose.yml logs --tail=200 connect \
  | grep -E 'workshop-mongo|ERROR|WARN|Exception' || true
```

**Expected output:** connector startup/status lines and possibly warnings; no output is also valid when the filter finds nothing. **Meaning:** logs supplement REST with error traces but should be correlated with current task status.

Record worker availability, connector state, task state, trace/error text, and the last known successful data movement as separate evidence.
