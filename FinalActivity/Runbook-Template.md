# Northwind Orders Operations Runbook

## 1. Document Control

| Field | Value |
| --- | --- |
| Owner | |
| Approver | |
| Version/date | |
| Review frequency | |
| Systems/environments | |
| Related dashboards/tickets | |

## 2. Service Objectives and Architecture

- Business outcome:
- Expected event rate and peak:
- Maximum acceptable processing delay:
- Replay/retention requirement:
- Recovery time and recovery point expectations:
- Data-quality invariants:

```text
Producer -> Kafka topic -> Connect/consumer -> MongoDB
```

List exact topics, groups, connectors, databases, collections, and owners.

## 3. Daily MongoDB Checks

| Check | Command/signal | Normal | Alert/owner | First action |
| --- | --- | --- | --- | --- |
| Writable primary/members | | | | |
| Storage growth/forecast | | | | |
| Important query plans | | | | |
| Index presence/usage | | | | |
| Connections/errors | | | | |
| Backup and restore-test age | | | | |

## 4. Daily Kafka Checks

| Check | Command/signal | Normal | Alert/owner | First action |
| --- | --- | --- | --- | --- |
| Broker/controller | | | | |
| Leaders/replicas/ISR | | | | |
| Disk forecast | | | | |
| Topic configuration | | | | |
| Throughput/skew | | | | |
| Consumer offsets/lag movement | | | | |

## 5. Daily Kafka Connect Checks

| Check | Command/signal | Normal | Alert/owner | First action |
| --- | --- | --- | --- | --- |
| Worker REST/membership | | | | |
| Connector/task status | | | | |
| Retry/error logs | | | | |
| DLQ movement | | | | |
| Configuration/version drift | | | | |
| Source-to-sink reconciliation | | | | |

## 6. Alert Matrix

| Alert | Condition and duration | Severity | Evidence in notification | Owner/escalation |
| --- | --- | --- | --- | --- |
| | | | | |

## 7. Incident Procedures

For each scenario document detection, triage order, evidence preservation, correction, verification, escalation, and prohibited/risky actions.

### Missing Recent Orders

### MongoDB Query Regression

### MongoDB Capacity Risk

### Kafka Lag or Stalled Group

### Hot/Uneven Partition

### Failed Connector Task

### DLQ Growth or Malformed Record

### Source-to-Sink Data Drift

## 8. Maintenance Procedures

### MongoDB Index Change

### Backup and Restore Validation

### Kafka Topic Configuration Change

### Broker/Database Maintenance

### Connector Configuration or Version Upgrade

For each include baseline, approval, commands, observation window, abort conditions, rollback, and post-change evidence.

## 9. Replay and Data Repair

- Authorization required:
- Source of truth:
- Replay range/key selection:
- Idempotency behavior:
- DLQ correction and audit:
- Count/field reconciliation:
- Completion evidence:

## 10. Security and Access

- Credential storage and rotation:
- TLS/authentication/authorization expectations:
- REST and database network controls:
- Audit/log access:
- Break-glass procedure:

## 11. Completion Checklist

- [ ] Every check has a normal condition and owner.
- [ ] Alerts distinguish availability, performance, capacity, and correctness.
- [ ] Commands use exact scoped resource names.
- [ ] Destructive operations have warnings and verified targets.
- [ ] Recovery includes business-flow verification.
- [ ] Rollback reverses configuration rather than merely restarting.
- [ ] Backup readiness includes a tested restore.
- [ ] DLQ handling includes alerting, ownership, retention, replay, and audit.
- [ ] Single-node lab limitations are separated from production procedure.
