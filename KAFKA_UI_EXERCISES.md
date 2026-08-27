# Independent Kafka UI Exercises

These exercises introduce Apache Kafka through Kafbat UI before learners complete the command-line-focused Module 3 labs. They are independent of `lab1.md`, `lab2.md`, `lab3.md`, and `Module3/Exercises.md`.

Use only these resources:

| Resource | Name |
| --- | --- |
| Main topic | `kafbat-ui-events` |
| Lifecycle topic | `kafbat-ui-lifecycle` |
| Consumer group | `kafbat-ui-exercise-group` |
| Kafbat cluster | `workshop` |
| Kafbat URL | `http://localhost:8080` |

Do not edit or delete `workshop-orders`, `workshop-orders-dlq`, `workshop-lifecycle`, Kafka Connect internal topics, or another group.

## Submission Requirements

For each exercise, record:

- the UI page and resource inspected;
- screenshots or copied values for the required evidence;
- the matching verification command and its output;
- an interpretation of what the evidence proves;
- one fact the evidence does not prove;
- any change, rollback, and final cleanup result.

## Prerequisites

Start Kafka and Kafbat UI:

```bash
docker compose -f kafka/docker-compose.yml up -d --wait
```

Verify both services:

```bash
docker compose -f kafka/docker-compose.yml ps
curl -fsS http://localhost:8080/actuator/health
```

Expected Kafbat response:

```json
{"status":"UP"}
```

Open `http://localhost:8080` and select the `workshop` cluster.

### Optional Scoped Reset Before Starting

Use this reset only if a previous attempt left the three named exercise resources. Stop any consumer using the exercise group first.

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --delete --group kafbat-ui-exercise-group \
  2>/dev/null || true

for topic in kafbat-ui-events kafbat-ui-lifecycle; do
  docker compose -f kafka/docker-compose.yml exec kafka \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --delete --if-exists --topic "$topic"
done
```

This reset targets only the independent exercise resources.

## Exercise 1: Visual Cluster Health Report

### Goal

Use Kafbat to build an initial cluster-health statement without changing Kafka.

### UI Tasks

1. Select the `workshop` cluster.
2. Record cluster status, controller mode, broker count, topic count, online-partition count, and read-only status.
3. Open the broker view and identify broker/node `1`.
4. Open the topic list and identify at least one user topic and one internal topic.
5. Explain why internal topics should not be changed during the workshop.

### Command Verification

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

### Required Interpretation

Explain why an `ONLINE` Kafbat cluster and a responding broker do not prove:

- consumer progress;
- downstream MongoDB correctness;
- adequate disk capacity;
- redundant Kafka availability.

## Exercise 2: Create and Verify a Topic

### Goal

Create one isolated three-partition topic and verify its structure.

### UI Tasks

1. Open **Topics**.
2. Select the create/add-topic control.
3. Create:

   | Setting | Value |
   | --- | --- |
   | Name | `kafbat-ui-events` |
   | Partitions | `3` |
   | Replication factor | `1` |
   | Cleanup policy | `delete` or inherited default |

4. Open the topic overview.
5. Record every partition, leader, replica set, ISR, earliest offset, and latest offset.

### Expected UI Evidence

- Exactly three partitions exist.
- Every partition has a leader.
- Broker `1` is the only replica and ISR member.
- A newly created topic has no retained exercise records.

### Command Verification

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic kafbat-ui-events

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

### Discussion

Why is replication factor one suitable only for this local exercise? What additional evidence would be required in a production cluster?

## Exercise 3: Produce Keyed JSON Records

### Goal

Use the UI to produce six records and observe their Kafka metadata.

### UI Tasks

Open `kafbat-ui-events`, select **Messages**, and use the produce-message control for each row below. Use the Key column as the record key and the Value column as the record value.

| Key | Value |
| --- | --- |
| `CUST-1001` | `{"event_type":"order.created","order_id":"UI-1001-A","customer_id":"CUST-1001","quantity":1}` |
| `CUST-1001` | `{"event_type":"order.created","order_id":"UI-1001-B","customer_id":"CUST-1001","quantity":2}` |
| `CUST-1002` | `{"event_type":"order.created","order_id":"UI-1002-A","customer_id":"CUST-1002","quantity":1}` |
| `CUST-1002` | `{"event_type":"order.created","order_id":"UI-1002-B","customer_id":"CUST-1002","quantity":3}` |
| `CUST-1003` | `{"event_type":"order.created","order_id":"UI-1003-A","customer_id":"CUST-1003","quantity":1}` |
| `CUST-1003` | `{"event_type":"order.created","order_id":"UI-1003-B","customer_id":"CUST-1003","quantity":2}` |

Add this header to at least one record:

| Header | Value |
| --- | --- |
| `source` | `kafbat-ui-exercise` |

### Required Evidence

For each record, record:

- key;
- partition;
- offset;
- timestamp;
- value;
- header when present.

### Command Verification

The total end-offset increase should be six:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

Read all six records independently:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events \
  --from-beginning --max-messages 6 \
  --property print.key=true \
  --property print.headers=true \
  --property print.partition=true \
  --property print.offset=true \
  --property key.separator=' | '
```

### Discussion

Explain why:

- the two records for one customer must use the same partition;
- three different customer keys need not produce a perfectly even distribution;
- a JSON-looking value is still only bytes to Kafka.

## Exercise 4: Inspect Partitions and Message Placement

### Goal

Use visual evidence to connect message keys, partition placement, ordering, and offset growth.

### UI Tasks

