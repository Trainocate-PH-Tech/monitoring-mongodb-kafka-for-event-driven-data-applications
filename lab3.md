# Lab 3: Poison Record, Stalled Consumer, and DLQ Recovery

## Objectives

By the end of this lab, you will be able to:

- Recognize a data-processing failure even when Kafka and MongoDB are healthy.
- Use producer acknowledgements, consumer errors, partition offsets, group lag, and MongoDB counts to locate the failed stage.
- Explain why restarting Kafka or MongoDB does not repair a deterministic malformed record.
- Route a rejected record to a dead-letter queue (DLQ), resume processing, and reconcile the complete pipeline.

## Incident Scenario

An insurer publishes 12 valid payment transactions and one malformed JSON record. Kafka accepts all 13 because Kafka stores bytes and does not validate the application's JSON schema. The strict consumer encounters the malformed record, refuses to commit its offset, and exits. Valid records later in the affected partition remain blocked.

```text
12 valid records + 1 malformed record
                  |
                  v
Kafka source topic remains healthy
                  |
                  v
strict consumer -> malformed JSON -> exits without committing
                                           |
                      +--------------------+--------------------+
                      v                                         v
               group lag remains                       MongoDB is incomplete

Recovery: malformed record -> DLQ acknowledgement -> source commit -> continue
```

This is commonly called a **poison record**: a record that repeatedly causes deterministic processing failure. A **DLQ** is a separate Kafka topic that preserves the rejected value and diagnostic context for investigation and later remediation.

## Safety and Processing Guarantees

The teaching client uses this order for valid records:

1. Decode and validate the Kafka value.
2. Upsert MongoDB by `transaction_id`.
3. Commit the Kafka source offset.

In DLQ mode it uses this order for invalid records:

1. Publish the original key and bytes to the DLQ with error headers.
2. Wait for Kafka to acknowledge the DLQ record.
3. Commit the source offset.
4. Continue consuming.

If the DLQ write fails, the source offset is not committed. This favors replay over silent loss. It is still not a distributed transaction: a crash between DLQ acknowledgement and source commit can duplicate the DLQ record, so production remediation must be idempotent.

## Isolated Lab Resources

| Resource | Lab 3 value |
| --- | --- |
| Source topic | `insurance-transactions-lab3` |
| Dead-letter topic | `insurance-transactions-lab3-dlq` |
| Consumer group | `insurance-mongodb-writer-lab3` |
| MongoDB namespace | `insurance_lab3.transactions` |
| Valid records | 12 |
| Malformed records | 1 |

Run commands from the repository root. Use three terminals: one for the application, one for Kafka monitoring, and one for MongoDB inspection.

## 1. Start the Environment

Create the Python environment if necessary, then start the persistent services:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demo/requirements.txt

docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
```

**Expected output:** dependency installation succeeds and both containers become healthy. **Meaning:** the client can reach the Kafka broker and the writable MongoDB replica-set primary.

## 2. Prepare a Known Empty State

Stop any Lab 3 consumer before resetting. Delete only the Lab 3 group, topics, and database collection:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --delete --group insurance-mongodb-writer-lab3 || true

for topic in insurance-transactions-lab3 insurance-transactions-lab3-dlq; do
  docker compose -f kafka/docker-compose.yml exec kafka \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --delete --if-exists --topic "$topic"

  until ! docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list \
    | grep -Fxq "$topic"; do sleep 0.5; done
done

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab3?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.transactions.drop()'
```

**Expected output:** existing resources are deleted; a missing first-run group may produce `GroupIdNotFoundException`, which `|| true` deliberately ignores. MongoDB prints `true` when the collection existed and `false` otherwise. **Meaning:** other labs and module datasets are untouched.

Create a three-partition source topic and a one-partition DLQ:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --create --if-not-exists \
  --topic insurance-transactions-lab3 \
  --partitions 3 --replication-factor 1

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --create --if-not-exists \
  --topic insurance-transactions-lab3-dlq \
  --partitions 1 --replication-factor 1
```

Expected output:

```text
Created topic insurance-transactions-lab3.
Created topic insurance-transactions-lab3-dlq.
```

Create the MongoDB uniqueness constraint before ingestion:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab3?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.transactions.createIndex({transaction_id: 1}, {unique: true})'
```

Expected output:

```text
transaction_id_1
```

**Meaning:** replaying a valid transaction updates its existing logical document instead of inserting a duplicate. Lab 3 focuses on malformed data rather than the missing-index problem covered by Lab 2.

