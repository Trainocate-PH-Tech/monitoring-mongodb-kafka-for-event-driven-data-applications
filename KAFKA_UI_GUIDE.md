# Kafka Administration with Kafbat UI

This guide introduces the local Kafbat UI web application and shows how to use it to inspect and administer the Apache Kafka workshop cluster before moving to Kafka command-line tools.

The examples use isolated resources whose names begin with `kafbat-ui-`. Do not edit or delete the course topics `workshop-orders`, `workshop-orders-dlq`, Kafka Connect internal topics, or any other resource not explicitly named in this guide.

Complete the independent exercises in [KAFKA_UI_EXERCISES.md](KAFKA_UI_EXERCISES.md) after reading this guide.

## 1. Scope and Limitations

Kafbat UI is useful for:

- seeing whether the configured Kafka cluster is reachable;
- browsing brokers, topics, partitions, replicas, and topic configuration;
- creating isolated topics;
- producing records with keys, values, and headers;
- browsing record metadata and payloads;
- inspecting consumer groups, committed offsets, and lag;
- reviewing or changing topic-level configuration;
- correlating visual observations with Kafka command-line evidence.

Kafbat UI does not replace:

- production metrics, alerting, and historical dashboards;
- broker, controller, disk, network, and JVM monitoring;
- authentication, authorization, TLS, and audit controls;
- change approval, rollback, and incident records;
- application-level processing and data reconciliation;
- Kafka command-line or API evidence needed for repeatable runbooks.

The workshop UI is write-enabled and the local Kafka broker has no authentication or TLS. Both services are bound to the host loopback interface. Do not expose ports `8080` or `9092` to another host.

## 2. Start Kafka and Kafbat UI

Run commands from the repository root:

```bash
docker compose -f kafka/docker-compose.yml up -d --wait
```

The same Compose project starts:

| Service | Purpose | Host endpoint |
| --- | --- | --- |
| `kafka` | Apache Kafka 4.3.1 broker/controller | `localhost:9092` |
| `kafbat-ui` | Kafka web interface | `http://localhost:8080` |

Confirm both services are healthy:

```bash
docker compose -f kafka/docker-compose.yml ps
```

Check the Kafbat health endpoint:

```bash
curl -fsS http://localhost:8080/actuator/health
```

Expected response:

```json
{"status":"UP"}
```

Check Kafbat build information:

```bash
curl -fsS http://localhost:8080/actuator/info
```

The build version should report `v1.5.0`.

## 3. Open the UI and Select the Cluster

Open:

```text
http://localhost:8080
```

No web login is configured in this local workshop. Select the cluster named:

```text
workshop
```

The Kafbat container connects to Kafka through the internal Docker listener:

```text
kafka:19092
```

Applications on the host continue to use:

```text
localhost:9092
```

Do not configure the UI container to use `localhost:9092`. Inside that container, `localhost` means the Kafbat container itself.

## 4. Read the Cluster Overview

The cluster overview should show:

- cluster name `workshop`;
- status `ONLINE`;
- one broker;
- KRaft controller mode;
- topic and online-partition counts;
- read-only status `false`.

The exact topic and partition totals vary because course setup and Kafka Connect create resources over time.

### What the Overview Proves

- Kafbat can reach Kafka.
- Kafka returned cluster metadata.
- The configured broker is responding.
- Kafbat can enumerate topics and partitions.

### What It Does Not Prove

- The broker has adequate disk, CPU, memory, or network capacity.
- A consumer is processing records.
- A downstream MongoDB collection is correct.
- The single broker has redundancy or failover capability.
- Topic retention and application semantics are correct.

