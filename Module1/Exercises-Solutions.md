# Module 1 Exercise Solutions

These are reference solutions. Equivalent evidence-backed approaches are valid. Exact offsets and partition distributions may vary.

## Solution 1: End-to-End Evidence Trail

Prepare and run the flow:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --interval-ms 0
python demo/consumer.py --max-messages 20
```

Topic health and source counts:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic workshop-orders

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic workshop-orders
```

Expected invariant: three partitions have leaders and in-sync replicas; the sum of their end offsets is 20.

Group evidence:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

Expected invariant: `CURRENT-OFFSET` equals `LOG-END-OFFSET`, and `LAG` is zero for every displayed partition.

MongoDB evidence:

```bash
python demo/inspect_mongodb.py stats

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.orders.findOne())'
```

Expected count: 20. Use the Kafka console consumer from walkthrough 01 to locate the selected `order_id`. `customer_id`, `product_id`, `quantity`, `unit_price`, and `created_at` should match. MongoDB additionally contains processing fields.

Production mapping: the Python worker becomes a Connect worker; configuration becomes a sink connector; partition-processing instances become tasks; group/offset evidence is supplemented by Connect REST connector and task status.

### CLI Solution Path

Export and create the CLI resources from `Module1/README.md`, then run the producer and sink pipelines in [walkthrough 01](01-Production-Architecture.md#command-line-implementation-of-the-same-flow). Expected invariants are the same: the three CLI topic end offsets total 20, `$CLI_GROUP` has zero lag, and `workshop.orders_cli` contains 20 documents. The generated CLI IDs begin with `cli-`, making cross-layer tracing straightforward.

## Solution 2: Layered Incident Triage

Healthy-layer evidence:

```bash
docker compose -f kafka/docker-compose.yml ps
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic workshop-orders
python demo/inspect_mongodb.py health
```

The producer already advanced topic offsets. Kafka has leaders, and MongoDB is a writable primary. The worker fails before processing because its MongoDB URI points to unused port `27018`.

Diagnosis:

- Faulty layer: worker/application configuration
- Kafka: healthy, retaining the backlog
- MongoDB: healthy, but receiving no requests from a valid client
- Restart required: none
- Correction owner: connector/worker configuration owner
- Broker/database teams: notify only if organizational procedure requires it

Recover:

```bash
python demo/consumer.py --max-messages 20
python demo/inspect_mongodb.py stats
```

Then describe the group and confirm zero lag. MongoDB should contain 20 documents because Kafka retained the unprocessed source records.

### CLI Solution Path

Use the bad-URI `mongoimport` command in [walkthrough 02](02-Operational-Responsibilities.md#2-inject-the-wrong-mongodb-endpoint). A direct `mongosh` ping to port `27017` succeeds while import to `27018` fails. Kafka end offsets remain unchanged. Rerun the valid CLI sink from walkthrough 01; `$CLI_GROUP` should reach zero lag and `orders_cli` should contain 20 documents. No service restart is required.

## Solution 3: Multi-Symptom Incident

The three primary problems are:

1. `--key-mode hot` sends all 200 valid records to one partition.
2. `--delay-ms 200` limits processing to about five records per second and creates lag.
3. `--inject-invalid` adds a poison record that stops the default worker without committing its offset.

Partition evidence:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic workshop-orders
```

One partition contains the valid burst; the poison record may hash to another partition. The exact partition numbers are not important.

Group and worker evidence:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
python demo/inspect_mongodb.py health
python demo/inspect_mongodb.py stats
```

The worker output identifies malformed JSON at a partition and offset. MongoDB remains healthy. Its document count reflects only successfully processed records and may vary depending on which partition the worker reads first.

Recover while preserving the poison record:

```bash
python demo/consumer.py --on-error dlq
```

After the DLQ message appears and lag drains, stop the consumer. Inspect the DLQ:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic workshop-orders-dlq --from-beginning \
  --max-messages 1 --formatter-property print.headers=true
```

Valid alerts include sustained group lag, no offset movement while end offsets grow, worker exit/task failure, DLQ record count greater than zero, or a partition-throughput imbalance.

### CLI Solution Path

Use the hot-key batch producer and malformed-record commands from [walkthrough 04](04-Typical-Failure-Points.md). `kafka-get-offsets.sh` should show the valid burst concentrated in one CLI partition. The throttled shell sink demonstrates slow downstream progress, while `jq` fails on the malformed record. Preserve the poison record as a JSON envelope in `$CLI_DLQ_TOPIC`.

The CLI diagnosis must additionally flag a guarantee problem: the console consumer may commit independently of `jq` or `mongoimport`, so zero CLI group lag does not prove every MongoDB write succeeded.

## Solution 4: Change Request Review

Problems in the proposal:

- No business justification or measured disk constraint
- Thirty-second retention can remove records needed for delayed consumers and replay
- Dropping an index can turn a support query into a full collection scan
- Command success does not validate behavior
- User complaints are a late detection method
- Restarting services does not reverse topic or index configuration

Pre-change evidence:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-orders --describe
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/inspect_mongodb.py stats
```

Kafka rollback:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-orders \
  --alter --delete-config retention.ms
```

MongoDB rollback after dropping the index:

```bash
python demo/inspect_mongodb.py create-index
```

The native CLI equivalent uses `kafka-configs.sh` with `$CLI_TOPIC` and `mongosh` against `orders_cli`, as shown in walkthrough 03. Its rollback is `--delete-config retention.ms` plus `db.orders_cli.createIndex({customer_id: 1}, {name: "customer_id_1"})`.

Validation should prove the intended effective retention, replay window, query plan, documents examined, index keys examined, and index storage. Suitable abort conditions include unexpected record deletion, rising consumer lag, missing leaders, query regression, or database write errors.

## Solution 5: Maintenance Window and Persistence

One valid setup:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 5 --interval-ms 0
python demo/consumer.py --max-messages 100
python demo/inspect_mongodb.py stats
```

Capture end offsets and group state, then restart:

```bash
docker compose -f kafka/docker-compose.yml restart kafka
docker compose -f kafka/docker-compose.yml up -d --wait
```

Repeat the offset and group commands. End offsets and committed offsets should remain because Kafka uses its named volume.

Publish and process the next batch:

```bash
python demo/producer.py --interval-ms 0
python demo/consumer.py --max-messages 20
```

Expected invariants:

- End offsets increase by 20 in total.
- Committed offsets advance from their pre-restart values.
- Lag returns to zero.
- MongoDB count increases from 100 to 120.

The lab has one broker, so clients lose Kafka availability during restart. A production rolling restart requires healthy replicas and ISR, one broker at a time, controlled leader movement, and post-broker validation.

Example abort conditions:

- Any partition is under-replicated or lacks a leader.
- Consumer lag does not recover after the agreed stabilization period.
- The restarted broker fails health checks or does not rejoin ISR.

### CLI Solution Path

Run the CLI producer and sink until `orders_cli` contains at least 100 documents, then record `$CLI_TOPIC` end offsets and `$CLI_GROUP` committed offsets. After the same Kafka restart, both should remain present. Produce another uniquely suffixed CLI batch and consume it with the same group. The committed offsets must continue from their prior values rather than reset.

## Solution 6: Data Drift Investigation

Availability and lag checks can all be healthy. Audit the expected fields directly:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson({total: db.orders.countDocuments({}), missingRegion: db.orders.countDocuments({region: {$exists: false}}), missingCustomer: db.orders.countDocuments({customer_id: {$exists: false}}), invalidQuantity: db.orders.countDocuments({quantity: {$not: {$gt: 0}}})})'
```

Inspect affected documents by replacing the filter as appropriate:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.orders.find({region: {$exists: false}}).forEach(printjson)'
```

Zero lag proves that the worker advanced through Kafka; it does not prove semantic equivalence between source and sink. The source Kafka event or authoritative transactional system should determine the correct value. Production repair should be auditable and idempotent, using a controlled replay/backfill or approved correction.

Preventive controls include schema validation, required-field checks, source-to-sink reconciliation, change streams/audit logs, DLQ monitoring, and periodic count or checksum comparisons.

For the CLI path, run the same two `mongosh` checks against `db.orders_cli`, or use the ready-made audit in [walkthrough 04](04-Typical-Failure-Points.md#station-e-data-drift). The conclusion is unchanged: zero `$CLI_GROUP` lag proves consumption progress, not field completeness or correctness.

## Solution 7: Operational Readiness Recommendation

A strong checklist includes:

### Routine Checks

- MongoDB primary/member health and connection capacity
- Kafka broker, partition leaders, replicas, and disk
- Topic configuration and retention against approved standards
- Consumer/task state, offset movement, and lag
- Source-to-sink counts and required-field validation

### Actionable Alerts

- Any partition without a leader: Kafka owner, immediate
- Sustained nonzero lag with no committed-offset movement: worker owner
- Worker/task failed or repeatedly restarting: connector owner
- MongoDB not writable primary or write failures: database owner
- DLQ receives records or data-quality audit fails: application/data owner

### Missing-Orders First Response

1. Confirm broker and MongoDB availability.
2. Confirm producer end offsets advance.
3. Check partition health and consumer/task status.
4. Compare committed offsets with end offsets.
5. Review worker/task errors and DLQ.
6. Verify MongoDB count, recent documents, and required fields.
7. Preserve evidence before restart, replay, or correction.

### Kafka Connect Gaps in This Lab

- No worker or connector REST status endpoints
- No plugin installation/version compatibility checks
- No distributed worker coordination or multiple task assignments
- No connector-specific configuration validation or metrics

Answers should assign measurable validation, ownership, and escalation rather than listing commands without operational decisions.

## Solution 8: Python Versus CLI Pipeline

A complete comparison should find:

| Dimension | Python implementation | CLI implementation |
| --- | --- | --- |
| Topic/group/collection | Standard workshop resources | Isolated `*-cli` resources |
| Keying | `customer_id` passed to producer API | `key|JSON` parsed by console producer |
| Transformation | Python dictionary and numeric calculation | `jq` filter |
| MongoDB idempotency | `replace_one` upsert by `order_id` | `mongoimport --mode=upsert --upsertFields=order_id` |
| Normal lag result | Zero after 20 records | Zero after 20 records |
| Write/offset ordering | MongoDB success before synchronous commit | Independent processes with no transaction |
| Invalid JSON | Configurable stop, skip, or DLQ | `jq` failure and manual DLQ preservation |
| Production suitability | Demonstration worker with clearer guarantees, still not Connect | Diagnostic/teaching pipeline only |

Replay the same CLI producer input and consume it with a new CLI group into the same collection. Kafka contains duplicate logical records, but `mongoimport` upserts the same `cli-ORD-*` IDs, leaving the document count unchanged.

Failure test:

1. Point `mongoimport` at port `27018` or stop the final import stage.
2. Observe that the console consumer is a separate process and may still advance offsets.
3. Compare `$CLI_GROUP` lag with the `orders_cli` count.
4. Conclude that Kafka progress alone cannot prove sink durability in this shell design.

The CLI path is excellent for learning protocols, inspecting boundaries, reproducing isolated failures, and ad hoc diagnosis. The Python worker is better for demonstrating controlled commit and error policy. Neither shell glue nor this sample Python worker replaces a supported production connector with monitoring, configuration management, retries, security, and tested delivery semantics.