Confirm both Kafka topics are empty:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab3

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab3-dlq
```

Expected output has three source rows ending in `:0` and one DLQ row ending in `:0`. **Meaning:** neither topic contains a record, so later offset growth belongs to this run.

## 3. Publish Valid and Malformed Insurance Transactions

Publish 12 valid transactions and inject malformed JSON after the fifth valid input:

```bash
python demo/insurance_client.py produce \
  --topic insurance-transactions-lab3 \
  --id-prefix LAB3-TXN \
  --count 12 --inject-invalid-after 5 \
  --interval-ms 0 --report-every 1
```

Representative output:

```text
[delivered] count=... transaction=INVALID-JSON partition=0 offset=2
...
[done] expected=13 delivered=13 failed=0 unflushed=0 topic=insurance-transactions-lab3
```

**Meaning:** Kafka acknowledged all 13 values, including the malformed one. Callback order and the reported partition/offset vary. Find the `transaction=INVALID-JSON` line and record its partition and offset; these become the incident's trace coordinates.

Kafka accepts this value because serialization validation belongs to the application, not the broker. Confirm source growth and an empty DLQ:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab3

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab3-dlq
```

**Expected output:** the three source end offsets sum to 13 and the DLQ end offset remains zero. **Meaning:** production succeeded, but no consumer has classified or stored the values yet.

## 4. Reproduce the Strict Consumer Failure

Run the consumer with its default strict error policy:

```bash
python demo/insurance_client.py consume \
  --topic insurance-transactions-lab3 \
  --group-id insurance-mongodb-writer-lab3 \
  --mongodb-database insurance_lab3 \
  --max-messages 13 --delay-ms 0
```

Representative final error:

```text
[error] invalid insurance transaction at topic=insurance-transactions-lab3 partition=0 offset=2; offset was not committed: ...
```

**Meaning:** the consumer exits nonzero at the poison record. Its exact partition and offset must match the producer acknowledgement. The client did not commit that offset, and it did not write the malformed value to MongoDB.

The number of valid documents written before failure is intentionally variable. Kafka schedules partitions independently, so the client may process valid records from other partitions before it encounters the poison record.

## 5. Diagnose the Incident Without Restarting Infrastructure

### 5A. Prove the dependencies are healthy

```bash
docker compose -f kafka/docker-compose.yml ps
docker compose -f mongodb/docker-compose.yml ps

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.runCommand({ping: 1}))'
```

Expected evidence: both containers are `Up` and `healthy`, and MongoDB returns `{ ok: 1 }`. **Meaning:** this is not broker unavailability or loss of the MongoDB primary. Restarting healthy dependencies would leave the same bytes at the same Kafka offset.

### 5B. Observe the stalled group

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group insurance-mongodb-writer-lab3
```

Representative evidence:

```text
Consumer group 'insurance-mongodb-writer-lab3' has no active members.

GROUP                           PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG
insurance-mongodb-writer-lab3   0         2              4              2
```

**Meaning:** the failed process is no longer a group member. At least one partition has a committed offset below its end offset, so total lag is nonzero. The actual rows vary because records from other partitions may already have been committed.

This differs from a slow consumer: take a second snapshot after several seconds. Both the committed offsets and lag remain unchanged because no consumer is running.

### 5C. Prove MongoDB is incomplete

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab3?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print("documents=" + db.transactions.countDocuments());
    printjson(db.transactions.find(
      {}, {_id: 0, transaction_id: 1, kafka_partition: 1, kafka_offset: 1}
    ).sort({transaction_id: 1}).toArray());
  '
```

**Expected output:** `documents` is less than 12, followed by the valid transactions processed before the failure. **Meaning:** healthy MongoDB availability does not prove completeness; application-level reconciliation is required.

### 5D. Inspect the exact source bytes

Set these shell variables from the strict consumer error:

```bash
BAD_PARTITION=0
BAD_OFFSET=2
```

Replace the example numbers when your output differs. Read exactly one record without joining the application group:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab3 \
  --partition "$BAD_PARTITION" --offset "$BAD_OFFSET" --max-messages 1 \
  --formatter-property print.key=true \
  --formatter-property key.separator=' | '
