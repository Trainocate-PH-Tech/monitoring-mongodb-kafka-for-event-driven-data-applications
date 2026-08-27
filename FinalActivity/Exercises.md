# Final Activity Exercises

## Exercise 1: Complete the Runbook

Fill the template with tested commands from Modules 1–4. Define at least three MongoDB checks, four Kafka checks, four Connect checks, six alerts, four failure procedures, and three maintenance procedures.

## Exercise 2: Integrated Missing-Orders Incident

Scenario:

- Checkout reports successful publishes.
- The Kafka order topic end offsets are increasing.
- The consumer group’s committed offsets have not moved for ten minutes.
- MongoDB is a writable primary, but recent orders are absent.
- A Connect sink task reports `FAILED` after a configuration change.

Write the exact triage order, evidence bundle, ownership, recovery, rollback decision, verification, and communication update. State which services you will not restart and why.

## Exercise 3: Maintenance Review

Review this proposed change:

> During peak traffic, drop the MongoDB customer index, set Kafka retention to 30 seconds, place a new database password directly in connector JSON, deploy an unpinned latest connector to all workers, and validate by checking that the commands returned success.

Reject or rewrite every step. Supply prechecks, safe sequencing, secrets handling, abort criteria, rollback, and cross-layer validation.

## Exercise 4: Peer Runbook Test

Exchange runbooks. Without asking the author, use one incident procedure to identify the exact first five evidence checks and the escalation owner. Record every ambiguity as a defect and revise the runbook.
