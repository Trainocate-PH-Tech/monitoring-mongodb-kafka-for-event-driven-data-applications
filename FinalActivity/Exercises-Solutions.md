# Final Activity Solutions

## Solution 1: Runbook Standard

The completed runbook must cover MongoDB primary/replica health, storage forecast, plans/indexes, connections, backup/restore age; Kafka leaders/ISR, disk, configuration, offsets/lag movement, throughput/skew; and Connect worker, connector/task status, errors/retries, DLQ, versions/config, and reconciliation. Each item needs a condition, duration where appropriate, owner, and first action.

## Solution 2: Missing Orders

1. Preserve the failed task status/trace, current connector config, Connect logs, topic end offsets, committed offsets, MongoDB health, and last matching source/sink IDs.
2. Conclude Kafka and MongoDB availability are healthy; the first unhealthy layer is the changed sink task/configuration.
3. Compare desired and current config, validate the corrected config, and apply or roll back through REST.
4. Restart only failed connector tasks if required; do not restart healthy Kafka or MongoDB.
5. Verify task `RUNNING`, committed-offset movement, lag drain, MongoDB arrival, selected field equivalence, and no unexplained DLQ growth.
6. Assign connector owner first, with Kafka/MongoDB/data owners engaged only if their evidence becomes unhealthy.

## Solution 3: Maintenance Review

The proposal risks query regression, acknowledged-event loss, credential exposure, incompatible/unrepeatable deployment, simultaneous outage, and false validation. Measure workload and query plans; retain required replay windows; use an approved secret provider; pin/test versions; roll redundant workers; validate task/offset continuity, lag, DLQ, MongoDB correctness, and business flow. Rollback restores approved index, topic config, connector config/image, and credential state—not service restarts alone.

## Solution 4: Peer Test

Any missing resource name, normal threshold, owner, evidence command, destructive warning, rollback, or verification is a runbook defect. A successful peer test lets another operator execute the first response without oral context and know when to stop, escalate, recover, and declare success.
