# MongoDB and Apache Kafka Workshop Environment

This repository provides persistent, single-node MongoDB and Apache Kafka services for the monitoring workshop. The services run independently, so you can start either one or both.

> [!WARNING]
> These services use no authentication, encryption, or network access controls beyond binding their host ports to `127.0.0.1`. They are intended only for local workshop use and are not production-ready.

## Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose v2 (`docker compose`)
- Python 3.10 or newer
- Bash, `curl`, and `jq` for native walkthroughs
- Enough free disk space for the images and persistent workshop data

Confirm that Docker is running:

```bash
docker --version
docker compose version
docker info
python3 --version
curl --version
jq --version
```

Run all commands below from the repository root unless a section says otherwise.

## Six-Hour Workshop Sequence

| Time | Material |
| --- | --- |
| 60 minutes | [Module 1 - Operational Architecture Review](Module1/README.md) |
| 75 minutes | [Module 2 - MongoDB Monitoring and Maintenance](Module2/README.md) |
| 75 minutes | [Module 3 - Kafka Monitoring and Maintenance](Module3/README.md) |
| 90 minutes | [Module 4 - Kafka Connect and MongoDB Connector Operations](Module4/README.md) |
| 60 minutes | [Final Activity - Operations Runbook](FinalActivity/README.md) |

The theoretical scenario and executable fault catalogue are in [USECASE.md](USECASE.md). Each module contains per-outline-bullet walkthroughs, student exercises, and instructor solutions.

Start with [Lab 1 - Insurance Transactions from Kafka to MongoDB](lab1.md)
for a small client application and a guided introduction to Kafka monitoring.

## MongoDB

The MongoDB environment runs MongoDB 8.3.8 as a single-node replica set named `rs0`. A replica set enables change streams needed by later MongoDB Kafka source-connector exercises.

