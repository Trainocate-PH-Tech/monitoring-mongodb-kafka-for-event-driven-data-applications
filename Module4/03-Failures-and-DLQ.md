# Walkthrough 03: Failed Tasks, Malformed Records, Retries, and DLQ

## A. Reject a Misconfigured Dependency

Attempt to apply the intentionally wrong MongoDB port:

```bash
python demo/connect_admin.py apply Module4/connectors/sink-bad-uri.json
```

**Expected output:** after the connection timeout, `[error] Connect returned HTTP 400` with `Unable to connect to the server`; exit status is nonzero. **Meaning:** validation rejected the bad desired state before replacing the running config.

Connector 3.0 validates connectivity and should reject the PUT with HTTP 400 after its connection timeout. Prove that the approved configuration and healthy task were not replaced:

```bash
curl -fsS http://localhost:8083/connectors/workshop-mongo-sink/config | jq '."connection.uri"'
python demo/connect_admin.py status workshop-mongo-sink
docker compose -f connect/docker-compose.yml logs --tail=200 connect
```

**Expected output:** config still prints URI `mongodb://mongodb:27017/...`; status remains task `RUNNING`; logs contain the rejected `27018` connection attempt. **Meaning:** the approved running connector survived the failed change.

This is a rejected change, not a failed running task. Restarting services would not make port `27018` correct.

## B. Drive a Task to `FAILED`

Apply the strict error policy and then publish malformed JSON:

```bash
python demo/connect_admin.py apply Module4/connectors/sink-strict.json

printf '%s\n' 'strict-not-json' \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 \
    --topic workshop-cdc.workshop.connector_source

python demo/connect_admin.py wait workshop-mongo-sink --state FAILED --timeout 60
```

**Expected output:** apply succeeds, console production is silent, and wait prints connector `RUNNING` with task 0 `FAILED` plus `Tolerance exceeded in error handler`/JSON conversion trace. **Meaning:** strict policy turned one malformed record into a task failure while the worker stayed available.

The task trace identifies the converter stage and source topic/offset. Kafka, the worker REST API, source connector, and MongoDB remain healthy.

Repair and restart failed tasks:

```bash
python demo/connect_admin.py apply Module4/connectors/sink.json
curl -fsS -X POST \
  'http://localhost:8083/connectors/workshop-mongo-sink/restart?includeTasks=true&onlyFailed=true' \
  | jq
python demo/connect_admin.py wait workshop-mongo-sink
```

**Expected output:** tolerant config is applied, restart may briefly show `RESTARTING`, and wait ends with connector/task `RUNNING`. **Meaning:** only the failed processing layer was repaired; the poison offset can now be handled by the DLQ policy.

The bad record was not committed under the strict policy. After enabling the tolerant policy, it should be routed to the DLQ and processing can continue.

## C. Malformed Record and DLQ

With the good sink configuration running, publish another value that the JSON converter cannot parse:

```bash
printf '%s\n' 'dlq-not-json' \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 \
    --topic workshop-cdc.workshop.connector_source
```

**Expected output:** no producer output on success and the CDC topic end offset increases by one. **Meaning:** Kafka stores raw bytes without requiring them to be valid JSON for this consumer.

Inspect the DLQ including framework headers:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic workshop-connect-dlq --from-beginning --max-messages 1 \
  --formatter-property print.headers=true
```

**Expected output:** one record with `__connect.errors.*` headers naming topic, partition, offset, connector, task, stage, exception, and raw malformed value. **Meaning:** Connect preserved the rejected record and diagnostic context while keeping the task running.

Then verify that the sink task remains `RUNNING`. `errors.tolerance=all` preserves pipeline availability, but an unmonitored DLQ silently hides data loss.

## Retry Discussion

Framework retry controls apply to retriable processing failures; dependency drivers may also retry internally. Define a bounded retry window, backoff, DLQ policy, alert, and replay owner. Never assume every exception is safe to retry indefinitely.
