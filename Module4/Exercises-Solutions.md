# Module 4 Exercise Solutions

## Solution 1: Layered Health Report

Use REST root/plugins, `connect_admin.py list`, Kafka topic/group commands, and MongoDB counts. REST availability proves only the worker API. `RUNNING` connector status is incomplete without every task. Kafka offsets prove movement, not sink correctness. Equal counts still require sampled field reconciliation.

## Solution 2: End-to-End Trace

Use walkthrough 04 with five unique `order_id` values. Record the source `_id`, CDC topic/partition/offset where available, connector/task status, and sink document. Poll with a bounded wait rather than assuming immediate delivery. Expected invariant: all five arrive with matching business fields and no new DLQ record.

## Solution 3: Misconfiguration Triage

Connector validation rejects `mongodb:27018`, leaving the approved URI and running task unchanged. The strict error policy then makes the malformed record fail the sink task at the value-converter stage. Kafka leaders, worker, source connector, and MongoDB primary remain healthy. Save `/status` trace and logs, apply `sink.json`, restart failed tasks if needed, wait for `RUNNING`, and prove the poison record reaches the DLQ while subsequent valid data reaches `connector_sink`.

## Solution 4: Malformed Record Policy

With `errors.tolerance=all`, the JSON conversion error is routed to `workshop-connect-dlq` with context headers and the task continues. Verify a valid source insert afterward. Production controls need immediate DLQ-growth alerting, restricted access, sufficient retention, accountable remediation, idempotent replay, and an audit linking the repaired event to its original topic/partition/offset.

## Solution 5: Change and Upgrade Review

Version-control and review config; validate through `/config/validate`; externalize credentials; pin worker/plugin versions and image digests; test compatibility; capture configs/status/offsets/DLQ/reconciliation; roll redundant workers; verify continuity; and define explicit abort/rollback. A restart does not roll back stored connector configuration.

## Solution 6: Connector Alert Matrix

Strong answers separate worker API loss, connector/task failure, no offset movement, growing lag, retry exhaustion, DLQ growth, unauthorized config differences, and reconciliation mismatch. Each identifies whether the worker, connector owner, MongoDB owner, Kafka owner, or data owner responds first and includes the exact status/log/offset evidence to gather.
