# Module 4 Exercises

Submit REST or Python commands, connector/task evidence, logs where relevant, root cause, correction, and end-to-end verification.

## Exercise 1: Layered Health Report

Report worker REST health, installed MongoDB plugin versions, connector states, every task state, Connect internal topics, CDC topic offsets, DLQ offsets, and source/sink counts. Explain what each layer does not prove.

## Exercise 2: End-to-End Trace

Insert five uniquely identified source documents. Trace one `order_id` through source collection, Kafka topic, and sink collection. Reconcile counts and fields and document the expected asynchronous delay.

## Exercise 3: Misconfiguration Triage

Attempt the bad-URI change and prove it was rejected without replacing the approved configuration. Then apply `sink-strict.json`, publish malformed JSON, identify the failed task without restarting Kafka or MongoDB, preserve its trace/log evidence, restore `sink.json`, and prove DLQ plus valid-record recovery.

## Exercise 4: Malformed Record Policy

Publish malformed JSON. Prove the DLQ gained a record with context, the sink task remained healthy, and subsequent valid data arrived. Propose ownership, alerting, retention, replay, and audit controls for the DLQ.

## Exercise 5: Change and Upgrade Review

Review a proposal to edit connector configuration directly in production, place credentials in JSON, rebuild with an unpinned latest plugin, and restart all workers together. Replace it with a complete change, validation, rollback, and credential-handling procedure.

## Exercise 6: Connector Alert Matrix

Define alerts for worker loss, failed tasks, stalled movement, retry exhaustion, DLQ growth, config drift, and source-to-sink mismatch. Include duration, evidence, severity, owner, and first action.
