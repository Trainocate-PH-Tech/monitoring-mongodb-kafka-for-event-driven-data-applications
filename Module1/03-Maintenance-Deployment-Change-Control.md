# Walkthrough 03: Maintenance, Deployment, and Change Control

## Course-Outline Topic

Common maintenance windows, deployment patterns, and change-control considerations.

## Goal

Practice evidence-based changes with an explicit baseline, validation, and rollback. This lab is single-node, so a Kafka or MongoDB restart creates a real local outage; production clusters use replicas and staged rollouts to preserve availability.

## Change Record Template

For every change, record:

| Field | Required content |
| --- | --- |
| Objective | The operational or business reason |
| Scope | Service, topic, collection, index, or application |
| Risk | Availability, data loss, replay, lag, performance |
| Baseline | Health and performance evidence before change |
| Implementation | Exact approved action |
| Validation | Evidence that proves success |
| Rollback | Exact reversal and its trigger |
| Owner | Person or team responsible |

## 1. Capture a Pre-Change Baseline

```bash
python demo/setup_demo.py --reset
python demo/producer.py --interval-ms 0
python demo/consumer.py --max-messages 20
python demo/inspect_mongodb.py health
python demo/inspect_mongodb.py stats
```

Capture Kafka state:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic workshop-orders

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-orders --describe
```

Save the document count, group offsets, lag, partition leaders, and dynamic topic configuration.

## 2. Application Deployment Pattern

Publish another batch, then start a delayed consumer and stop it with `Ctrl+C` while work remains:

```bash
python demo/producer.py --repeat 5 --interval-ms 0
python demo/consumer.py --delay-ms 100
```

Describe the group before restarting the consumer. Then run the normal consumer:

```bash
python demo/consumer.py
```

Stop it after lag reaches zero. Verify that committed offsets resume rather than returning to zero. This models a worker deployment with durable Kafka offsets.

Production deployment patterns may include rolling replacement, blue/green workers, canary connectors, or pausing a connector before configuration changes. The correct pattern depends on task coordination, compatibility, replay behavior, and acceptable lag.

## 3. Topic Retention Change and Rollback

Introduce a deliberately unsafe 30-second retention override:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-orders \
  --alter --add-config retention.ms=30000
```

Validate the dynamic configuration:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-orders --describe
```

The risk is loss of records needed for delayed processing or incident replay. Roll back by removing the override:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-orders \
  --alter --delete-config retention.ms
```

Describe the topic configuration again and confirm that the dynamic override is absent.

## 4. MongoDB Index Change and Rollback

Capture the query plan without the index:

```bash
python demo/inspect_mongodb.py drop-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

Create and validate the index:

```bash
python demo/inspect_mongodb.py create-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/inspect_mongodb.py stats
```

Validation requires `IXSCAN`, fewer documents examined, and acceptable index storage—not merely successful command completion. The rollback is:

```bash
python demo/inspect_mongodb.py drop-index
```

Rollback would be justified if the index has unacceptable write/storage cost, duplicates an existing index, or does not support a real query workload.

## 5. Single-Node Maintenance Window

Record topic offsets and MongoDB document count. Restart Kafka:

```bash
docker compose -f kafka/docker-compose.yml restart kafka
docker compose -f kafka/docker-compose.yml up -d --wait
```

Verify topic records and committed group offsets still exist. This environment has no second broker, so Kafka is unavailable during the restart. A production maintenance plan should address:

- Broker replicas and in-sync replicas before proceeding
- One broker at a time versus full-cluster shutdown
- Client retry and timeout behavior
- Expected leader movement and rebalance impact
- Abort conditions if replicas or tasks fail to recover
- Post-change lag, throughput, and disk checks

## Command-Line Implementation

Use the isolated CLI resources to perform the same deployment and change-control checks without Python.

### 1. Process a Deployment in Two Batches

Produce 20 CLI orders using [walkthrough 01](01-Production-Architecture.md#1-produce-keyed-json-events). Define a Bash function that consumes and imports a requested batch size:

```bash
consume_cli_batch() {
  local count="$1"
  docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
    --group "$CLI_GROUP" --from-beginning --max-messages "$count" \
  | jq -c '. + {
      total_amount: (.quantity * .unit_price),
      status: "received",
      processed_at: (now | todateiso8601)
    }' \
  | docker compose -f mongodb/docker-compose.yml exec -T mongodb \
      mongoimport \
      --uri 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
      --collection "$CLI_COLLECTION" --mode=upsert --upsertFields=order_id
}

consume_cli_batch 10
```

Describe `$CLI_GROUP`; it should retain lag for the second half. Simulate a new worker deployment by invoking the function again:

```bash
consume_cli_batch 10
```

Verify zero lag and 20 CLI documents. The second process resumes from committed group offsets rather than starting at the beginning.

### 2. Change and Roll Back CLI Topic Retention

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name "$CLI_TOPIC" \
  --alter --add-config retention.ms=30000

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name "$CLI_TOPIC" --describe

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name "$CLI_TOPIC" \
  --alter --delete-config retention.ms
```

### 3. Change and Roll Back the CLI Collection Index

Capture the unindexed execution statistics:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const e = db.runCommand({
      explain: {find: "orders_cli", filter: {customer_id: "CUST-1001"}},
      verbosity: "executionStats"
    });
    printjson({plan: e.queryPlanner.winningPlan, executionStats: e.executionStats});'
```

Create, validate, and roll back the index:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'print(db.orders_cli.createIndex({customer_id: 1}, {name: "customer_id_1"}))'

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const e = db.runCommand({
      explain: {find: "orders_cli", filter: {customer_id: "CUST-1001"}},
      verbosity: "executionStats"
    });
    printjson({plan: e.queryPlanner.winningPlan, executionStats: e.executionStats});'

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.orders_cli.dropIndex("customer_id_1")'
```

The CLI makes the database commands explicit, while the Python inspector presents the same evidence in a shorter summary.

## Completion Check

Write one complete change record for either the retention or index change. It must contain measurable validation and an executable rollback, not statements such as “check that it works.”