```

Representative output:

```text
POL-1001 | {"event_type":"insurance.transaction.recorded","transaction_id":
Processed a total of 1 messages
```

**Meaning:** the value ends before valid JSON can be completed. Direct partition/offset inspection does not alter `insurance-mongodb-writer-lab3` because this diagnostic consumer does not use that group.

## 6. Recover Through the DLQ

Restart the same source group with DLQ handling enabled:

```bash
python demo/insurance_client.py consume \
  --topic insurance-transactions-lab3 \
  --group-id insurance-mongodb-writer-lab3 \
  --mongodb-database insurance_lab3 \
  --max-messages 13 --idle-timeout-seconds 3 --delay-ms 0 \
  --on-error dlq \
  --dlq-topic insurance-transactions-lab3-dlq
```

Representative output:

```text
[ready] topic=insurance-transactions-lab3 group=insurance-mongodb-writer-lab3 sink=insurance_lab3.transactions
[dlq] topic=insurance-transactions-lab3 partition=0 offset=2 destination=insurance-transactions-lab3-dlq source_offset_committed=true
[stored] ...
[idle] no records received for 3s; stopping
[done] consumed=2 processed=1 rejected=1
```

**Meaning:** the exact counters vary because they describe only this recovery process, not the earlier strict run. The invariant is one rejected record, acknowledged DLQ delivery, and processing of every remaining valid record. The idle timeout lets the finite lab exit after draining an unknown number of remaining records.

Do not replace this recovery with repeated restarts under the strict policy. A deterministic malformed value fails the same parser every time and pins the same offset again.

## 7. Verify Recovery at Every Layer

### 7A. Source-group progress

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group insurance-mongodb-writer-lab3
```

Expected result: `CURRENT-OFFSET` equals `LOG-END-OFFSET` and `LAG` is zero for all three partitions. **Meaning:** the group has made a terminal decision—store or reject—for every current source record.

### 7B. DLQ growth and diagnostic context

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab3-dlq

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab3-dlq \
  --from-beginning --max-messages 1 \
  --formatter-property print.key=true \
  --formatter-property print.headers=true \
  --formatter-property key.separator=' | '
```

Representative output includes:

```text
insurance-transactions-lab3-dlq:0:1
source_topic:insurance-transactions-lab3,source_partition:0,source_offset:2,error:... POL-1001 | {"event_type":...
Processed a total of 1 messages
```

**Meaning:** the DLQ contains exactly one rejected value. Its headers preserve the original topic, partition, offset, and parser error needed for remediation and audit. Header formatting varies slightly by Kafka version.

### 7C. MongoDB completeness

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab3?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const expected = Array.from({length: 12}, (_, i) =>
      "LAB3-TXN-" + String(i + 1).padStart(3, "0"));
    const actual = db.transactions.distinct("transaction_id");
    print("documents=" + db.transactions.countDocuments());
    printjson({missing: expected.filter(id => !actual.includes(id))});
  '
```

Expected output:

```text
documents=12
{ missing: [] }
```

**Meaning:** every valid logical transaction reached MongoDB and none is missing. The malformed record is deliberately absent from the business collection.

## 8. Reconcile the Incident

| Measurement | Expected final value | Interpretation |
| --- | ---: | --- |
| Source Kafka records | 13 | Kafka retained 12 valid values and one malformed value. |
| Source consumer-group lag | 0 | Every source offset was committed after storage or DLQ acknowledgement. |
| MongoDB documents | 12 | Every valid transaction was upserted. |
| DLQ records | 1 | The malformed value and its diagnostic context were preserved. |

Zero lag does not mean every source record became a MongoDB document. Here, zero lag is correct only because the reconciliation equation is explainable: `13 source records = 12 MongoDB documents + 1 DLQ record`.

## Operational Response and Alerting

A practical alert should detect more than `lag > 0`. Brief lag is normal. For this incident, alert on a combination such as:

- nonzero lag sustained for five minutes;
- no committed-offset movement during the same window;
- no active consumer member or repeated application failures;
- any increase in the DLQ end offset.

The first response should preserve the application error and topic/partition/offset, confirm dependency health, inspect the source value safely, and choose an approved error policy. DLQ routing restores pipeline availability but does not finish the business process. Assign an owner to correct, validate, replay, and audit rejected insurance transactions, and protect the DLQ because its records may contain sensitive data.

## Analysis Questions

1. Why did the producer report success for invalid JSON?
2. Which evidence distinguishes this stalled group from a merely slow group?
3. Why does restarting Kafka or MongoDB fail to solve the incident?
4. Why must DLQ delivery succeed before the source offset is committed?
5. Why can the strict-run MongoDB count differ between students?
6. Why does zero source lag not imply that MongoDB contains 13 documents?
7. What monitoring and ownership are required so a DLQ does not become silent data loss?

## Stop or Reset

Preserve the evidence while stopping the services:

```bash
docker compose -f kafka/docker-compose.yml down
docker compose -f mongodb/docker-compose.yml down
```

**Expected output:** the containers stop while named volumes retain the source record, group offsets, DLQ evidence, and MongoDB documents. Repeat section 2 when you want a clean Lab 3 run.
