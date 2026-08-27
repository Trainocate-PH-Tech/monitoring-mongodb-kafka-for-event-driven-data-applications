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

Check each layer:

```bash
docker compose -f kafka/docker-compose.yml ps
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic workshop-orders
python demo/inspect_mongodb.py health
```

Do not start the consumer yet. Kafka should contain events while MongoDB remains healthy but has no `orders` collection. This is backlog, not a MongoDB outage.

## 2. Inject a Worker Configuration Failure

Run the consumer with a wrong MongoDB port.

Linux or macOS:

```bash
MONGODB_URI='mongodb://localhost:27018/?directConnection=true' \
  python demo/consumer.py
```

Windows PowerShell:

```powershell
$env:MONGODB_URI='mongodb://localhost:27018/?directConnection=true'
python demo/consumer.py
Remove-Item Env:MONGODB_URI
```

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

MongoDB health:

```bash
python demo/inspect_mongodb.py health
```

The broker and database are healthy. The failure is in the worker's dependency configuration. Restarting Kafka or MongoDB would add risk without correcting the endpoint.

## 4. Correct and Verify

Run the consumer without the bad override:

```bash
python demo/consumer.py --max-messages 20
```

Verify zero lag and 20 MongoDB documents:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
python demo/inspect_mongodb.py stats
```

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

### 2. Inject the Wrong MongoDB Endpoint

```bash
printf '%s\n' '{"order_id":"CLI-CONNECTION-TEST"}' \
| docker compose -f mongodb/docker-compose.yml exec -T mongodb \
    mongoimport \
    --uri 'mongodb://localhost:27018/workshop?directConnection=true' \
    --collection "$CLI_COLLECTION" --mode=upsert --upsertFields=order_id
```

`mongoimport` should fail to connect. This does not prove that MongoDB itself is down.

### 3. Check MongoDB Independently

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson({hello: db.hello(), ping: db.runCommand({ping: 1})})'
```

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
