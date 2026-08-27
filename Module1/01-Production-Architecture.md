# Walkthrough 01: Production Event-Driven Architecture

## Course-Outline Topic

How MongoDB, Kafka, and Kafka Connect work together in production event-driven systems.

## Goal

Produce orders, process them, and collect evidence from every layer. The exercise uses the Python consumer as a Kafka Connect sink-worker analogue.

## Terms Used in This Walkthrough

| Term | Meaning in this workshop |
| --- | --- |
| Event-driven application | An application whose components communicate by publishing and reacting to events instead of requiring every component to respond in the same request. |
| Event, message, or record | The JSON description of something that happened. Here, one Kafka record represents one `order.created` event. These terms are used interchangeably in this introductory lab. |
| Producer | A program that publishes records to Kafka. `producer.py` and `kafka-console-producer.sh` are producers. |
| Broker | A Kafka server that stores records and serves producer and consumer requests. This lab has one broker. |
| Topic | A named stream of Kafka records. The Python flow uses `workshop-orders`. A topic is divided into partitions. |
| Partition | An ordered, append-only portion of a topic. Records are ordered within a partition, but Kafka provides no global order across all partitions. |
| Message key | A value used to choose a partition. This lab uses `customer_id`, keeping a customer's orders together and ordered within that partition. |
| Leader | The broker currently serving reads and writes for a partition. Every usable partition needs a leader. |
| Replica and ISR | A replica is a copy of a partition; ISR means in-sync replicas. The one-broker lab has one replica per partition and cannot demonstrate redundant failover. |
| Offset | A record's position within one partition. Offset numbers are local to a partition, not to the entire topic. |
| End offset | The next offset that would be assigned in a partition. On a new topic without deletions, the sum of end offsets equals the number of records published. |
| Consumer | A program that reads Kafka records. `consumer.py` and `kafka-console-consumer.sh` are consumers. |
| Consumer group | Consumers sharing a group ID coordinate partition ownership and saved progress. This lab uses `workshop-order-processor`. |
| Committed offset | The saved next-read position for a consumer group and partition. It lets a restarted consumer resume instead of always starting over. |
| Consumer lag | `log end offset - committed offset`. It estimates how many records remain for a group to process. |
| Source and sink | A source is where data comes from; a sink is where it is written. Kafka is the source for this consumer, and MongoDB is its sink. |
| Worker or task | The process or unit of work that moves and transforms records. `consumer.py` stands in for a Kafka Connect sink task in Modules 1–3. |
| Document and collection | A MongoDB document is one stored JSON-like object. A collection groups documents; this flow writes to `workshop.orders`. |
| Upsert | “Update or insert.” If a matching `order_id` exists, replace/update it; otherwise insert a new document. |
| Idempotent write | An operation that can be repeated with the same logical input without creating additional logical results. Upserting by `order_id` makes replay safer. |
| Replay | Reading and processing retained Kafka records again, usually for recovery or rebuilding downstream data. |
| DLQ | Dead-letter queue: a separate Kafka topic that preserves records the normal path could not process, together with error context. |

In one sentence, the flow is: a **producer** appends keyed **records** to a partitioned Kafka **topic**, a **consumer group** tracks processing with committed **offsets**, and a sink worker **upserts** MongoDB **documents** by `order_id`.

## 1. Prepare a Known State

```bash
python demo/setup_demo.py --reset
```

Representative output:

```text
[ok] MongoDB is reachable
[reset] Dropped MongoDB collection workshop.orders
[reset] Deleted Kafka topic 'workshop-orders'
[reset] Deleted Kafka topic 'workshop-orders-dlq'
[ok] Created Kafka topic 'workshop-orders' with 3 partitions
[ok] Created Kafka topic 'workshop-orders-dlq' with 1 partitions
[ok] Kafka topic 'workshop-orders' is ready (3 partitions)
[ok] Kafka topic 'workshop-orders-dlq' is ready (1 partitions)
[ready] The workshop demo is ready
```

What it means: MongoDB and Kafka are reachable; only the workshop collection and topics were reset; the source topic now has three empty partitions. If a topic did not previously exist, its `[reset] Deleted` line may be absent.