The Compose service sets `GLIBC_TUNABLES=glibc.pthread.rseq=1`. This is a compatibility workaround for MongoDB [SERVER-121912](https://jira.mongodb.org/browse/SERVER-121912), which otherwise prevents current MongoDB 8.x releases from starting on Linux kernels 6.19 and newer.

Start MongoDB and wait until it is ready:

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
```

Check its status and logs:

```bash
docker compose -f mongodb/docker-compose.yml ps
docker compose -f mongodb/docker-compose.yml logs -f mongodb
```

Press `Ctrl+C` to stop following the logs; the container continues to run.

Open a MongoDB shell:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/?replicaSet=rs0&directConnection=true'
```

Useful connection strings:

- From applications on the host: `mongodb://localhost:27017/?replicaSet=rs0&directConnection=true`
- From a future container on the same Docker network: `mongodb://mongodb:27017/?replicaSet=rs0`

### MongoDB smoke test

Insert and read a workshop document:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.healthchecks.insertOne({service: "mongodb", checkedAt: new Date()}); db.healthchecks.find().toArray()'
```

Verify replica-set health:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'rs.status().members.map(({name, stateStr, health}) => ({name, stateStr, health}))'
```

Stop MongoDB without deleting its data:

```bash
docker compose -f mongodb/docker-compose.yml down
```

## Apache Kafka

The Kafka environment runs Apache Kafka 4.3.1 as a single combined KRaft broker and controller. ZooKeeper is not required.

Start Kafka and wait until it is ready:

```bash
docker compose -f kafka/docker-compose.yml up -d --wait
```

Check its status and logs:

```bash
docker compose -f kafka/docker-compose.yml ps
docker compose -f kafka/docker-compose.yml logs -f kafka
```

Press `Ctrl+C` to stop following the logs; the container continues to run.

Useful bootstrap servers:

- From applications on the host: `localhost:9092`
- From a future container on the same Docker network: `kafka:19092`

### Kafka producer and consumer primer

A **producer** sends records to a Kafka topic. A **consumer** reads records from a
topic. Most exercises use one of two interfaces for those roles:

| Role | Python demo | Kafka command-line utility |
| --- | --- | --- |
| Producer | `python demo/producer.py` | `/opt/kafka/bin/kafka-console-producer.sh` |
| Consumer | `python demo/consumer.py` | `/opt/kafka/bin/kafka-console-consumer.sh` |

The `kafka-console-producer.sh` and `kafka-console-consumer.sh` files are standard
utilities supplied by the official Apache Kafka distribution in the Kafka
container. They were not created or customized for this repository. The
`/opt/kafka/bin` path exists inside the container, so the commands invoke them
through `docker compose exec kafka`; they do not need to be installed on the
host.

This is the anatomy of the common command prefix:

```text
docker compose -f kafka/docker-compose.yml exec -T kafka /opt/kafka/bin/<tool>.sh
|              selects this Compose project |   |      command inside the container      |
|                                             |   service name
|                                             disable a pseudo-terminal for piped input
```

Both utilities connect to the broker with `--bootstrap-server localhost:9092`.
Here, `localhost` means the Kafka container itself because the utility is running
inside that container. The `--topic` option selects the named stream of records.

The producer does not send directly to a particular consumer. Kafka retains each
record in the topic according to its retention policy, and consumers track their
own positions using offsets. Reading a record does not delete it. Consumers in
the same group share the topic's partitions; consumers in different groups can
independently read the same records. This is why an exercise may produce once but
consume or replay the data with more than one group.

#### Console producer

The console producer reads one input line at a time from standard input and
publishes each line as one Kafka record. For example:

```bash
printf '%s\n' '{"event":"workshop-started"}' | \
  docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic workshop-events
```

**Expected output:** no output when the record is accepted. The shell prompt
returns after `printf` closes the pipe. **Meaning:** silence is normal for a
successful console-producer run; use a consumer or inspect topic offsets to prove
that Kafka stored the record. The `-T` option is important in pipelines because
it prevents Docker from allocating an interactive terminal.

Some exercises send a key and JSON value on the same line:

```text
CUST-1001|{"event_type":"order.created","order_id":"cli-ORD-0001"}
```

They add these producer options:

```text
--reader-property parse.key=true --reader-property key.separator='|'
```

The portion before the first `|` becomes the Kafka record key, and the portion
after it becomes the value. Kafka uses the key to choose a partition, which lets
records with the same key retain their order within that partition. The separator
is only input syntax and is not stored as part of the key or value.

Without piped input, the producer is interactive: type one record per line and
press `Ctrl+D` on Linux/macOS to close its input. Use `Ctrl+C` to cancel it.

#### Console consumer

The console consumer prints each record value it receives, normally one record
per line:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic workshop-events \
  --from-beginning --max-messages 1
```

Representative output:

```text
{"event":"workshop-started"}
Processed a total of 1 messages
```

**Meaning:** the consumer read one stored record and then stopped because of
`--max-messages 1`. The final summary may be written to standard error, but it is
informational.

Frequently used consumer options are:

| Option | Meaning |
| --- | --- |
| `--from-beginning` | Start at the earliest retained record when there is no applicable saved group position. |
| `--max-messages N` | Exit successfully after printing `N` records. Useful for deterministic exercises. |
| `--group GROUP_ID` | Join a named consumer group and save progress as committed offsets. |
| `--property print.key=true` or `--formatter-property print.key=true` | Print the record key as well as its value; the accepted spelling depends on the selected formatter and Kafka command version. |
| `--property key.separator=' | '` or `--formatter-property key.separator=' | '` | Put a visible separator between a printed key and value. |
| `--timeout-ms N` | Stop after `N` milliseconds without a record. Kafka may print a `TimeoutException`; in an observation command, that usually means no additional record arrived rather than that the broker failed. |

Without `--max-messages` or a timeout, a consumer is expected to keep waiting for
new records. Stop it with `Ctrl+C`. Also remember that `--from-beginning` does not
erase a named group's committed offsets: a group normally resumes from its saved
position. Use a new group ID when an exercise requires an independent replay.

The console tools expose Kafka directly and are useful for inspection. The Python
programs add the workshop's application behavior: structured order generation,
validation, MongoDB upserts, error handling, and deliberate fault controls. A
console consumer printing a record proves that Kafka can return it; it does not
prove that the Python consumer processed it or that MongoDB stored it.

### Kafka smoke test

Create and inspect a topic:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic workshop-events \
  --partitions 3 --replication-factor 1

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --describe --topic workshop-events
```

Produce a test event:

```bash
printf '%s\n' '{"event":"workshop-started"}' | \
  docker compose -f kafka/docker-compose.yml exec -T kafka \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic workshop-events
```

Consume the test event:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic workshop-events \
  --from-beginning --max-messages 1
```

Stop Kafka without deleting its data:

```bash
docker compose -f kafka/docker-compose.yml down
```

## Kafka Connect and MongoDB Connector

Module 4 uses Apache Kafka Connect 4.3.1 with the official MongoDB Kafka Connector 3.0.0. Start MongoDB and Kafka first so their Docker networks exist, then build and start Connect:

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
docker compose -f connect/docker-compose.yml up -d --build --wait
```

Verify the loopback-only REST API and connector plugins:

```bash
curl -fsS http://localhost:8083/connector-plugins | jq
python demo/connect_admin.py plugins
```

Stop Connect before the backing services:

```bash
docker compose -f connect/docker-compose.yml down
```

## Start or stop both services

Start both environments:

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
```

Stop both environments while retaining their data:

```bash
docker compose -f connect/docker-compose.yml down
docker compose -f kafka/docker-compose.yml down
docker compose -f mongodb/docker-compose.yml down
```

## Order-processing sample application

The theoretical scenario and discussion questions are in [USECASE.md](USECASE.md). The `demo/` directory contains dummy orders and small Python programs that publish orders to Kafka, consume them, and write them to MongoDB.

### Install the Python dependencies

Python 3.10 or newer is recommended. Create an isolated virtual environment from the repository root.

Linux and macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demo/requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r demo/requirements.txt
```

Start MongoDB and Kafka using the earlier instructions, then verify the services and create the main and dead-letter topics:

```bash
python demo/setup_demo.py
```

The setup command is idempotent and can be run more than once. To begin a fault exercise from a clean state, reset only the workshop topics and `workshop.orders` collection:

```bash
python demo/setup_demo.py --reset
```

This reset is destructive to the demo orders and topic records, but does not affect other MongoDB collections or Kafka topics.

### Run the happy path

In terminal 1, start the consumer. It will continue until you press `Ctrl+C`:

```bash
python demo/consumer.py
```

In terminal 2, publish the 20 dummy orders:

```bash
python demo/producer.py
```

Inspect the MongoDB results:

```bash
python demo/inspect_mongodb.py health
python demo/inspect_mongodb.py stats
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

Each producer run creates new `order_id` values. Replaying the same Kafka event remains safe because the consumer upserts by `order_id`.

### Create and inspect consumer lag

Stop terminal 1's consumer with `Ctrl+C`, then publish 20 copies of the dataset as quickly as possible:

```bash
python demo/producer.py --repeat 20 --interval-ms 0
```

Inspect the backlog:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group workshop-order-processor --describe
```

Restart the consumer with a visible quarter-second processing delay:

```bash
python demo/consumer.py --delay-ms 250
```

Run the consumer-group command again while the consumer works. The `LAG` values should eventually fall to zero. Use `Ctrl+C` to stop the consumer after the backlog is processed.

If you want an independent run without existing committed offsets, supply the same new group name to both the consumer and the inspection command:

```bash
python demo/consumer.py --group-id workshop-order-processor-2
```

### Compare an unindexed and indexed MongoDB query

Ensure the demonstration index is absent, then explain the customer query:

```bash
python demo/inspect_mongodb.py drop-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

The plan should contain `COLLSCAN`, and the number of documents examined will be larger than the number returned. Create the index and run the same query again:

```bash
python demo/inspect_mongodb.py create-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

The plan should now contain `IXSCAN` and examine index keys instead of scanning the full collection.

### Continue with operational failures

[USECASE.md](USECASE.md) contains executable fault exercises that build on the happy path:

- MongoDB health, storage growth, query plans, indexes, backup, and restore
- Kafka lag, hot partitions, topic health, and unsafe retention
- A poison record that stops the consumer and is recovered through a DLQ
- Duplicate delivery and idempotent replay

The producer and consumer expose these fault controls without changing the normal defaults:

```bash
python demo/producer.py --help
python demo/consumer.py --help
```

### Configuration overrides

The programs work with the supplied local Docker services by default. These environment variables override their settings when needed:

- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_TOPIC`
- `KAFKA_DLQ_TOPIC`
- `KAFKA_GROUP_ID`
- `MONGODB_URI`
- `MONGODB_DATABASE`
- `MONGODB_COLLECTION`

## Persistent data

MongoDB data is stored in `mongodb-workshop-data`, MongoDB backup archives in `mongodb-workshop-backups`, and Kafka data—including Connect distributed-worker state—in `kafka-workshop-data`. Regular `docker compose down`, container restarts, and container recreation preserve these volumes.

To verify persistence, run the smoke tests, stop and restart the services, and then query the MongoDB collection or consume the Kafka topic again.

To permanently delete the workshop data, stop the relevant environment with the `--volumes` option:

```bash
# Destructive: permanently removes all MongoDB workshop data.
docker compose -f mongodb/docker-compose.yml down --volumes

# Destructive: permanently removes all Kafka workshop data.
docker compose -f kafka/docker-compose.yml down --volumes
```

## Troubleshooting

### A service does not become healthy

Inspect its status and recent logs:

```bash
docker compose -f mongodb/docker-compose.yml ps
docker compose -f mongodb/docker-compose.yml logs --tail=100 mongodb

docker compose -f kafka/docker-compose.yml ps
docker compose -f kafka/docker-compose.yml logs --tail=100 kafka
```

On the first start, Docker must download the images and initialize the persistent data, so startup can take longer than subsequent runs.

MongoDB 8.x has a known incompatibility with Linux kernels 6.19 and newer. The supplied Compose file includes the required `GLIBC_TUNABLES` workaround; retain that environment setting if you adapt the MongoDB service.

### Port already in use

MongoDB requires host port `27017`, and Kafka requires host port `9092`. Stop the application already using the affected port, then start the Compose environment again.

On Linux, identify listeners with:

```bash
ss -ltnp | grep -E ':(27017|9092)\b'
```

### Reset a broken local environment

If preserving the workshop data is not necessary, remove the affected environment and its volume using the destructive `down --volumes` command shown above, then start it again. This creates a completely new MongoDB replica set or Kafka cluster.
