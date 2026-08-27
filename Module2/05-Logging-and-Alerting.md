# Walkthrough 05: MongoDB Logging and Alerting Practices

## Goal

Convert raw database signals into alerts that identify an owner and a first action.

## Collect a Diagnostic Bundle

```bash
python demo/monitor_mongodb.py snapshot
python demo/monitor_mongodb.py index-usage
docker compose -f mongodb/docker-compose.yml logs --since=10m mongodb
docker compose -f mongodb/docker-compose.yml exec mongodb df -h /data/db /backups
```

Native structured snapshot:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const s = db.serverStatus();
    printjson({
      writablePrimary: db.hello().isWritablePrimary,
      connections: s.connections,
      opcounters: s.opcounters,
      network: s.network,
      assertions: s.asserts
    });'
```

## Alert Design

For each signal define a condition, duration, severity, owner, evidence link, and first response. Example lab recommendations:

| Signal | Actionable condition | First owner/action |
| --- | --- | --- |
| Writable primary | False on a replica set expected to accept writes | DBA: inspect member state and elections |
| Disk forecast | Projected to cross the operational limit inside the response window | Platform/DBA: identify growth source and add capacity |
| Query efficiency | Sustained high examined/returned ratio for an important query shape | DBA/application: inspect plan and workload |
| Connections | Sustained use near the configured or platform limit | DBA/application: find pool or leak source |
| Replication | Unhealthy member or growing optime lag | DBA: protect redundancy before maintenance |
| Backups | Backup or scheduled restore validation overdue/failed | Backup owner: investigate before declaring readiness |

Never alert on every slow log line or on raw collection size without context. Prefer sustained symptoms, rate-of-change, and business-query scope.

## Completion Check

Write one availability alert, one performance alert, and one capacity alert. Each must be actionable without the responder first asking what system or query the alert describes.