Describe the Kafka topic before any orders exist:

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

Representative topic description:

```text
Topic: workshop-orders  PartitionCount: 3  ReplicationFactor: 1
Topic: workshop-orders  Partition: 0  Leader: 1  Replicas: 1  Isr: 1
Topic: workshop-orders  Partition: 1  Leader: 1  Replicas: 1  Isr: 1
Topic: workshop-orders  Partition: 2  Leader: 1  Replicas: 1  Isr: 1
```

What it means: the topic is divided into three partitions; broker 1 leads every partition; the only replica is currently in sync. Replication factor 1 is appropriate only for this local lab because it provides no redundant copy.

Expected offset output immediately after reset:

```text
workshop-orders:0:0
workshop-orders:1:0
workshop-orders:2:0
```

What it means: the fields are `topic:partition:end-offset`. All three next-write positions are zero, so the clean topic contains no records.

Confirm that the topic has three partitions, one leader per partition, and end offsets of zero.

The topic description is structural evidence: it proves partitions have leaders and in-sync replicas. It does not prove that a producer, consumer, or MongoDB is healthy.

## 2. Publish the Source Events

```bash
python demo/producer.py --interval-ms 0
```

Expected output:

```text
[done] expected=20 delivered=20 failed=0 unflushed=0 topic=workshop-orders
```

What it means: the producer attempted 20 records, Kafka acknowledged all 20, none failed, and none remained buffered locally. This proves delivery to Kafka, not processing by the consumer or storage in MongoDB.

The producer should report 20 expected and delivered records. Inspect the new end offsets:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic workshop-orders
```

Representative output:

```text
workshop-orders:0:4
workshop-orders:1:4
workshop-orders:2:12
```

What it means: the partitions contain 4, 4, and 12 appended records respectively, for a total of 20. The exact distribution may differ, but the sum must be 20 after one run from a clean reset.

The sum of the three end offsets should be 20. Events with the same `customer_id` use the same message key and therefore remain ordered within one partition.

Kafka appends rather than overwrites records. Running the producer twice adds another 20 records; it does not replace the first batch. Use the reset command before this walkthrough when an exact count matters.

## 3. Run the Sink Worker

```bash
python demo/consumer.py --max-messages 20
```

Representative output:

```text
[ready] Consuming 'workshop-orders' as group 'workshop-order-processor'; press Ctrl+C to stop
[progress] processed=1 partition=1 offset=0
[progress] processed=10 partition=0 offset=5
[progress] processed=20 partition=2 offset=11
[done] consumed=20 processed=20 rejected=0
```

What it means: the consumer joined the named group, examined 20 records, successfully transformed and wrote all 20, and rejected none. Partition and offset values vary because records from different partitions can be processed in different orders.

The consumer reads Kafka records, calculates `total_amount`, and performs an **upsert** for each `order_id`: it replaces a matching order document or inserts one when no match exists. Only after MongoDB accepts the write does it **commit the offset**, saving the consumer group's progress. This write-before-commit order reduces the risk of recording Kafka progress before the sink write succeeds.

Inspect the consumer group:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

Representative output, shortened to the relevant columns:

```text
GROUP                       TOPIC             PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
workshop-order-processor    workshop-orders   0          4               4               0
workshop-order-processor    workshop-orders   1          4               4               0
workshop-order-processor    workshop-orders   2          12              12              0
```

The command may first report that the group has no active members. That is normal after the bounded consumer exits; its committed offsets remain available.

What it means: every committed next-read position has caught up with its partition's end offset. The group has no Kafka backlog.

For every displayed partition:

- `CURRENT-OFFSET` is the consumer group's committed next-read position.
- `LOG-END-OFFSET` is Kafka's next-write position for that partition.
- `LAG` is the difference between them.

`CURRENT-OFFSET` should equal `LOG-END-OFFSET`, producing zero lag. Zero lag proves that the group advanced through the records; it does not by itself prove that the MongoDB documents are complete or correct.

## 4. Verify MongoDB

```bash
python demo/inspect_mongodb.py stats
```

Representative output:

```text
documents: 20
storage bytes: 4096
total index bytes: 4096
indexes:
  - _id_: {'_id': 1}
