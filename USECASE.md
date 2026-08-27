# Workshop Use Case: Online Order Processing

## Scenario

Northwind Outfitters is a fictional online retailer. When a customer completes checkout, the checkout application publishes an `order.created` event. An order processor consumes the event and stores a queryable order record in MongoDB for support and operations teams.

The workshop uses a small Python producer and consumer in place of production applications. This keeps the business flow visible while learners focus on operating MongoDB and Kafka.

Module 4 additionally runs the official MongoDB Kafka source and sink connectors so learners can inspect real worker, connector, task, REST, retry, and DLQ behavior. It uses isolated `connector_source` and `connector_sink` collections and does not replace the introductory Python flow.

## Architecture

```text
Dummy orders                 Kafka                       MongoDB
orders.jsonl -> producer.py -> workshop-orders topic -> consumer.py -> workshop.orders
                                      |
                                      +-> consumer group: workshop-order-processor
```

The producer keys each event by `customer_id`. Kafka therefore keeps a customer's orders ordered within a partition. The consumer writes each order using `order_id` as an idempotency key, then commits the Kafka offset only after MongoDB accepts the write.

## Event Model

Each Kafka message is JSON and contains:

| Field | Purpose |
| --- | --- |
| `event_type` | Identifies the event as `order.created`. |
| `event_id` | Uniquely identifies this published event. |
| `order_id` | Uniquely identifies the generated order. |
| `customer_id` | Kafka message key and common support-query field. |
| `product_id` | Identifies the ordered product. |
| `quantity` | Number of units ordered. |
| `unit_price` | Price per unit in the fictional transaction. |
| `region` | Fictional fulfillment region. |
| `created_at` | UTC time at which the demo event was produced. |

The consumer adds `total_amount`, `status`, and `processed_at` before writing the document to MongoDB.

## Operational Objectives

- Accept checkout events without losing acknowledged messages.
- Preserve ordering for orders belonging to the same customer.
- Keep consumer lag low enough for support staff to see recent orders promptly.
- Store orders idempotently so replaying an event does not create duplicates.
- Keep customer lookups efficient as the order collection grows.
- Make broker, consumer, application, and database failures distinguishable.

This is a single-node training environment. Replication factor, authentication, encryption, failover, backup automation, schema management, and production service-level objectives are intentionally simplified.

## Learning Path: Observe the Problem Before Fixing It

The demo deliberately keeps several operational weaknesses available. Students first create or observe a symptom, gather evidence, and only then apply a recovery or maintenance action.

| Workshop topic | Problem the demo can create | Evidence to collect | Recovery or improvement |
| --- | --- | --- | --- |
| Architecture | A wrong MongoDB endpoint prevents the pipeline from starting. | Consumer error and unchanged Kafka offsets | Correct configuration and verify each layer independently. |
| MongoDB health | Collection growth increases storage and query work. | Replica health, collection statistics, and document counts | Establish health and capacity checks. |
| MongoDB queries | A customer lookup performs `COLLSCAN`. | Query plan and documents examined | Create and validate a targeted index. |
| Kafka consumers | The producer outruns a delayed or stopped consumer. | Current offset, log-end offset, and lag | Restore processing and verify lag drains. |
| Kafka partitions | One message key sends all traffic to a hot partition. | Per-partition end offsets | Choose keys with appropriate cardinality and distribution. |
| Kafka retention | An unsafe 30-second retention override risks early data loss. | Effective topic configuration | Review and remove the unsafe override. |
| Connector-style processing | A malformed record repeatedly stops the Python sink worker. | Consumer error, uncommitted offset, and group lag | Route the poison record to a DLQ and commit only after delivery. |
| Replay | A duplicate Kafka event is delivered more than once. | Kafka record count versus MongoDB document count | Use `order_id` as an idempotency key. |
| Backup readiness | A database has data but no proven restore procedure. | Backup archive and restored document count | Perform and validate a test restore. |
| Kafka Connect | Validation rejects a bad connector URI; a strict policy lets malformed Kafka data fail a task. | REST validation/task state, worker logs, offsets, and DLQ | Preserve the approved config, apply the tolerant policy, restart only failed tasks, and reconcile data. |

