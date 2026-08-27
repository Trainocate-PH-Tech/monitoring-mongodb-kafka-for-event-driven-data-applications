# Module 1 Exercises

Complete these exercises without opening `Exercises-Solutions.md`. Commands are run from the repository root with the Python virtual environment active.

Unless an exercise explicitly specifies an implementation, students may use Python, native CLI tools, or both. Identify the chosen path in the submission. CLI work uses the isolated resources and exports defined in `Module1/README.md`.

## Submission Requirements

For every exercise, submit:

1. Commands used
2. Relevant output or observations
3. Diagnosis and affected layer
4. Recovery or recommendation
5. Verification that proves the result
6. Proposed owner and alert
7. Implementation used: Python, CLI, or both

Exact offsets can vary. Unsupported conclusions such as “Kafka is broken” or “restart everything” receive no credit.

## Exercise 1: End-to-End Evidence Trail

Reset the demo, publish one dataset, and process it.

Prove all of the following without relying only on application success messages:

- The topic has three healthy partitions.
- Exactly 20 source records were appended across the partitions.
- The processing group committed through every source partition it consumed.
- Consumer lag is zero.
- MongoDB contains 20 order documents.
- One selected `order_id` exists in both Kafka and MongoDB with matching business fields.

Deliver an evidence table and explain where a Kafka Connect connector and task would appear in the same production flow.

## Exercise 2: Layered Incident Triage

Prepare 20 Kafka records, but do not process them. Then run this faulty worker configuration:

Linux or macOS:

```bash
MONGODB_URI='mongodb://localhost:27018/?directConnection=true' \
  python demo/consumer.py
```

**Expected observable behavior:** the command must fail with a `27018` connection/server-selection error. Interpret which layer that implicates; do not treat the failure text as the exercise's diagnosis.

Windows PowerShell:

```powershell
$env:MONGODB_URI='mongodb://localhost:27018/?directConnection=true'
python demo/consumer.py
Remove-Item Env:MONGODB_URI
```

**Expected observable behavior:** Python reports the same bad-port failure; removing the environment override is normally silent.

Determine:

- Which layers remain healthy?
- Which layer contains the fault?
- Why are orders absent from MongoDB?
- Which service, if any, should be restarted?
- Which team owns the correction and which teams only need notification?

Recover the pipeline and prove that all original records were processed exactly once as MongoDB documents.

## Exercise 3: Multi-Symptom Incident

Create the incident:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 10 --interval-ms 0 \
  --key-mode hot --inject-invalid
python demo/consumer.py --delay-ms 200
```

**Expected observable behavior:** 201 records are published (200 valid plus one malformed); valid work is concentrated by the hot key; the delayed worker eventually stops on an invalid-event error. Your task is to correlate those observations with partition, group, and MongoDB evidence.

The incident contains at least three independent operational problems. Diagnose each one and separate root causes from symptoms.

Required deliverables:

- Per-partition workload evidence
- Consumer-group evidence
- Worker failure evidence
- MongoDB health and document evidence
- A recovery sequence that preserves the poison record for investigation
- Proof that the group eventually reaches zero lag
- Two alerts that would detect different parts of the incident

## Exercise 4: Change Request Review

A proposed change contains these instructions:

> During peak traffic, set `workshop-orders` retention to 30 seconds and drop the `customer_id_1` MongoDB index to save disk space. Validation: “commands completed successfully.” Rollback: “restart Kafka and MongoDB if users complain.”

Review the request and produce a corrected change plan. Your answer must include:

- Business objective and missing justification
- Separate risks for Kafka retention and MongoDB indexing
- Pre-change evidence
- Measurable validation
- Exact rollback commands
- Abort conditions
- Appropriate maintenance timing
- Why restarting both services is not a valid rollback

Safely demonstrate both changes in the lab, roll them back, and provide before-and-after evidence.

## Exercise 5: Maintenance Window and Persistence

Create and fully process at least 100 orders. Record MongoDB count, topic end offsets, committed group offsets, and lag.

Simulate a Kafka maintenance restart. After recovery:

- Prove that source records remain present.
- Prove that committed offsets remain present.
- Publish and process another 20 orders.
- Prove that processing resumes from the prior offsets.
- Explain why the local restart causes an outage and how a production rolling restart changes the plan.

Write three abort conditions that would stop a production maintenance window.

## Exercise 6: Data Drift Investigation

Create a healthy 20-document dataset. Ask another student or the instructor to introduce one downstream data defect using a MongoDB update without telling you which document was changed.

Determine:

- Whether Kafka, the worker, and MongoDB availability are healthy
- Which required field or value drifted
- How many documents are affected
- Why zero consumer lag does not prove data correctness
- The safest source of truth and repair method
- What automated control could detect recurrence

Do not reset the environment until you have preserved evidence of the defect.

## Exercise 7: Operational Readiness Recommendation

Using evidence from the earlier exercises, write a concise Module 1 operational checklist containing:

- Five routine health checks across all layers
- Five actionable alerts with thresholds or conditions
- An escalation owner for each alert
- A maintenance change template
- A first-response sequence for “orders are missing”
- Three gaps that remain because this lab uses a Python worker instead of a real Kafka Connect deployment

The checklist must distinguish availability, performance, backlog, processing failure, and data correctness.

## Exercise 8: Python Versus CLI Pipeline

Run the same 20 logical dummy orders through both implementations:

- Python: `workshop-orders` → `workshop-order-processor` → `workshop.orders`
- CLI: `workshop-orders-cli` → `workshop-order-processor-cli` → `workshop.orders_cli`

Compare and submit evidence for:

- Topic partition counts and message distribution
- Group committed offsets and lag
- MongoDB document counts and shapes
- Idempotent replay of the same order IDs
- Behavior when MongoDB import fails
- Behavior when one malformed JSON record is consumed
- DLQ preservation and source-offset implications

Conclude which implementation is appropriate for teaching, troubleshooting, and production. Your answer must specifically explain why a successful shell command pipeline does not provide the same delivery guarantee as the Python worker.