```

What it means: MongoDB contains 20 order documents. Storage and index byte counts vary by host and database state; the important invariant here is `documents: 20`. Additional indexes may appear if another walkthrough created them.

The collection should contain 20 documents. Display one document:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.orders.findOne())'
```

Representative output, abbreviated:

```text
{
  _id: ObjectId('...'),
  event_type: 'order.created',
  event_id: '...',
  order_id: 'ORD-1001-<run-id>-001',
  customer_id: 'CUST-1001',
  quantity: 1,
  unit_price: 59.95,
  total_amount: 59.95,
  status: 'received',
  created_at: '...',
  processed_at: ISODate('...')
}
```

What it means: the source business fields and the consumer-added processing fields coexist in one document. `_id`, generated IDs, and timestamps vary. `total_amount`, `status`, and `processed_at` prove that the sink worker transformed the Kafka event before writing it.

Identify its `event_id`, `order_id`, `customer_id`, `created_at`, `processed_at`, and computed `total_amount`.

## 5. Trace an Event Across Layers

Choose an `order_id` from MongoDB. Read the Kafka records and locate the same value in the JSON output:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic workshop-orders --from-beginning \
  --max-messages 20 \
  --formatter-property print.key=true \
  --formatter-property key.separator=' | '
```

Representative output, showing two of the 20 lines:

```text
CUST-1001 | {"customer_id":"CUST-1001",...,"order_id":"ORD-1001-<run-id>-001",...}
CUST-1002 | {"customer_id":"CUST-1002",...,"order_id":"ORD-1002-<run-id>-001",...}
Processed a total of 20 messages
```

What it means: the value before ` | ` is the Kafka message key and the JSON after it is the record value. Locate the MongoDB `order_id` here to prove the same business event exists in both layers. The record order displayed across partitions is not a global business order.

`--from-beginning` starts this diagnostic consumer at the topic's earliest retained records. `--max-messages 20` makes it exit cleanly after the known 20-record batch. This console consumer has no group ID here, so it is inspecting records rather than changing the `workshop-order-processor` group's committed offsets.

For the selected order, record:

| Evidence | Value |
| --- | --- |
| Kafka message key | |
| Kafka partition | Use consumer progress or group evidence |
| `event_id` | |
| `order_id` | |
| MongoDB database and collection | `workshop.orders` |
| MongoDB `processed_at` | |

## Command-Line Implementation of the Same Flow

Export and create the CLI resources as described in [Module 1 setup](README.md#command-line-resource-setup). The commands below implement the same logical producer, consumer, transformation, and MongoDB sink without Python.

In the shell examples, `|` is a **pipeline**: it sends one command's standard output into the next command's standard input. `jq` parses and transforms JSON. Docker Compose `exec -T` runs a command inside a container without allocating an interactive terminal, allowing piped data to pass cleanly.

### 1. Produce Keyed JSON Events

`jq` converts each dummy template into an `order.created` event and prefixes the JSON with its Kafka key. Kafka's console producer parses the text before `|` as the key.

```bash
jq -r '
  . as $source
  | (del(.sample_order_id) + {
      event_type: "order.created",
      event_id: ("cli-event-" + $source.sample_order_id),
      order_id: ("cli-" + $source.sample_order_id),
      created_at: (now | todateiso8601)
    }) as $event
  | $event.customer_id + "|" + ($event | tojson)
' demo/data/orders.jsonl \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
    --reader-property parse.key=true --reader-property key.separator='|'
```

Expected output:

```text
<no output on success>
```

What it means: all 20 `jq` output lines became standard input for the console producer. The console producer does not echo successful acknowledgements. Check its exit status and the topic end offsets for evidence.

Successful console production is normally silent because the generated lines are being sent to Kafka rather than printed. The fixed CLI event and order IDs also mean that rerunning this command appends duplicate logical records to Kafka. The sink's upserts prevent those duplicate IDs from becoming additional MongoDB documents.

Verify that the sum of end offsets is 20:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic "$CLI_TOPIC"
```