## What to Monitor

### Kafka

- Broker availability and disk usage
- Topic partition count and leader availability
- Latest partition offsets and event throughput
- `workshop-order-processor` committed offsets and lag
- Consumer rebalances, processing rate, and errors

### MongoDB

- Replica-set state and server availability
- Database, collection, and storage growth
- Write errors and operation latency
- Documents examined versus returned by support queries
- Index presence, size, and use

### Application

- Events produced and delivery failures
- Events processed and MongoDB write failures
- Time between `created_at` and `processed_at`
- Clean shutdown and offset-commit behavior

## Exercise: Run the Order-Processing Demo

### Goal

Run the complete happy path, confirm that Kafka delivers the dummy orders, and verify that the consumer stores them in MongoDB.

### Prerequisites

- Docker Desktop or Docker Engine is running.
- Docker Compose v2 is available as `docker compose`.
- Python 3.10 or newer is installed.
- Commands are run from the repository root.

### Step 1: Start MongoDB and Kafka

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
```

Both commands should finish with a healthy container. If either command fails, inspect its logs before continuing:

```bash
docker compose -f mongodb/docker-compose.yml logs --tail=100 mongodb
docker compose -f kafka/docker-compose.yml logs --tail=100 kafka
```

### Step 2: Create a Python Virtual Environment

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demo/requirements.txt
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r demo/requirements.txt
```

### Step 3: Prepare the Demo

```bash
python demo/setup_demo.py
```

This checks MongoDB and Kafka connectivity and creates the three-partition `workshop-orders` topic if it does not already exist. The final output should say that the workshop demo is ready.

### Step 4: Start the Consumer

Open terminal 1, activate the same virtual environment, and run:

```bash
python demo/consumer.py
```

Leave this terminal running. The consumer joins the `workshop-order-processor` group and waits for order events. It stops cleanly when you press `Ctrl+C`.

### Step 5: Publish Dummy Orders

Open terminal 2, activate the virtual environment, and run:

```bash
python demo/producer.py
```

The producer reads `demo/data/orders.jsonl` and publishes 20 orders. Its summary should report `expected=20`, `delivered=20`, and no failures. Terminal 1 should report its processing progress.

### Step 6: Verify the Result

Inspect the MongoDB collection and query plan:

```bash
python demo/inspect_mongodb.py stats
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

The collection should contain the generated orders. Before the demonstration index is created, the query plan should include `COLLSCAN`.

Inspect the Kafka consumer group:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

After the consumer catches up, each displayed partition should have `LAG` equal to `0`.

### Step 7: Continue or Finish

Press `Ctrl+C` in terminal 1. Keep MongoDB and Kafka running if you are continuing with the fault exercises below. When the workshop is finished, stop the services without deleting their persistent data:

```bash
docker compose -f kafka/docker-compose.yml down
docker compose -f mongodb/docker-compose.yml down
```

The basic demo is complete. The exercises below intentionally make the pipeline unhealthy or inefficient. Run `python demo/setup_demo.py --reset` between exercises when a clean `workshop.orders` collection and fresh workshop topics are required. The reset affects only the two workshop topics and the orders collection.

## Fault Exercise 0: Misconfigured Dependency

Run the consumer with an intentionally incorrect MongoDB port.

On Linux or macOS:

```bash
MONGODB_URI='mongodb://localhost:27018/?directConnection=true' \
  python demo/consumer.py
