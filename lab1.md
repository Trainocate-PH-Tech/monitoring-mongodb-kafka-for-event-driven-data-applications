# Lab 1: Insurance Transactions from Kafka to MongoDB

## Objectives

By the end of this lab, you will be able to:

- Explain how a client application produces keyed insurance transactions to Kafka.
- Explain how a consumer group reads Kafka records and inserts or updates MongoDB documents.
- Use topic metadata, end offsets, consumer-group state, committed offsets, and lag to monitor every stage of the flow.
- Distinguish evidence that a record reached Kafka from evidence that the application processed it and MongoDB stored it.

## Scenario

An insurer records premium payments, claim payments, and refunds. A client publishes each transaction to the `insurance-transactions-lab1` Kafka topic. A second mode of the same client consumes the records as group `insurance-mongodb-writer-lab1` and upserts them into `insurance.transactions` in MongoDB.

```text
insurance_client.py produce
          |
          | keyed by policy_id
          v
Kafka: insurance-transactions-lab1
          |
          | group: insurance-mongodb-writer-lab1
          v
insurance_client.py consume
          |
          | upsert by transaction_id, then commit Kafka offset
          v
MongoDB: insurance.transactions
```

An **upsert** updates a document when its `transaction_id` already exists and inserts it otherwise. This makes replaying the lab's deterministic transactions safe: Kafka may contain another copy, but MongoDB retains one document per transaction ID.

The runnable client is [demo/insurance_client.py](demo/insurance_client.py). Its
important application calls are deliberately easy to locate:

| Client step | Python API | Purpose |
| --- | --- | --- |
| Connect a producer | `Producer({"bootstrap.servers": ...})` | Create a client that can send records to Kafka. |
| Publish | `producer.produce(topic, key=..., value=...)` | Queue a policy-keyed JSON record for delivery. |
| Confirm delivery | `on_delivery=delivery_report` | Receive Kafka's success or failure result, including partition and offset. |
| Finish buffered sends | `producer.flush(10)` | Wait up to ten seconds for queued delivery callbacks. |
| Connect a consumer | `Consumer({... "group.id": ...})` | Join the application group and configure explicit commits. |
| Receive records | `consumer.subscribe(...)` and `consumer.poll(...)` | Subscribe to the topic and retrieve one available record. |
| Store the result | `collection.replace_one(..., upsert=True)` | Insert or update one transaction in MongoDB. |
| Save progress | `consumer.commit(message=..., asynchronous=False)` | Commit the next-read position only after MongoDB succeeds. |

This is a teaching client, not a production insurance system. It omits authentication, encryption, schema management, retries, a dead-letter topic, and sensitive-data controls so the Kafka-to-MongoDB interaction remains visible.

## Before You Begin

Run commands from the repository root. You need four terminals during the monitoring portion:

1. Consumer application
2. Producer application
3. Kafka monitoring
4. MongoDB inspection

Create and activate the Python environment if you have not already done so:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demo/requirements.txt
```

**Expected output:** package installation finishes without an error and the prompt is prefixed with `(.venv)`. **Meaning:** the Kafka and MongoDB Python drivers required by the client are available.

Start the two persistent services:

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
```

Representative output:

```text
Container mongodb  Healthy
Container kafka    Healthy
```

**Meaning:** Docker reports that MongoDB is a writable replica-set primary and that Kafka answers broker API requests. Container names may include a project prefix on some Compose versions.

## 1. Prepare an Empty Lab

Do not run this reset while the lab consumer is active. Delete only this lab's Kafka topic, consumer-group offsets, and MongoDB collection:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --delete --group insurance-mongodb-writer-lab1 || true

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete --if-exists --topic insurance-transactions-lab1

until ! docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list \
  | grep -Fxq insurance-transactions-lab1; do sleep 0.5; done

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.transactions.drop()'
```

Representative output:

```text
Deletion of requested consumer groups ('insurance-mongodb-writer-lab1') was successful.
true
```

**Meaning:** any prior group position and MongoDB documents are gone. Kafka topic deletion may be silent; the loop waits for its asynchronous deletion to finish. Deleting a group that does not yet exist may print an error that `|| true` deliberately ignores.

Create a three-partition topic:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists \
  --topic insurance-transactions-lab1 \
  --partitions 3 --replication-factor 1
```

Expected output:

```text
Created topic insurance-transactions-lab1.
```

**Meaning:** the application now has a named Kafka destination with three independent ordered partitions. Replication factor 1 is suitable only for this single-broker workshop.

## 2. Establish the Kafka Baseline

Describe the topic and its empty offsets in terminal 3:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic insurance-transactions-lab1

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab1
```

Representative output:

```text
Topic: insurance-transactions-lab1  PartitionCount: 3  ReplicationFactor: 1
Topic: insurance-transactions-lab1  Partition: 0  Leader: 1  Replicas: 1  Isr: 1
Topic: insurance-transactions-lab1  Partition: 1  Leader: 1  Replicas: 1  Isr: 1
Topic: insurance-transactions-lab1  Partition: 2  Leader: 1  Replicas: 1  Isr: 1
insurance-transactions-lab1:0:0
insurance-transactions-lab1:1:0
insurance-transactions-lab1:2:0
```

**Meaning:** all partitions have a leader and an in-sync replica. Each `topic:partition:end-offset` ends in zero, proving that no record has yet been appended.

## 3. Start the Consumer Application

In terminal 1, with the virtual environment active, run:

```bash
python demo/insurance_client.py consume --max-messages 12 --delay-ms 750
```

Expected initial output:

```text
[ready] topic=insurance-transactions-lab1 group=insurance-mongodb-writer-lab1 sink=insurance.transactions
```

**Meaning:** the client reached both services, subscribed to the topic, and is waiting. It has not processed a record yet. The 750 ms delay is intentional so lag remains visible long enough to observe.

In terminal 3, inspect the new group:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group insurance-mongodb-writer-lab1
```

Representative output before production:

```text
GROUP                              TOPIC                        PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG CONSUMER-ID ...
insurance-mongodb-writer-lab1      insurance-transactions-lab1 0         -              0              -   ...
insurance-mongodb-writer-lab1      insurance-transactions-lab1 1         -              0              -   ...
insurance-mongodb-writer-lab1      insurance-transactions-lab1 2         -              0              -   ...
```

**Meaning:** group membership proves the consumer joined Kafka. A dash is normal before the group commits its first record. It does not yet prove MongoDB writes work.

## 4. Produce Insurance Transactions

In terminal 2, with the virtual environment active, publish 12 transactions at once:

```bash
python demo/insurance_client.py produce --count 12 --interval-ms 0
```

Representative output:

```text
[delivered] count=1 transaction=LAB1-TXN-001 partition=0 offset=0
[delivered] count=2 transaction=LAB1-TXN-002 partition=2 offset=0
...
[done] expected=12 delivered=12 failed=0 unflushed=0 topic=insurance-transactions-lab1
```

**Meaning:** Kafka acknowledged all 12 records. Partition assignments and callback order may differ. Each reported offset is local to its partition. This output proves Kafka accepted the records; it does not prove that the consumer or MongoDB handled them.

The application uses `policy_id` as the record key. Transactions for the same policy therefore go to the same partition and retain their relative order there.

## 5. Watch Kafka While the Consumer Works

Immediately rerun these commands in terminal 3 several times:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab1

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group insurance-mongodb-writer-lab1
```

Representative output while work is in progress:

```text
insurance-transactions-lab1:0:3
insurance-transactions-lab1:1:3
insurance-transactions-lab1:2:6