Corroborate the broker independently:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092
```

## 5. Browse Topics and Partitions

Open **Topics** from the cluster navigation. The topic list provides information such as:

- topic name;
- partition count;
- replication factor;
- number of records or offsets when available;
- internal-topic status;
- cleanup policy.

Select a topic to inspect its overview, partitions, messages, consumer relationships, and configuration.

For each partition, distinguish:

- partition number;
- current leader;
- replica set;
- in-sync replica set;
- earliest and latest offsets;
- approximate record count.

In this one-broker lab, a healthy workshop topic normally shows broker `1` as leader, replica, and ISR for every partition. This is internally consistent but provides no redundant replica.

Corroborate a topic through the command line:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic kafbat-ui-events
```

## 6. Create an Isolated Topic

Use the independent exercise topic:

```text
kafbat-ui-events
```

From **Topics**, select the create/add-topic control and enter:

| Setting | Value |
| --- | --- |
| Topic name | `kafbat-ui-events` |
| Partitions | `3` |
| Replication factor | `1` |
| Cleanup policy | `delete` or inherited default |

Leave other settings at their inherited defaults unless an exercise explicitly changes them.

After creation, verify:

- the topic appears in the topic list;
- it has exactly three partitions;
- every partition has a leader;
- replica and ISR each contain the single broker;
- end offsets begin at zero when the topic is new.

Command-line verification:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic kafbat-ui-events

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

## 7. Produce Records

Open `kafbat-ui-events`, select its **Messages** view, and open the produce-message control.

Enter a key:

```text
CUST-1001
```

Enter a JSON value:

```json
{
  "event_type": "order.created",
  "order_id": "UI-ORDER-1001",
  "customer_id": "CUST-1001",
  "quantity": 1,
  "status": "created"
}
```

Optionally add a header:

| Header | Value |
| --- | --- |
| `source` | `kafbat-ui-exercise` |

Produce the record, then confirm that the message view shows:

- topic and partition;
- offset;
- timestamp;
- key;
- headers when supplied;
- value.

Kafka accepts bytes and does not require every record value to be JSON. JSON formatting in the UI helps learners read the record; it is not broker-side schema validation.

## 8. Understand Keys and Partition Placement

Kafka hashes a non-null key to choose a partition. Records with the same key remain in the same partition while the topic's partition count remains unchanged.

Produce at least two records using `CUST-1001` and compare their partition numbers. They should match.

Produce additional records using `CUST-1002` and `CUST-1003`. Different keys may use different partitions, but a small number of keys is not guaranteed to distribute perfectly.

Operational interpretation:

- A stable key can preserve per-key ordering.
- One constant key forces all records to one partition.
- A hot partition limits consumer parallelism and can concentrate disk, network, and lag.
- Adding consumers beyond the partition count cannot increase active partition ownership.

Inspect end offsets independently:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

## 9. Browse and Filter Messages

Use the topic's **Messages** view to select:

- a partition or all partitions;
- an offset or time position;
- an appropriate result limit;
- key or value search/filter controls when available.

When reading the result, record the exact partition and offset. An offset is unique only within its partition; `partition 0, offset 5` and `partition 1, offset 5` are different records.

Do not infer processing success from message visibility. Seeing a source record proves Kafka retained and returned it, not that a named consumer committed it or that a sink stored it.

Command-line comparison:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events \
  --from-beginning --max-messages 1 \
  --property print.key=true \
  --property key.separator=' | '
```

## 10. Inspect Consumer Groups and Lag

A consumer group records committed next-read offsets for its partitions. Lag is:

```text
log end offset - committed offset
```

Open the **Consumers** or consumer-groups view and select:

```text
kafbat-ui-exercise-group
```

Inspect:

- topic and partition;
- committed offset;
- log-end offset;
- lag;
- active members and assignments when a consumer is running;
- group state.

Interpret movement rather than a single lag value:

| End offsets | Committed offsets | Interpretation |
| --- | --- | --- |
| Increasing | Increasing equally | Consumer is keeping up |
| Increasing | Increasing more slowly | Throughput deficit |
| Fixed | Increasing | Backlog is draining |
| Fixed or increasing | Fixed | Consumer is stopped, blocked, failed, or rebalancing |

A brief nonzero lag value is not automatically an incident. Alerting should include duration, progress, business tolerance, and ownership.

Command-line verification:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group kafbat-ui-exercise-group --describe
```

