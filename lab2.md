# Lab 2: Debugging MongoDB Query and Index Problems Behind Kafka

## Objectives

By the end of this lab, you will be able to:

- Connect slow MongoDB operations to slow Kafka offset commits and rising consumer lag.
- Read the most useful fields from MongoDB `explain("executionStats")` output.
- Diagnose a missing index, a query that cannot use an existing index, and an index that cannot satisfy a sort.
- Use Kafka end offsets and consumer-group offsets to confirm whether a MongoDB fix improves end-to-end processing.

## Scenario

The insurance transaction consumer from [Lab 1](lab1.md) writes each Kafka record to MongoDB with this operation:

```python
collection.replace_one(
    {"transaction_id": event["transaction_id"]},
    document,
    upsert=True,
)
consumer.commit(message=message, asynchronous=False)
```

The database write happens before the Kafka commit. That ordering protects the record if MongoDB fails, but it also means MongoDB latency directly limits how quickly the group can commit offsets:

```text
Kafka record -> MongoDB lookup/upsert -> Kafka offset commit -> next record
                    slow here                 delayed here
                                                   |
                                                   v
                                           consumer lag grows
```

This lab uses an isolated topic, group, and database:

| Resource | Lab 2 value |
| --- | --- |
| Kafka topic | `insurance-transactions-lab2` |
| Consumer group | `insurance-mongodb-writer-lab2` |
| MongoDB namespace | `insurance_lab2.transactions` |
| Test records | 3,000 logical insurance transactions |

> [!NOTE]
> Query timings depend on the computer and may be small in this local lab. Plan shape and examined-record counts are more reliable evidence than elapsed time alone.

## The Query Evidence to Watch

MongoDB's execution statistics answer four key questions:

| Field or stage | Meaning |
| --- | --- |
| `COLLSCAN` | MongoDB read documents from the collection because it had no usable index path. |
| `IXSCAN` | MongoDB traversed an index. This is helpful only when the index avoids substantial work. |
| `SORT` | MongoDB performed a blocking in-memory or on-disk sort because input was not already in the requested order. |
| `nReturned` | Documents returned by the query. |
| `totalDocsExamined` | Collection documents fetched or tested. |
| `totalKeysExamined` | Index entries scanned. |
| `executionTimeMillis` | Server execution time for this run; use it as supporting, not sole, evidence. |

A useful efficiency ratio is `totalDocsExamined / nReturned`. A point lookup returning one document after examining 3,000 is a strong indexing problem. A result of one examined for one returned is much healthier.

## Before You Begin

Run commands from the repository root. Create the Python environment if necessary, then start both services:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demo/requirements.txt

docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
```

**Expected output:** dependency installation succeeds and both containers become healthy. **Meaning:** the insurance client can reach Kafka on `localhost:9092` and MongoDB on `localhost:27017`.

## 1. Prepare a Clean Lab 2 Environment

Stop any prior Lab 2 consumer before resetting. Delete only Lab 2 resources:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --delete --group insurance-mongodb-writer-lab2 || true

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete --if-exists --topic insurance-transactions-lab2

until ! docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list \
  | grep -Fxq insurance-transactions-lab2; do sleep 0.5; done

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.transactions.drop()'
```

**Expected output:** deletion succeeds, or the group-deletion command reports that a first-time group does not exist. `db.transactions.drop()` prints `true` if the collection existed and `false` otherwise. **Meaning:** Lab 1 and the module datasets are untouched; Lab 2 starts without records or indexes.

Create the Kafka topic:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic insurance-transactions-lab2 \
  --partitions 3 --replication-factor 1
```

Expected output:

```text
Created topic insurance-transactions-lab2.
```

## Scenario 1: A Missing Index Slows the Kafka Sink

### 1A. Create a Kafka backlog

Publish 3,000 insurance transactions. Progress is summarized every 500 acknowledgements so the terminal remains readable:

```bash
python demo/insurance_client.py produce \
  --topic insurance-transactions-lab2 \
  --id-prefix LAB2-TXN \
  --count 3000 --interval-ms 0 --report-every 500
```

Representative final output:

```text
[delivered] count=3000 transaction=<transaction-id> partition=<partition> offset=<offset>
[done] delivered=3000 failed=0 unflushed=0 topic=insurance-transactions-lab2
```

**Meaning:** Kafka acknowledged all 3,000 records. Partition and offset values vary, but the partition end offsets must sum to 3,000.

Verify the backlog before starting the consumer:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab2
```

Representative output:

```text
insurance-transactions-lab2:0:750
insurance-transactions-lab2:1:750
insurance-transactions-lab2:2:1500
```

**Meaning:** the exact split depends on Kafka's key hashing. The sum is the important invariant: 3,000 records are available for the new group.