```

On Windows PowerShell:

```powershell
$env:MONGODB_URI='mongodb://localhost:27018/?directConnection=true'
python demo/consumer.py
Remove-Item Env:MONGODB_URI
```

The consumer should fail before joining the normal processing loop. Confirm that Kafka and MongoDB themselves are healthy, identify the incorrect endpoint, then rerun the consumer without the override.

Discuss which team owns application configuration, database availability, broker availability, and pipeline validation. A connection failure at one layer should not automatically be diagnosed as a broker or database outage.

## Fault Exercise 1: MongoDB Health and Storage Growth

### Create the condition

Start the consumer in terminal 1, then publish 500 orders from terminal 2:

```bash
python demo/consumer.py
```

```bash
python demo/producer.py --repeat 25 --interval-ms 0
```

### Observe

```bash
python demo/inspect_mongodb.py health
python demo/inspect_mongodb.py stats
```

Record the replica-set role, member health, connection counts, document count, storage bytes, and index bytes. Repeat the statistics after another burst and identify which values grow.

### Discuss

- Which checks prove that MongoDB is writable rather than merely reachable?
- Which growth rates would be useful for capacity alerts?
- How would this single-node result differ from a production replica set?

## Fault Exercise 2: Inefficient MongoDB Query

### Create and observe the problem

```bash
python demo/inspect_mongodb.py drop-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

The plan should contain `COLLSCAN`. Record the documents returned and documents examined.

### Apply and verify the maintenance action

```bash
python demo/inspect_mongodb.py create-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/inspect_mongodb.py stats
```

The plan should now contain `IXSCAN`. Compare documents examined, keys examined, and index storage before and after the change.

### Discuss

- Does this query shape represent a genuine support requirement?
- What write and storage cost does the index introduce?
- When would an index be unused, redundant, or harmful?

## Fault Exercise 3: Consumer Lag and Recovery

### Create the condition

Stop the consumer, then publish a burst:

```bash
python demo/producer.py --repeat 20 --interval-ms 0
```

### Observe

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

Record `CURRENT-OFFSET`, `LOG-END-OFFSET`, and `LAG` for every displayed partition.

Inspect the Kafka data directory and recent broker logs before and after large bursts:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  du -sh /var/lib/kafka/data
docker compose -f kafka/docker-compose.yml logs --tail=50 kafka
```

### Recover and verify

```bash
python demo/consumer.py --delay-ms 250
```

Run the consumer-group command repeatedly while the consumer works. Confirm that offsets advance and lag eventually reaches zero, then stop the consumer with `Ctrl+C`.

### Discuss

- Is lag isolated to one partition or spread across the topic?
- Could MongoDB write latency be limiting consumption?
- Would more consumers help if only one partition were busy?
- What lag value and duration should trigger an alert?

## Fault Exercise 4: Hot and Uneven Kafka Partitions

### Create the condition

Reset the demo, then force every event to use the same Kafka key:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 20 --interval-ms 0 --key-mode hot
```

### Observe

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic workshop-orders
```

One partition should contain all 400 records while the other partitions remain empty. Describe the topic to confirm leader and replica state:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --describe --topic workshop-orders
```

### Compare with a better key

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 20 --interval-ms 0 --key-mode customer
```

Run `kafka-get-offsets.sh` again and compare the distribution. The five sample customer keys may not divide perfectly, but more than one partition should receive records.

### Discuss

- Why can additional consumers not fix a single hot partition?
- Which business key preserves required ordering without concentrating traffic?
- Which partition-level metrics would reveal this condition early?

## Fault Exercise 5: Unsafe Topic Retention

### Review the current configuration

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 --entity-type topics \
  --entity-name workshop-orders --describe
```

### Introduce the risk

Set a deliberately unsafe 30-second topic retention override:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 --entity-type topics \
  --entity-name workshop-orders --alter --add-config retention.ms=30000
```

Describe the configuration again and confirm `retention.ms=30000`. Do not rely on the records remaining available for replay after this point; segment cleanup is asynchronous.

### Recover

Remove the topic override so the broker default applies again:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 --entity-type topics \
  --entity-name workshop-orders --alter --delete-config retention.ms
```

Run `python demo/setup_demo.py --reset` before the next exercise to restore a known dataset state.

### Discuss

