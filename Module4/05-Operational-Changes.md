# Walkthrough 05: Credentials, Configuration Changes, and Version Upgrades

## Configuration Change Record

Before any PUT, capture:

```bash
curl -fsS http://localhost:8083/connectors/workshop-mongo-sink/config | jq \
  > /tmp/workshop-mongo-sink-before.json
curl -fsS http://localhost:8083/connectors/workshop-mongo-sink/status | jq
```

Review the desired JSON, validate it with the plugin endpoint, apply it, wait for all tasks, and reconcile a new record. Rollback uses the captured approved configuration—not a worker restart.

Do not put production secrets in connector JSON, shell history, Git, or exercise submissions. Use the deployment platform’s secret/config provider, restrict REST access, rotate credentials, and verify old credentials are revoked. The lab has no authentication so students can focus on operation flow.

## Version Evidence

```bash
curl -fsS http://localhost:8083/ | jq
curl -fsS http://localhost:8083/connector-plugins \
  | jq '.[] | select(.class | ascii_downcase | contains("mongodb"))'
docker compose -f connect/docker-compose.yml images
```

Record worker Kafka version, connector version, image digest, MongoDB version, compatibility evidence, and connector config before an upgrade.

## Upgrade Procedure

1. Read release notes and compatibility/security guidance.
2. Back up connector configuration and capture task/source/sink offsets and DLQ count.
3. Validate the new image and plugin in a nonproduction environment with representative data.
4. Roll workers one at a time in a redundant distributed deployment.
5. Confirm worker membership, all connectors/tasks, offset continuity, lag recovery, DLQ, and reconciliation.
6. Roll back the image/plugin if an abort condition is reached; do not blindly change stored offsets.

This lab has one worker, so recreating it causes a Connect outage. Connector configuration and offsets survive because distributed-worker state is stored in Kafka internal topics.

## Alert Recommendations

Alert on REST unavailability, any failed task, repeated restarts, sustained source/sink lag, retry exhaustion, any DLQ growth, configuration drift, and reconciliation failure. Assign worker, connector, source database, sink database, and data-quality ownership explicitly.