### 1B. Consume without the required MongoDB index

In terminal 1, time the consumer. Do not create an index yet:

```bash
time python demo/insurance_client.py consume \
  --topic insurance-transactions-lab2 \
  --group-id insurance-mongodb-writer-lab2 \
  --mongodb-database insurance_lab2 \
  --max-messages 3000 --delay-ms 0 --report-every 500
```

Representative progress:

```text
[ready] topic=insurance-transactions-lab2 group=insurance-mongodb-writer-lab2 sink=insurance_lab2.transactions
[stored] count=1 transaction=<transaction-id> action=inserted partition=<partition> offset=<offset>
[stored] count=500 ... action=inserted ...
...
[done] processed=3000
```

**Meaning:** every upsert searches for a matching `transaction_id`, but that field has no index. As the collection grows, MongoDB has progressively more documents to inspect. Record order differs because Kafka preserves order within each partition, not globally across the topic. Save the `real` time printed by your shell as supporting evidence.

While terminal 1 runs, repeatedly execute this in terminal 2:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group insurance-mongodb-writer-lab2
```

Representative row while processing:

```text
GROUP                              PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG
insurance-mongodb-writer-lab2      2         340            1500           1160
```

**Meaning:** end offsets stay fixed because production is complete, while committed offsets advance only after MongoDB writes. Falling lag means the consumer is progressing; slow or flattening movement points to limited downstream throughput.

### 1C. Prove the missing-index problem

After consumption finishes, explain an exact transaction lookup:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const e = db.transactions.find({transaction_id: "LAB2-TXN-2999"})
      .explain("executionStats");
    printjson({
      winningPlan: e.queryPlanner.winningPlan,
      nReturned: e.executionStats.nReturned,
      docsExamined: e.executionStats.totalDocsExamined,
      keysExamined: e.executionStats.totalKeysExamined,
      millis: e.executionStats.executionTimeMillis
    });
  '
```

Representative evidence:

```text
winningPlan: { stage: 'COLLSCAN', ... }
nReturned: 1
docsExamined: 3000
keysExamined: 0
```

**Analysis:** the query returns one document but examines the whole collection. The same predicate is used by every upsert, so this is not merely a reporting-query issue—it is on the Kafka consumer's critical path.

### 1D. Add the index and replay

Create a unique index matching the upsert predicate:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.transactions.createIndex({transaction_id: 1}, {unique: true})'
```

Expected output:

```text
transaction_id_1
```

**Meaning:** MongoDB can now locate a transaction by its ID and enforces one document per ID.

Publish the same deterministic transactions again and consume the replay:

```bash
python demo/insurance_client.py produce \
  --topic insurance-transactions-lab2 \
  --id-prefix LAB2-TXN \
  --count 3000 --interval-ms 0 --report-every 500

time python demo/insurance_client.py consume \
  --topic insurance-transactions-lab2 \
  --group-id insurance-mongodb-writer-lab2 \
  --mongodb-database insurance_lab2 \
  --max-messages 3000 --delay-ms 0 --report-every 500
```

Expected result: producer offsets advance by another 3,000; consumer actions are `updated`; group lag returns to zero; MongoDB still contains 3,000 documents. The second runtime should normally improve, although synchronous Kafka commits and local machine load also contribute to total time.

Run the same explain command again. Representative evidence is now:

```text
winningPlan: { stage: 'FETCH', inputStage: { stage: 'IXSCAN', ... } }
nReturned: 1
docsExamined: 1
keysExamined: 1
```

**Analysis:** the plan and examined counts prove the fix more reliably than timing alone. The Kafka group confirms the operational outcome when committed offsets catch up to end offsets.

## Scenario 2: An Index Exists, but the Query Cannot Use It

An index is not automatically useful for every expression involving its field. Explain a case-insensitive lookup that transforms every stored value:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const e = db.transactions.find({
      $expr: {$eq: [{$toUpper: "$transaction_id"}, "LAB2-TXN-2999"]}
    }).explain("executionStats");
    printjson({
      winningPlan: e.queryPlanner.winningPlan,
      nReturned: e.executionStats.nReturned,
      docsExamined: e.executionStats.totalDocsExamined,
      keysExamined: e.executionStats.totalKeysExamined
    });
  '
```

Representative evidence:

```text
winningPlan: { stage: 'COLLSCAN', ... }
nReturned: 1
docsExamined: 3000
keysExamined: 0
```

**Analysis:** `transaction_id_1` exists, but applying `$toUpper` to the stored field prevents a direct ordered-index lookup. This is a **non-sargable** predicate: MongoDB must compute the expression for candidate documents.

