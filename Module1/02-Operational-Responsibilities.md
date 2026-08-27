# Walkthrough 02: Operational Responsibilities Across Layers

## Course-Outline Topic

Operational responsibilities across database, broker, connector, and application layers.

## Goal

Diagnose a broken pipeline by checking every layer and assigning the response to the correct owner.

## Responsibility Model

| Layer | Typical responsibilities | First evidence |
| --- | --- | --- |
| Producer application | Event construction, keys, delivery handling, rate, business semantics | Producer output and application logs |
| Kafka broker/topic | Availability, leaders, replicas, partitions, retention, disk, throughput | Topic description, broker logs, end offsets |
| Connector/worker | Configuration, task state, consumption, transformation, retries, offsets, DLQ | Worker output, group state, lag, DLQ records |
| MongoDB | Primary state, writes, storage, indexes, query performance, backup | Replica health, collection stats, query plans, logs |

Ownership does not remove collaboration. It prevents an incident from being escalated to every team before evidence identifies the affected layer.

## 1. Establish a Healthy Baseline

```bash
python demo/setup_demo.py --reset
python demo/producer.py --interval-ms 0
```

**Expected output:** setup ends with `[ready]`, and the producer reports `expected=20 delivered=20 failed=0`. **Meaning:** Kafka has accepted a clean 20-record backlog; no sink has processed it yet.

Check each layer:

```bash
docker compose -f kafka/docker-compose.yml ps
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic workshop-orders
python demo/inspect_mongodb.py health
```

**Expected output:** Compose reports Kafka `Up (healthy)`; partition end offsets sum to 20; MongoDB reports `is writable primary: True` and member state `PRIMARY`. **Meaning:** the broker, source data, and database are healthy independently of the worker.

Do not start the consumer yet. Kafka should contain events while MongoDB remains healthy but has no `orders` collection. This is backlog, not a MongoDB outage.

## 2. Inject a Worker Configuration Failure

Run the consumer with a wrong MongoDB port.

Linux or macOS:

```bash
MONGODB_URI='mongodb://localhost:27018/?directConnection=true' \
  python demo/consumer.py
```

**Expected output:** `[error] Consumer stopped` followed by a server-selection or connection-refused error for `localhost:27018`; the command exits nonzero. **Meaning:** the worker cannot reach its configured dependency. It does not show that the real MongoDB service on port `27017` is down.

Windows PowerShell:

```powershell
$env:MONGODB_URI='mongodb://localhost:27018/?directConnection=true'
python demo/consumer.py
Remove-Item Env:MONGODB_URI
```

**Expected output:** the Python command reports the same `27018` connection failure; `Remove-Item` normally prints nothing. **Meaning:** the fault is reproduced on Windows and the final command removes the temporary environment override.

The worker should fail with a connection-refused or server-selection error.

## 3. Prove What Is Still Healthy

Kafka topic and offsets:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic workshop-orders

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic workshop-orders
```

**Expected output:** all three partitions have `Leader: 1` and `Isr: 1`; end offsets still sum to 20. **Meaning:** Kafka retained the backlog and did not lose records when the worker failed.

MongoDB health:

```bash
python demo/inspect_mongodb.py health
```

**Expected output:** `is writable primary: True`, with `mongodb:27017` in `PRIMARY` state and health `1.0`. **Meaning:** MongoDB is writable through the correct endpoint.

The broker and database are healthy. The failure is in the worker's dependency configuration. Restarting Kafka or MongoDB would add risk without correcting the endpoint.

## 4. Correct and Verify

Run the consumer without the bad override:

```bash
python demo/consumer.py --max-messages 20
```

**Expected output:** `[done] consumed=20 processed=20 rejected=0`. **Meaning:** correcting the client configuration was sufficient; the retained Kafka backlog was processed without restarting either service.

Verify zero lag and 20 MongoDB documents:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
python demo/inspect_mongodb.py stats
```

**Expected output:** every group row has `LAG 0`, and MongoDB reports `documents: 20`. **Meaning:** Kafka progress and sink state both recovered.

## Command-Line Implementation

The same responsibility exercise can be run without Python against the isolated CLI resources.

### 1. Prove the CLI Source Topic Is Healthy

Use the command-line producer from [walkthrough 01](01-Production-Architecture.md#1-produce-keyed-json-events), then inspect the topic:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic "$CLI_TOPIC"

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic "$CLI_TOPIC"
```

**Expected output:** the description lists three led/in-sync partitions, and the offset lines sum to 20 after one CLI producer run. **Meaning:** the CLI source layer is healthy before testing the sink endpoint.

### 2. Inject the Wrong MongoDB Endpoint

```bash
printf '%s\n' '{"order_id":"CLI-CONNECTION-TEST"}' \
| docker compose -f mongodb/docker-compose.yml exec -T mongodb \
    mongoimport \
    --uri 'mongodb://localhost:27018/workshop?directConnection=true' \
    --collection "$CLI_COLLECTION" --mode=upsert --upsertFields=order_id
```

**Expected output:** `mongoimport` reports a connection/server-selection failure for `localhost:27018` and imports no document. **Meaning:** the deliberately incorrect sink URI failed before changing MongoDB.

`mongoimport` should fail to connect. This does not prove that MongoDB itself is down.

### 3. Check MongoDB Independently

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson({hello: db.hello(), ping: db.runCommand({ping: 1})})'
```

**Expected output:** `hello.isWritablePrimary` is `true` and `ping.ok` is `1`. **Meaning:** the database is available at port `27017`; only the failed command's endpoint was wrong.

The correct endpoint reports a writable primary and a successful ping. The affected layer is the sink command configuration.

### 4. Correct the CLI Sink

Run the console-consumer-to-`mongoimport` pipeline from [walkthrough 01](01-Production-Architecture.md#2-consume-transform-and-upsert). Then prove zero lag and 20 documents using its verification commands.

Neither the Python nor CLI failure requires a Kafka or MongoDB restart. The correct action is to repair the client endpoint and process the retained backlog.

## Incident Evidence Template

Complete this before escalating:

| Question | Evidence |
| --- | --- |
| Is the producer advancing Kafka end offsets? | |
| Do all topic partitions have leaders? | |
| Is the worker running and configured for the correct endpoints? | |
| Are committed offsets advancing? | |
| Is MongoDB writable primary healthy? | |
| Are documents appearing with expected fields? | |
| Which layer owns the first failed check? | |

## Discussion

- Which team owns the bad URI, and which team should be informed rather than paged?
- What monitoring signal would detect this failure before a user reports missing orders?
- Why is “restart everything” a poor first-response strategy?
- In Kafka Connect, which REST resources would distinguish a healthy worker from a failed connector task?
