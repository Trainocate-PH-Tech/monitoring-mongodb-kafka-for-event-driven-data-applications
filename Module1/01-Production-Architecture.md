# Walkthrough 01: Production Event-Driven Architecture

## Course-Outline Topic

How MongoDB, Kafka, and Kafka Connect work together in production event-driven systems.

## Goal

Produce orders, process them, and collect evidence from every layer. The exercise uses the Python consumer as a Kafka Connect sink-worker analogue.

## 1. Prepare a Known State

```bash
python demo/setup_demo.py --reset
```

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

Confirm that the topic has three partitions, one leader per partition, and end offsets of zero.

## 2. Publish the Source Events

```bash
python demo/producer.py --interval-ms 0
```

The producer should report 20 expected and delivered records. Inspect the new end offsets:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic workshop-orders
```

The sum of the three end offsets should be 20. Events with the same `customer_id` use the same message key and therefore remain ordered within one partition.

## 3. Run the Sink Worker

```bash
python demo/consumer.py --max-messages 20
```

The consumer reads Kafka records, calculates `total_amount`, upserts each `order_id` into MongoDB, and commits each source offset after the MongoDB write succeeds.

Inspect the consumer group:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

For every displayed partition, `CURRENT-OFFSET` should equal `LOG-END-OFFSET`, producing zero lag.

## 4. Verify MongoDB

```bash
python demo/inspect_mongodb.py stats
```

The collection should contain 20 documents. Display one document:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.orders.findOne())'
```

Identify its `event_id`, `order_id`, `customer_id`, `created_at`, `processed_at`, and computed `total_amount`.

## 5. Trace an Event Across Layers

Choose an `order_id` from MongoDB. Read the Kafka records and locate the same value in the JSON output:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic workshop-orders --from-beginning \
  --timeout-ms 5000 \
  --formatter-property print.key=true \
  --formatter-property key.separator=' | '
```

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

Verify that the sum of end offsets is 20:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic "$CLI_TOPIC"
```

### 2. Consume, Transform, and Upsert

The console consumer emits JSON values. `jq` adds the processing fields, and `mongoimport` upserts by `order_id`.

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