Compare it with the direct equality form:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const e = db.transactions.find({transaction_id: "LAB2-TXN-2999"})
      .explain("executionStats");
    printjson({
      winningPlan: e.queryPlanner.winningPlan,
      nReturned: e.executionStats.nReturned,
      docsExamined: e.executionStats.totalDocsExamined,
      keysExamined: e.executionStats.totalKeysExamined
    });
  '
```

Expected evidence: the direct query contains `IXSCAN` and examines approximately one key and one document.

**Kafka relevance:** if a consumer performs the transformed lookup for every event—for deduplication, policy enrichment, or fraud checks—the presence of an index may create false confidence. Monitor the plan actually used, then verify that consumer commits advance faster and lag falls after changing the query. For real case-insensitive matching, consider normalized data or an index/query pair using the same collation rather than transforming every stored value at runtime.

## Scenario 3: An Index Filters but Cannot Satisfy the Sort

An insurance service asks for the 20 latest transactions for one policy. First create an index that supports only the equality filter:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.transactions.dropIndex("policy_id_1_occurred_at_-1");
  ' || true

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.transactions.createIndex({policy_id: 1})'
```

Expected output ends with `policy_id_1`. A missing compound index during cleanup may print an error that `|| true` ignores.

Explain the latest-transactions query. The diagnostic hint makes this comparison deterministic; do not treat hints as the default production fix.

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const e = db.transactions.find({policy_id: "POL-1001"})
      .sort({occurred_at: -1}).limit(20).hint({policy_id: 1})
      .explain("executionStats");
    printjson({
      winningPlan: e.queryPlanner.winningPlan,
      nReturned: e.executionStats.nReturned,
      docsExamined: e.executionStats.totalDocsExamined,
      keysExamined: e.executionStats.totalKeysExamined
    });
  '
```

Representative evidence:

```text
winningPlan: { stage: 'SORT', inputStage: { ... stage: 'IXSCAN' ... } }
nReturned: 20
docsExamined: 750
keysExamined: 750
```

**Analysis:** `policy_id_1` finds the policy's records, but those index entries are not ordered by `occurred_at`. MongoDB must fetch and sort roughly one quarter of the 3,000-record dataset before returning 20.

Create a compound index using equality fields first and the sort field next:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.transactions.createIndex({policy_id: 1, occurred_at: -1})'
```

Expected output:

```text
policy_id_1_occurred_at_-1
```

Explain again while hinting the compound index:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const e = db.transactions.find({policy_id: "POL-1001"})
      .sort({occurred_at: -1}).limit(20)
      .hint({policy_id: 1, occurred_at: -1})
      .explain("executionStats");
    printjson({
      winningPlan: e.queryPlanner.winningPlan,
      nReturned: e.executionStats.nReturned,
      docsExamined: e.executionStats.totalDocsExamined,
      keysExamined: e.executionStats.totalKeysExamined
    });
  '
```

Expected evidence: the winning plan contains `IXSCAN` without a blocking `SORT`, returns 20, and examines about 20 keys and 20 documents.

**Kafka relevance:** enrichment and routing consumers often request the latest policy state before processing an event. A blocking sort increases per-record time even though an index appears in the plan. Kafka shows the accumulated operational effect as a widening gap between end and committed offsets.

## Final Verification

Check all three layers:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic insurance-transactions-lab2

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group insurance-mongodb-writer-lab2

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/insurance_lab2?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print("documents=" + db.transactions.countDocuments());
    printjson(db.transactions.getIndexes().map(i => ({name: i.name, key: i.key})));
  '
```

Expected invariants after the replay:

- Kafka end offsets sum to 6,000.
- Consumer committed offsets equal end offsets, so total lag is zero.
- MongoDB contains 3,000 documents because replay used idempotent upserts.
- MongoDB lists `_id_`, `transaction_id_1`, `policy_id_1`, and `policy_id_1_occurred_at_-1`.

## Analysis Questions

1. Why is `executionTimeMillis` alone weaker evidence than plan shape and examined counts?
2. In Scenario 1, why can Kafka remain healthy while consumer lag grows?
3. Why does the `$toUpper` expression prevent use of the existing transaction ID index?
4. Why does `{policy_id: 1}` help filtering but not sorting by `occurred_at`?
5. Why does zero lag still require a separate MongoDB document-count check?
6. Which index would you retain in production, and what write/storage costs would you evaluate before keeping it?

## Cleanup or Preserve the Evidence

Regular Compose shutdown preserves the Lab 2 topic and database for later inspection:

```bash
docker compose -f kafka/docker-compose.yml down
docker compose -f mongodb/docker-compose.yml down
```

To rerun the lab, start the services and repeat section 1. The reset removes only `insurance-transactions-lab2`, group `insurance-mongodb-writer-lab2`, and database collection `insurance_lab2.transactions`.