1. Open the partition view for `kafbat-ui-events`.
2. Record each partition's earliest offset, latest offset, and approximate record count.
3. Open the message browser for each partition containing records.
4. Confirm that both `CUST-1001` records share one partition and have increasing offsets.
5. Repeat for `CUST-1002` and `CUST-1003`.
6. Calculate:

   ```text
   partition skew ratio = maximum partition record count / average partition record count
   ```

### Command Verification

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

### Required Interpretation

State whether the six-record observation demonstrates a hot partition or merely a small sample. Do not claim broker pressure without CPU, disk, latency, or error evidence.

## Exercise 5: Create, Observe, and Drain Consumer Lag

### Goal

Create durable consumer-group progress, observe a partial backlog in Kafbat, then drain it.

### Create Partial Progress

Use a bounded console consumer to process only two of the six records:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events \
  --group kafbat-ui-exercise-group \
  --from-beginning --max-messages 2 \
  --consumer-property enable.auto.commit=true \
  --consumer-property auto.commit.interval.ms=100
```

### UI Tasks

1. Open the consumer-groups/consumers view.
2. Select `kafbat-ui-exercise-group`.
3. Record every partition's committed offset, log-end offset, and lag.
4. Record total lag.
5. Refresh once after several seconds and determine whether offsets are moving.

The group should be inactive after the bounded consumer exits, with durable committed offsets and remaining lag.

### Command Verification

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group kafbat-ui-exercise-group --describe
```

### Drain the Backlog

Consume the remaining records using the same group. The exact number remaining is the total lag reported above; if the initial six-record exercise state is intact, it should be four.

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events \
  --group kafbat-ui-exercise-group \
  --max-messages 4 \
  --consumer-property enable.auto.commit=true \
  --consumer-property auto.commit.interval.ms=100
```

Refresh the group in Kafbat and verify total lag reaches zero.

### Required Interpretation

Explain why:

- inactive membership does not erase committed progress;
- lag is calculated per partition;
- zero lag does not prove a downstream database contains correct data.

## Exercise 6: Review and Roll Back a Lifecycle Change

### Goal

Apply a reviewed topic-level retention override to an isolated topic and then remove it.

### Create the Lifecycle Topic

In Kafbat, create:

| Setting | Value |
| --- | --- |
| Name | `kafbat-ui-lifecycle` |
| Partitions | `3` |
| Replication factor | `1` |

Open its configuration/settings view and capture the baseline. Identify whether `retention.ms` and `cleanup.policy` are explicit topic overrides or inherited defaults.

### Apply the Reviewed Override

Set:

```text
retention.ms = 604800000
```

This represents seven days.

Save the change and verify it independently:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name kafbat-ui-lifecycle --describe
```

### Roll Back

Use the UI's reset/remove-override control for `retention.ms`. Do not replace the old inherited state with a guessed number.

Verify that the dynamic topic override is absent:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name kafbat-ui-lifecycle --describe
```

### Change Review

Reject a proposal to set `retention.ms=30000` on `workshop-orders`. Explain the replay, outage, consumer-lag, and downstream-recovery risks.

## Exercise 7: Diagnose a UI-Only Failure

### Goal

Prove that losing the administration UI does not mean the Kafka broker is down.

### Capture the Healthy Baseline

```bash
curl -fsS http://localhost:8080/actuator/health

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

### Stop Only Kafbat

```bash
docker compose -f kafka/docker-compose.yml stop kafbat-ui
```

Observe:

- the browser page is unavailable;
- the Kafbat health request fails;
- the Kafka service remains healthy;
- the exercise topic and offsets remain available through Kafka tools.

```bash
docker compose -f kafka/docker-compose.yml ps

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic kafbat-ui-events
```

### Recover Only the Failed Layer

```bash
docker compose -f kafka/docker-compose.yml start kafbat-ui
docker compose -f kafka/docker-compose.yml up -d --wait
curl -fsS http://localhost:8080/actuator/health
```

Refresh the UI and confirm the topics, records, and group state remain visible.

### Required Interpretation

Explain why restarting Kafka would have added risk without addressing the failed UI layer.

## Exercise 8: Scoped Cleanup and Final Report

### Goal

Delete only the exercise resources and prove that shared course resources remain.

### Pre-Cleanup Evidence

Record:

- both topic names;
- `kafbat-ui-events` partition/end-offset totals;
- the consumer group's final committed offsets and lag;
- final `retention.ms` override state on `kafbat-ui-lifecycle`.

### UI Cleanup

1. Confirm no consumer is actively using `kafbat-ui-exercise-group`.
2. Delete the inactive group through the consumer-group view if the control is available.
3. Delete `kafbat-ui-events`.
4. Delete `kafbat-ui-lifecycle`.
5. Do not select any other topic or group.

If the UI does not offer inactive-group deletion, delete only that exact group through Kafka:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --delete --group kafbat-ui-exercise-group
```

### Verification

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --list
```

The three `kafbat-ui-*` resources must be absent. Existing `workshop-*` and internal resources must remain.

## Completion Checklist

- [ ] Both Kafka and Kafbat became healthy.
- [ ] The cluster overview was interpreted without overstating what it proves.
- [ ] `kafbat-ui-events` was created with three partitions and replication factor one.
- [ ] Six keyed records were produced and traced by partition and offset.
- [ ] Same-key partition placement was verified.
- [ ] A named consumer group showed partial lag and then zero lag.
- [ ] A seven-day retention override was applied and removed on the isolated lifecycle topic.
- [ ] A Kafbat-only outage was diagnosed without restarting Kafka.
- [ ] Only the independent exercise topics and group were deleted.
- [ ] UI evidence was corroborated with repeatable Kafka commands.
