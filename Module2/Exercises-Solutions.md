# Module 2 Exercise Solutions

Equivalent evidence-backed answers are valid; exact byte counts vary.

## Solution 1: Growth Forecast

Use `monitor_mongodb.py snapshot` at both points and `du -sh /data/db`. Subtract the initial values. Forecast with `remaining bytes / observed bytes per hour`. Collection `size`, allocated `storageSize`, index storage, journal, oplog, and filesystem allocation measure different things, so they must not be forced to reconcile exactly.

## Solution 2: Unknown Query Regression

The expected plan is `COLLSCAN`. Evidence should show `workshop.orders`, the `customer_id` filter, `docsExamined` far above `nreturned`, and the matching `executionStats`. Disable profiling with `db.setProfilingLevel(0)`. A good alert targets a sustained examined/returned ratio or latency for that query shape, not one profiler entry.

## Solution 3: Index Change Review

The approved command is:

```bash
python demo/inspect_mongodb.py create-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/monitor_mongodb.py index-usage
```

Expected change: `COLLSCAN` becomes `IXSCAN`, returned results remain identical, and examined work falls close to returned rows. Record index-byte growth. Roll back with `python demo/inspect_mongodb.py drop-index` if an agreed write, storage, or query regression boundary is crossed.

## Solution 4: Restore Readiness

Use the archive and namespace-remap commands in walkthrough 04. Source/restored counts and index definitions must match. The drill proves logical backup readability and a local restore procedure; it does not prove off-host durability, encryption/key access, point-in-time oplog coverage, production-scale RTO, or automated retention.

## Solution 5: Capacity Incident

Preserve snapshots, growth source, disk/filesystem state, top namespaces, oplog/backup consumption, and recent changes. Escalate to DBA/platform owners, stop nonessential growth only through approved controls, add capacity, and protect backup/replication requirements. Do not delete data files, shrink retention blindly, drop indexes without workload evidence, or restart to “free disk.” Validate write health and revised forecast.

## Solution 6: MongoDB Health Checklist

A strong checklist includes writable-primary/member state, optime lag, connections, collection/index growth, filesystem forecast, important query plans, examined/returned ratios, index usage, assertions/errors, backup success, and restore-test age. Alerts must name a sustained condition, service/namespace, owner, severity, and first evidence command.