- How could short retention prevent incident replay or recovery?
- When is compaction more appropriate than time-based deletion?
- Which configuration changes require review and change control?

## Fault Exercise 6: Poison Record and Dead-Letter Queue

This Python consumer stands in for a Kafka Connect sink task so students can observe the same failed-task pattern without adding another runtime.

### Create the condition

Reset the demo. Start the default consumer in terminal 1, then publish valid orders followed by one malformed JSON record from terminal 2:

```bash
python demo/setup_demo.py --reset
python demo/consumer.py
```

```bash
python demo/producer.py --inject-invalid
```

The consumer should process some or all valid events, report the poison record's partition and offset, and stop without committing that offset. Kafka preserves order within a partition, not across the whole topic, so valid events in other partitions may still be waiting. Run the consumer-group description command from Fault Exercise 3 and confirm that lag remains.

### Recover with a DLQ policy

Restart the same group with DLQ handling:

```bash
python demo/consumer.py --on-error dlq
```

The consumer publishes the bad bytes and source metadata to `workshop-orders-dlq`, commits the source offset, and continues processing other partitions. After the output reports `[dlq]` and the remaining lag reaches zero, stop it with `Ctrl+C`. Inspect the DLQ:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic workshop-orders-dlq \
  --from-beginning --max-messages 1 --formatter-property print.headers=true
```

### Discuss

- Why must the source offset be committed only after DLQ delivery succeeds?
- Which errors should retry, stop, skip, or enter a DLQ?
- What alerts should exist for task failure and DLQ growth?
- What additional status endpoints and task metrics would Kafka Connect provide?

## Fault Exercise 7: Duplicate Delivery and Replay Safety

### Create the condition

Reset the demo. In terminal 1, start a consumer that exits after 21 Kafka records. In terminal 2, publish 20 orders and deliberately duplicate the first event:

```bash
python demo/setup_demo.py --reset
python demo/consumer.py --max-messages 21
```

```bash
python demo/producer.py --duplicate-first
```

### Verify

```bash
python demo/inspect_mongodb.py stats
```

Kafka delivered 21 records, but MongoDB should contain only 20 order documents because both copies have the same `order_id` and the consumer uses an upsert.

### Discuss

- Why is at-least-once delivery expected during retries or replay?
- Which business key makes the sink operation idempotent?
- What would happen if the consumer inserted every event with a new MongoDB `_id`?

## Fault Exercise 8: Backup and Restore Readiness

Ensure `workshop.orders` contains data, then create an archive on the host:

```bash
docker compose -f mongodb/docker-compose.yml exec -T mongodb \
  mongodump --db workshop --archive > workshop.archive
```

Restore the archive into a separate verification database:

```bash
docker compose -f mongodb/docker-compose.yml exec -T mongodb \
  mongorestore --archive --nsFrom='workshop.*' --nsTo='workshop_restore.*' \
  < workshop.archive
```

Verify the restored count:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop_restore?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.orders.countDocuments({})'
```

After recording the result, the instructor can remove the `workshop_restore` database and local `workshop.archive` file. Do not treat a backup as ready until a restore has been tested.

## First-Response Checklist

When recent orders are missing from MongoDB:

1. Confirm that the MongoDB primary and Kafka broker are healthy.
2. Confirm that `workshop-orders` exists and its partitions have leaders.
3. Check whether producer offsets are advancing.
4. Inspect the consumer group's state and lag.
5. Review consumer output for Kafka, JSON, or MongoDB errors.
6. Compare Kafka events with documents stored by `order_id`.
7. Record findings before restarting or replaying the consumer.

## Boundaries for This Exercise

The Python consumer demonstrates the data path directly and simulates connector-style failure, restart, offset, and DLQ behavior. A Kafka Connect worker and the MongoDB Kafka Connector are still deferred to a later environment because they add image, plugin, REST API, and connector-configuration complexity. The instructor should map the Python worker's observable symptoms to the equivalent Kafka Connect worker, connector, and task status signals during Module 4.
