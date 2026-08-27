# Module 2 Exercises

Complete these without opening the solutions. Submit commands, raw evidence, interpretation, recovery/rollback, and verification. Use Python and native commands where both exist.

## Exercise 1: Growth Forecast

Measure `workshop.orders` before and after adding 400 documents. Calculate bytes and documents added, identify why filesystem and collection growth differ, and forecast the time to a hypothetical 2 GiB operational limit at the observed hourly rate.

## Exercise 2: Unknown Query Regression

With `customer_id_1` absent, enable profiling only long enough to capture a customer lookup. Identify the namespace, query shape, plan summary, returned documents, examined documents, and efficiency ratio. Disable profiling and propose an alert that avoids noise.

## Exercise 3: Index Change Review

Prepare a change record for `customer_id_1` containing justification, baseline, expected benefit, cost/risk, validation, abort condition, and rollback. Apply it and prove both result correctness and plan improvement. Then inspect its usage counter.

## Exercise 4: Restore Readiness

Back up `workshop`, restore it as `workshop_restore`, and prove document and index equivalence. Explain what this local drill does not prove about point-in-time recovery, encryption, off-host copies, retention, and recovery time.

## Exercise 5: Capacity Incident

Assume disk growth accelerated tenfold and the remaining capacity will be exhausted in six hours. Produce a first-response plan that preserves evidence, names safe mitigations, defines escalation, and rejects at least two risky reactions.

## Exercise 6: MongoDB Health Checklist

Create a daily checklist covering storage, indexes, query behavior, replication, connections, backups, and logs. For four checks, define an actionable alert with duration, owner, and first action.