Representative output:

```text
workshop-orders-cli:0:4
workshop-orders-cli:1:4
workshop-orders-cli:2:12
```

What it means: the exact partition distribution can vary, but the sum must be 20 after one CLI producer run from a clean CLI reset. A sum of 40 usually means the producer pipeline ran twice.

### 2. Consume, Transform, and Upsert

The console consumer emits JSON values. `jq` adds the processing fields, and `mongoimport` upserts by `order_id`. `--mode=upsert --upsertFields=order_id` is the native-command equivalent of the Python worker's `replace_one(..., upsert=True)` behavior.

```bash
docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
  --group "$CLI_GROUP" --from-beginning --max-messages 20 \
| jq -c '. + {
    total_amount: (.quantity * .unit_price),
    status: "received",
    processed_at: (now | todateiso8601)
  }' \
| docker compose -f mongodb/docker-compose.yml exec -T mongodb \
    mongoimport \
    --uri 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
    --collection "$CLI_COLLECTION" --mode=upsert --upsertFields=order_id
```

Representative output:

```text
connected to: mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true
Processed a total of 20 messages
20 document(s) imported successfully. 0 document(s) failed to import.
```

Kafka may also print an informational consumer-protocol message. It is not a failure.

What it means: the console consumer read 20 records, `jq` transformed them, and `mongoimport` successfully upserted all 20. These are separate processes; the output does not provide the Python worker's write-before-offset-commit guarantee.

### 3. Verify CLI Offsets and Documents

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group "$CLI_GROUP" --describe

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson({count: db.orders_cli.countDocuments({}), sample: db.orders_cli.findOne()})'
```

Representative consumer-group output:

```text
GROUP                           TOPIC                 PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
workshop-order-processor-cli    workshop-orders-cli   0          4               4               0
workshop-order-processor-cli    workshop-orders-cli   1          4               4               0
workshop-order-processor-cli    workshop-orders-cli   2          12              12              0
```

Representative MongoDB output:

```text
{
  count: 20,
  sample: {
    order_id: 'cli-ORD-1001',
    customer_id: 'CUST-1001',
    total_amount: 59.95,
    status: 'received',
    processed_at: '...'
  }
}
```

What it means: the CLI group reports no Kafka backlog and the isolated CLI collection contains 20 transformed documents. These two checks are complementary: lag measures Kafka progress, while the MongoDB query measures sink state.

Expected result: zero CLI group lag and 20 documents in `workshop.orders_cli`.

### 4. Compare the Implementations

| Behavior | Python worker | CLI pipeline |
| --- | --- | --- |
| Keyed production | `Producer.produce()` | `kafka-console-producer.sh` parses `key|JSON` |
| Transformation | Python dictionary logic | `jq` filter |
| Idempotent sink | `replace_one(..., upsert=True)` | `mongoimport --mode=upsert` |
| Offset/write coordination | Commit after MongoDB succeeds | Independent console-consumer and import processes |
| Invalid-event policy | Stop, skip, or DLQ | Shell exit/manual DLQ handling |

The CLI implementation shows each boundary clearly, but a broken downstream pipe can still leave Kafka commit behavior that is not coordinated with MongoDB. Do not treat this pipeline as a production connector.

## Production Interpretation

In a production Kafka Connect deployment, the application producer still writes to Kafka, but a MongoDB sink connector owns one or more tasks that read topic partitions and write MongoDB documents. Operators would add these checks:

- Connect worker process and REST endpoint health
- Connector configuration and status
- Task assignments and task-level failures
- Connector offset movement
- Retry, error-tolerance, and DLQ configuration
- Plugin and worker version compatibility

The data path does not end when Kafka acknowledges a producer. Operational readiness requires evidence that the processing layer advanced its offsets and the database received correct documents.

## Completion Check

Explain why each statement can be true independently:

- Kafka is healthy while MongoDB has no new orders.
- MongoDB is healthy while consumer lag rises.
- The consumer process is running while one partition receives no traffic.
- The producer reports success while the end-to-end business flow is incomplete.
