# Module 3 Exercises

Submit commands, two or more time-separated observations, diagnosis, recovery, and post-recovery proof.

## Exercise 1: Topic Health Report

Produce 2,000 events and report broker reachability, leaders, replicas, ISR, partition end offsets, estimated record throughput, disk usage, and limitations of the measurement.

## Exercise 2: Classify Lag

Create and identify each state without being told its label: fixed backlog draining, stalled consumer, and throughput deficit. Use offset movement rather than process presence alone.

## Exercise 3: Partition Skew

Generate a hot-key batch, calculate the partition skew ratio, explain the capacity consequence, recover with customer keys, and prove improved distribution. State why adding consumers beyond partition count cannot help.

## Exercise 4: Lifecycle Change Review

Review a proposal to set the order topic to `retention.ms=30000` and `cleanup.policy=compact`. Identify semantic and operational risks, define prechecks, test safely on `workshop-lifecycle`, and provide exact rollback.

## Exercise 5: Restart and Persistence

Capture topic and group state, restart the single broker, verify retained records and offsets, then explain the additional checks required for a production rolling restart.

## Exercise 6: Kafka Alert Checklist

Write daily checks and four actionable alerts covering availability, lag movement, disk forecast, skew, lifecycle drift, and throughput. Every alert needs duration, scope, owner, and first action.
