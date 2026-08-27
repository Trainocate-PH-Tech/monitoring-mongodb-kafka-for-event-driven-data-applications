# Walkthrough 04: Typical Failure Points

## Course-Outline Topic

Typical failure points: slow queries, broker pressure, connector failures, lag, and data drift.

## Method

For every station:

1. Create one controlled fault.
2. Observe before changing anything.
3. Identify the first unhealthy layer.
4. Recover only that layer or configuration.
5. Verify the business flow and operational signals.

Reset between stations unless instructed otherwise:

```bash
python demo/setup_demo.py --reset
```

**Expected output:** setup ends with `[ready]` and reports the scoped topic/collection reset. **Meaning:** the next station starts without records, offsets, or documents left by the previous fault.

That command resets the Python demo only. For a command-line station, instead run
the scoped commands in [Reset the CLI Resources](README.md#reset-the-cli-resources).

## Station A: Slow or Inefficient MongoDB Query

Load 500 orders:

```bash
python demo/producer.py --repeat 25 --interval-ms 0
python demo/consumer.py --max-messages 500
```

**Expected output:** the producer reports 500 delivered records and the consumer ends with `processed=500 rejected=0`. **Meaning:** a sufficiently larger collection is available for comparing query work.

Remove the demonstration index and explain the query:

```bash
python demo/inspect_mongodb.py drop-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

**Expected output:** the index is absent and the query reports `plan stages: COLLSCAN`, many documents examined, and zero keys examined. **Meaning:** MongoDB scanned the collection instead of navigating an index.

Evidence of the problem:

- `COLLSCAN` appears in the plan.
- Documents examined is substantially greater than documents returned.
- No index keys are examined.

Apply and verify the maintenance action:

```bash
python demo/inspect_mongodb.py create-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/inspect_mongodb.py stats
```

**Expected output:** creation reports `customer_id_1`; the plan changes to `IXSCAN`/`FETCH`, examined work falls near returned rows, and stats list the index. **Meaning:** the targeted maintenance action fixed the measured query pattern.

The plan should contain `IXSCAN`, with documents examined close to documents returned.

### Command-Line Alternative

Load 500 unique CLI orders by adding a batch suffix to each template, then run the CLI sink:

```bash
for batch in $(seq 1 25); do
  jq --arg batch "$batch" -r '
    . as $source
    | (del(.sample_order_id) + {
        event_type: "order.created",
        event_id: ("cli-event-" + $source.sample_order_id + "-" + $batch),
        order_id: ("cli-" + $source.sample_order_id + "-" + $batch),
        created_at: (now | todateiso8601)
      }) as $event
    | $event.customer_id + "|" + ($event | tojson)
  ' demo/data/orders.jsonl
done \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
    --reader-property parse.key=true --reader-property key.separator='|'

docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
  --group "$CLI_GROUP" --from-beginning --max-messages 500 \
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

**Expected output:** the producer stage is silent; the consumer reports 500 messages; `mongoimport` reports 500 successful documents and zero failures. **Meaning:** the isolated CLI collection now has 500 unique orders for the same query-plan comparison.

Use the `mongosh` explain/create-index/drop-index commands from [walkthrough 03](03-Maintenance-Deployment-Change-Control.md#3-change-and-roll-back-the-cli-collection-index) to observe the same `COLLSCAN` to `IXSCAN` improvement.

## Station B: Broker Pressure and Hot Partitions

Reset, then publish 500 records as quickly as possible using one key:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 25 --interval-ms 0 --key-mode hot
```

**Expected output:** reset succeeds and the producer reports 500 deliveries. **Meaning:** all records used the same Kafka key and therefore target one partition.

Inspect partition end offsets, data-directory growth, and recent broker logs:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic workshop-orders

docker compose -f kafka/docker-compose.yml exec kafka \
  du -sh /var/lib/kafka/data

docker compose -f kafka/docker-compose.yml logs --tail=100 kafka
```

**Expected output:** one offset line is approximately `:500` while the others are `:0`; `du` prints the log-directory size; logs should not show a fatal broker error. **Meaning:** this is severe partition skew, not necessarily actual resource exhaustion.

All records should land on one partition. This small burst will not exhaust the lab broker, but it demonstrates the workload shape that can produce uneven CPU, network, disk, and consumer capacity in production.

Compare with customer keys:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --repeat 25 --interval-ms 0 --key-mode customer
```

**Expected output:** 500 records are delivered and a repeated offset check shows records in more than one partition. **Meaning:** higher-cardinality customer keys distribute the workload better than one constant key.

Run `kafka-get-offsets.sh` again. More than one partition should contain records.

### Command-Line Alternative

Reset the CLI resources, then force every keyed line to `HOT-CUSTOMER`:

```bash
for batch in $(seq 1 25); do
  jq --arg batch "$batch" -r '
    . as $source
    | (del(.sample_order_id) + {
        event_type: "order.created",
        event_id: ("cli-hot-event-" + $source.sample_order_id + "-" + $batch),
        order_id: ("cli-hot-" + $source.sample_order_id + "-" + $batch),
        created_at: (now | todateiso8601)
      }) as $event
    | "HOT-CUSTOMER|" + ($event | tojson)
  ' demo/data/orders.jsonl
done \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
    --reader-property parse.key=true --reader-property key.separator='|'
```

**Expected output:** no producer output on success; end offsets later show all 500 records on one CLI partition. **Meaning:** the native producer reproduced the hot-key workload.

Inspect `$CLI_TOPIC` with `kafka-get-offsets.sh`. One partition should contain all 500 records. This is the same skew generated by Python's `--key-mode hot`.

## Station C: Consumer Lag

With the consumer stopped, publish a burst:

```bash
python demo/producer.py --repeat 20 --interval-ms 0
```

**Expected output:** `expected=400 delivered=400 failed=0`. **Meaning:** the stopped consumer now has a 400-record source backlog.

Inspect lag:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

**Expected output:** after the group exists, `LOG-END-OFFSET` exceeds `CURRENT-OFFSET` and total `LAG` is nonzero. **Meaning:** Kafka is retaining records the group has not yet completed.

Start a deliberately slow consumer:

```bash
python demo/consumer.py --delay-ms 250
```

**Expected output:** progress appears roughly four records per second; repeated group descriptions show committed offsets rising and lag falling. **Meaning:** the consumer is slow but making progress, which differs from a stall.

In another terminal, repeat the group description. Observe committed offsets advancing while log-end offsets remain fixed. Stop the consumer only after lag reaches zero.

Lag is a symptom. Possible causes include a stopped worker, expensive processing, slow MongoDB writes, rebalances, insufficient task/partition parallelism, or an unexpectedly high producer rate.

### Command-Line Alternative

Produce a CLI burst using the batch loop from Station A. Start this throttled shell sink:

```bash
docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
  --group "$CLI_GROUP" --from-beginning --max-messages 500 \
| while IFS= read -r event; do
    sleep 0.25
    printf '%s\n' "$event"
  done \
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

**Expected output:** message/import progress takes about 125 seconds for 500 records because of the 250 ms delay. Kafka lag and MongoDB count may move at different times. **Meaning:** shell stages buffer independently and do not coordinate commits with sink durability.

Describe `$CLI_GROUP` from another terminal. The shell delay limits downstream throughput, but the console consumer can buffer and commit independently of `mongoimport`. Compare Kafka lag with MongoDB document growth; their divergence is evidence that this shell pipeline lacks the Python worker's write-before-commit guarantee.

## Station D: Connector-Style Failure and DLQ

Reset. Start the default consumer in terminal 1:

```bash
python demo/setup_demo.py --reset
python demo/consumer.py
```

**Expected output:** setup resets the lab; the consumer prints `[ready]` and waits for records. **Meaning:** the worker is healthy before the poison event is introduced.

Publish valid orders plus one malformed JSON record from terminal 2:

```bash
python demo/producer.py --inject-invalid
```

**Expected output:** the producer reports 21 delivered records and `[inject] Published one malformed JSON record`; the consumer reports an invalid-event error with partition/offset and exits nonzero. **Meaning:** one poison record stopped the default strict worker without committing that record.

The consumer should stop at the poison record without committing that offset. It may encounter the invalid record before valid records in other partitions because Kafka has no global cross-partition order.

Collect evidence:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

**Expected output:** at least one partition retains nonzero lag or an unadvanced committed position at the poison offset. **Meaning:** Kafka preserved work after the worker failure.

Recover with DLQ handling:

```bash
python demo/consumer.py --on-error dlq
```

**Expected output:** `[dlq] Sent invalid event ...`, normal progress, and eventual zero lag. **Meaning:** the recovery worker preserved the bad record in the DLQ, committed its source position, and continued valid processing.

After `[dlq]` appears and lag reaches zero, stop the consumer. Inspect the DLQ payload and source metadata:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic workshop-orders-dlq --from-beginning \
  --max-messages 1 --formatter-property print.headers=true
```

**Expected output:** headers identify source topic, partition, offset, and error, followed by the malformed payload; the consumer reports one message. **Meaning:** the DLQ retains both the rejected data and enough context to investigate or replay it.

In Kafka Connect, this pattern appears as a failed task or a task configured with retries, error tolerance, and DLQ settings. DLQ delivery must succeed before the source offset is committed.

### Command-Line Alternative

Publish one malformed value after the normal CLI producer command:

```bash
printf '%s\n' 'INVALID-RECORD|{"event_type":"order.created","order_id":' \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
    --reader-property parse.key=true --reader-property key.separator='|'
```

**Expected output:** no producer output on success; the CLI source topic end-offset sum increases by one. **Meaning:** Kafka accepted the malformed bytes even though they are not valid JSON.

Run the CLI sink with Bash pipeline failure detection:

```bash
set -o pipefail
docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic "$CLI_TOPIC" \
  --group "$CLI_GROUP" --from-beginning --max-messages 21 \
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

**Expected output:** `jq` reports a JSON parse error and the pipeline returns nonzero with `pipefail`; some valid documents may already have imported. **Meaning:** the malformed value broke transformation, and shell-level progress is not transactionally tied to Kafka commits.

`jq` should report malformed JSON. The console consumer may nevertheless have advanced its group offset because its commits are not coordinated with the failed downstream command.

Preserve the bad record manually as a DLQ envelope:

```bash
jq -nc \
  --arg source_topic "$CLI_TOPIC" \
  --arg error 'malformed JSON: incomplete order_id value' \
  --arg raw '{"event_type":"order.created","order_id":' \
  '{source_topic: $source_topic, error: $error, raw_record: $raw}' \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 --topic "$CLI_DLQ_TOPIC"
```

**Expected output:** no producer output on success; the CLI DLQ end offset increases by one. **Meaning:** a JSON envelope preserving source topic, error, and raw value was published manually.

This preserves evidence but is a manual teaching procedure. The Python policy and a production connector can couple DLQ success to source-offset handling more safely.

## Station E: Data Drift

Reset and load a healthy dataset:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --interval-ms 0
python demo/consumer.py --max-messages 20
```

**Expected output:** reset succeeds, 20 records are delivered, and the consumer reports 20 processed with zero rejected. **Meaning:** data drift will be introduced into an otherwise healthy source-to-sink result.

Simulate an unauthorized or incorrect downstream update by removing `region` from one MongoDB document:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.orders.findOneAndUpdate({}, {$unset: {region: ""}}, {returnDocument: "after"}))'
```

**Expected output:** one order document is printed without a `region` field. **Meaning:** MongoDB remained available, but one business document was changed incorrectly downstream.

Audit required fields:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson({total: db.orders.countDocuments({}), missingRegion: db.orders.countDocuments({region: {$exists: false}})})'
```

**Expected output:** `{ total: 20, missingRegion: 1 }`. **Meaning:** availability and count are normal while a field-level quality invariant is broken.

Kafka and the consumer group can both be healthy while stored business data is wrong. Offset monitoring alone cannot detect semantic drift.

For this controlled lab, recover by resetting and replaying the source dataset:

```bash
python demo/setup_demo.py --reset
python demo/producer.py --interval-ms 0
python demo/consumer.py --max-messages 20
```

**Expected output:** the clean replay again produces/processes 20 records; the audit should return `missingRegion: 0`. **Meaning:** this lab reset rebuilt correct sink state from a known source, though production repair needs stronger controls.

Production recovery requires an approved source of truth, defined validation rules, an auditable correction, and careful replay or backfill controls.

### Command-Line Alternative

Run the same audit against the CLI collection:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.orders_cli.updateOne({}, {$unset: {region: ""}});
    printjson({
      total: db.orders_cli.countDocuments({}),
      missingRegion: db.orders_cli.countDocuments({region: {$exists: false}})
    });'
```

**Expected output:** the update reports one matched/modified document and the summary reports `missingRegion: 1`. **Meaning:** the CLI sink can also be semantically wrong while Kafka and MongoDB service health remain green.

The Kafka CLI can prove topic and offset health, while `mongosh` proves the sink data drifted. Neither implementation can infer the correct missing value without consulting the source event or another system of record.

## Failure Comparison

| Symptom | Kafka healthy? | Worker healthy? | MongoDB healthy? | Primary evidence |
| --- | --- | --- | --- | --- |
| `COLLSCAN` | Yes | Yes | Available but inefficient | Query plan |
| Hot partition | Usually | Possibly constrained | Yes | Per-partition offsets |
| Consumer lag | Usually | Slow/stopped/blocked | Possibly | Group offsets and lag |
| Poison record | Yes | Failed | Usually | Worker error and uncommitted offset |
| Data drift | Yes | May be healthy | Available but incorrect data | Data-quality audit |

## Completion Check

For each station, propose one alert signal, one first-response command, one owner, and one condition that requires escalation.
