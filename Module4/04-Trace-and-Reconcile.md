# Walkthrough 04: Trace MongoDB → Kafka → MongoDB

## Prepare

Run the scoped reset from `README.md`, then redeploy both configurations and wait for `RUNNING` tasks.

## Insert Source Documents

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.connector_source.insertMany([
      {order_id: "CONNECT-1001", customer_id: "CUST-1001", quantity: 1, status: "created"},
      {order_id: "CONNECT-1002", customer_id: "CUST-1002", quantity: 2, status: "created"},
      {order_id: "CONNECT-1003", customer_id: "CUST-1003", quantity: 1, status: "created"}
    ])'
```

**Expected output:** `insertMany` reports `acknowledged: true` and three generated ObjectIds. **Meaning:** three committed changes are now available to the source connector's MongoDB change stream.

The MongoDB source connector reads the replica-set change stream and writes full documents to `workshop-cdc.workshop.connector_source`.

## Trace Kafka

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server localhost:9092 \
  --topic workshop-cdc.workshop.connector_source

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic workshop-cdc.workshop.connector_source --from-beginning --max-messages 3 \
  --formatter-property print.key=true --formatter-property key.separator=' | '
```

**Expected output:** end offsets total at least three; the console consumer prints three full JSON documents containing `CONNECT-1001` through `CONNECT-1003`. **Meaning:** the source connector published the MongoDB changes to Kafka.

## Reconcile the Sink

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson({source: db.connector_source.countDocuments({}), sink: db.connector_sink.countDocuments({})});
    db.connector_sink.find({}, {_id: 0, order_id: 1, customer_id: 1, quantity: 1, status: 1}).sort({order_id: 1}).forEach(printjson)'
```

**Expected output:** `{ source: 3, sink: 3 }` followed by three matching projected order documents. **Meaning:** count and sampled fields reconcile across the asynchronous source-topic-sink path.

Wait briefly and repeat if the asynchronous pipeline is still moving. Success invariants:

- both tasks are `RUNNING`;
- Kafka contains at least three new records;
- source and sink counts match for the test batch;
- selected business fields match by `order_id`;
- DLQ did not grow for valid records.

Availability and zero lag do not prove semantic equivalence. Reconciliation is a separate control.