## 11. Review Topic Configuration

Open a topic's configuration/settings view and distinguish:

- explicit topic overrides;
- broker defaults inherited by the topic;
- values that affect retention, compaction, durability, or message limits.

Important examples:

| Setting | Meaning |
| --- | --- |
| `cleanup.policy` | Delete retention, compaction, or both |
| `retention.ms` | Time eligibility for old segments under delete cleanup |
| `retention.bytes` | Size-based retention boundary |
| `min.insync.replicas` | Minimum ISR required for writes using `acks=all` |
| `max.message.bytes` | Topic-level maximum record batch size |

An absent topic override usually means the broker default is effective; it does not mean the setting is unlimited.

Use only `kafbat-ui-lifecycle` for lifecycle changes. Record the old state and exact rollback before saving an override.

Verify effective topic overrides:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name kafbat-ui-lifecycle --describe
```

## 12. UI and Command-Line Evidence Map

| Administrative question | Kafbat view | Kafka command-line evidence |
| --- | --- | --- |
| Is the cluster reachable? | Cluster overview | `kafka-broker-api-versions.sh` |
| Does every partition have a leader? | Topic partitions | `kafka-topics.sh --describe` |
| Where are records stored? | Messages with partition/offset | `kafka-console-consumer.sh` |
| How far behind is a group? | Consumer-group lag | `kafka-consumer-groups.sh --describe` |
| Are offsets moving? | Refresh/live lag view | Repeated group descriptions |
| Are partitions balanced? | Partition record/offset distribution | `kafka-get-offsets.sh` |
| What configuration is explicit? | Topic settings | `kafka-configs.sh --describe` |
| Is disk or process pressure present? | Not sufficient alone | Docker/host metrics and broker logs |

The UI is excellent for discovery. Command-line commands are easier to copy into runbooks, automate, timestamp, compare, and attach to incident evidence.

## 13. Administrator Troubleshooting Method

For every UI or Kafka problem:

1. Record the time, cluster, topic, partition, group, requested operation, and observed error.
2. Preserve the browser message before retrying.
3. Check the Kafbat health endpoint and container status.
4. Check Kafbat logs for connection, timeout, or request errors.
5. Check Kafka health independently of the UI.
6. Reproduce only the read-only inspection through a Kafka command-line tool.
7. Identify whether the problem is browser, Kafbat, Docker networking, Kafka, topic configuration, consumer behavior, or record semantics.
8. Correct only the affected layer.
9. Verify both the operational signal and the original business observation.
10. Record rollback and cleanup actions.

Do not restart Kafka merely because the web page fails.

## 14. Collect a Diagnostic Bundle

```bash
date -u

docker compose -f kafka/docker-compose.yml ps

curl -fsS http://localhost:8080/actuator/health
curl -fsS http://localhost:8080/api/clusters

docker compose -f kafka/docker-compose.yml logs --since=10m kafbat-ui
docker compose -f kafka/docker-compose.yml logs --since=10m kafka

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic kafbat-ui-events

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

Add consumer-group and configuration evidence when those resources exist.

## 15. Troubleshoot Common Problems

### The Page Does Not Load

```bash
docker compose -f kafka/docker-compose.yml ps
curl -v http://localhost:8080/actuator/health
docker compose -f kafka/docker-compose.yml logs --tail=150 kafbat-ui
```

Interpretation:

- Connection refused: Kafbat is stopped, unhealthy, or port `8080` is occupied.
- Health response `UP`: the web process responds; continue to cluster-connectivity checks.
- Browser error while health is `UP`: inspect browser state and Kafbat request logs.

If Kafka remains healthy and only Kafbat is unhealthy, restart only Kafbat:

```bash
docker compose -f kafka/docker-compose.yml restart kafbat-ui
docker compose -f kafka/docker-compose.yml ps
curl -fsS http://localhost:8080/actuator/health
```

### The UI Opens but the Cluster Is Offline

Inspect Kafbat logs and the configured environment:

```bash
docker compose -f kafka/docker-compose.yml logs --tail=200 kafbat-ui
docker compose -f kafka/docker-compose.yml exec kafbat-ui env \
  | grep '^KAFKA_CLUSTERS_0_'
```

Verify Docker DNS from the Kafbat container:

```bash
docker compose -f kafka/docker-compose.yml exec kafbat-ui \
  getent hosts kafka
```

Verify that Kafka responds independently:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092
```

The Kafbat bootstrap address must be `kafka:19092`, not `localhost:9092`.

### A Topic Does Not Appear

1. Refresh the topic list once.
2. Check exact capitalization and cluster selection.
3. Confirm topic creation through the CLI.
4. Inspect Kafbat logs for request errors.
5. Do not create the same topic repeatedly with different settings.

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

### A Produced Message Does Not Appear

Check:

- exact cluster and topic;
- partition selection in the message browser;
- offset/time search position;
- result limit;
- whether a key/value filter is active;
- whether production returned an error;
- topic end-offset movement.

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic kafbat-ui-events
```

If the end offset increased, Kafka stored a record even if the current UI filter hides it.

### JSON Looks Invalid or Unformatted

Kafka stores bytes. It does not validate JSON unless an application, serializer, schema system, or connector performs validation.

- Confirm whether the value is intended to be a string, JSON, Avro, Protobuf, or another encoding.
- Inspect the raw value.
- Do not treat a formatting problem as a broker outage.
- Preserve malformed data and its topic/partition/offset before repair or replay.

### Consumer Lag Is Nonzero

Take at least two observations separated by time.

- End fixed, commits increasing: draining backlog.
- End increasing faster than commits: throughput deficit.
- Commits fixed with lag: stopped, blocked, failed, or rebalancing consumer.
- No group: the consumer may never have committed.

Correlate UI observations with:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group kafbat-ui-exercise-group --describe --members --verbose
```

Restarting the broker does not correct a slow consumer, bad message, hot key, or downstream database problem.

### A Topic Configuration Change Is Wrong

1. Preserve the current UI value and CLI description.
2. Stop further changes.
3. Compare with the approved baseline.
4. Remove only the incorrect topic override or restore the exact approved value.
5. Verify the effective configuration.
6. Check whether retention may already have removed data; rollback cannot restore deleted records.

### A Topic Was Deleted Accidentally

1. Stop all further administrative changes.
2. Record the topic, operator, time, UI action, and expected contents.
3. Preserve broker and Kafbat logs.
4. Identify the source of truth and retained upstream data.
5. Determine whether recreation and replay are authorized and safe.
6. Recreate only with approved partitions, replication, and configuration.
7. Reconcile replayed records and downstream state.

The UI has no undo function. Topic deletion can remove all retained records.

## 16. Safe Administrative Practices

- Use only isolated `kafbat-ui-*` resources for this guide.
- Confirm cluster, topic, partition, and group before changing anything.
- Record existing topic configuration before editing it.
- Treat topic deletion and retention reduction as destructive.
- Do not change internal topics.
- Do not reset consumer-group offsets without authorization and an exact partition/offset plan.
- Capture evidence before restarting a service.
- Restart only the unhealthy layer.
- Verify UI observations with repeatable commands.
- Remember that zero lag does not prove downstream data correctness.
- Use secured Kafka listeners, authorization, audit logging, protected UI access, and redundant brokers in production.

## 17. Stop the Environment

Stop Kafka and Kafbat while preserving the Kafka data volume:

```bash
docker compose -f kafka/docker-compose.yml down
```

Do not add `--volumes` unless permanent deletion of all Kafka workshop data is explicitly intended.