GROUP                         TOPIC                        PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG
insurance-mongodb-writer-lab1 insurance-transactions-lab1 0         1              3              2
insurance-mongodb-writer-lab1 insurance-transactions-lab1 1         1              3              2
insurance-mongodb-writer-lab1 insurance-transactions-lab1 2         2              6              4
```

**Meaning:** the exact distribution varies, but the three end offsets sum to 12. `CURRENT-OFFSET` is the group's saved next-read position. `LAG = LOG-END-OFFSET - CURRENT-OFFSET`; decreasing lag proves that commits are advancing toward Kafka's end offsets.

Meanwhile, terminal 1 prints records as MongoDB accepts them:

```text
[stored] count=1 transaction=LAB1-TXN-001 action=inserted partition=0 offset=0
...
[done] consumed=12 processed=12 rejected=0
```

**Meaning:** for each line, the client decoded the Kafka value, upserted MongoDB, and synchronously committed that source offset. The consumer stops after 12 records.

## 6. Prove Completion at Both Layers

After the consumer exits, describe its group again:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group insurance-mongodb-writer-lab1
```

Expected result: all three `LAG` values are `0`; the sum of `CURRENT-OFFSET` values is 12. Consumer identity fields may be blank because the finite client has exited.

**Meaning:** the group has committed through every current Kafka record. Zero lag proves Kafka progress, but MongoDB is a separate system and must be checked independently.

In terminal 4, inspect MongoDB:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print("documents=" + db.transactions.countDocuments());
    printjson(db.transactions.findOne(
      {transaction_id: "LAB1-TXN-001"},
      {_id: 0, transaction_id: 1, policy_id: 1, transaction_type: 1,
       amount: 1, kafka_partition: 1, kafka_offset: 1}
    ));
  '
```

Representative output:

```text
documents=12
{
  transaction_id: 'LAB1-TXN-001',
  policy_id: 'POL-1001',
  transaction_type: 'premium.payment',
  amount: 94.25,
  kafka_partition: 0,
  kafka_offset: 0
}
```

**Meaning:** MongoDB contains all 12 logical transactions and preserves the Kafka source location for traceability. The partition and offset can differ from this example.

## 7. Connect the Evidence

For one transaction, compare the three observations:

| Stage | Evidence | What it proves |
| --- | --- | --- |
| Producer acknowledgement | `[delivered] ... partition=P offset=O` | Kafka accepted the record at location `P/O`. |
| Consumer processing | `[stored] ... partition=P offset=O` | The client read that same location, wrote MongoDB, and then committed. |
| MongoDB query | Document contains `kafka_partition: P` and `kafka_offset: O` | The downstream record exists and can be traced back to Kafka. |
| Group monitoring | Lag reaches zero | No current Kafka records remain uncommitted for this group. |

No single observation proves the whole pipeline. A healthy producer with rising end offsets can coexist with a stopped consumer. A running consumer can fail to write MongoDB. Zero lag can also be misleading if an unsafe client commits before its database write. This client intentionally writes first and commits second.

## Optional Challenge: Observe a Replay

Run the producer again, then consume the next 12 records with the same group:

```bash
python demo/insurance_client.py produce --count 12 --interval-ms 0
python demo/insurance_client.py consume --max-messages 12 --delay-ms 0
```

Expected consumer result: each transaction reports `action=updated`, Kafka end offsets advance by 12, group lag returns to zero, and MongoDB still contains 12 documents.

**Meaning:** Kafka is an append-only event log and now contains 24 records, while idempotent upserts prevent duplicate logical transactions in MongoDB.

## Review Questions

1. Why does a producer acknowledgement not prove that MongoDB contains the transaction?
2. Which two offset columns are used to calculate consumer lag?
3. Why are transactions keyed by `policy_id` rather than a random value?
4. Why does the consumer commit only after the MongoDB upsert succeeds?
5. How can Kafka contain 24 records while MongoDB contains only 12 documents after the replay?

## Stop the Lab

The services are persistent. Stop them without deleting their data:

```bash
docker compose -f kafka/docker-compose.yml down
docker compose -f mongodb/docker-compose.yml down
```

**Expected output:** both containers stop and are removed. **Meaning:** named volumes retain Kafka and MongoDB data for later exercises.
