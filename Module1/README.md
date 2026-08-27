# Module 1: Operational Architecture Review

This module turns the four architecture topics from the course outline into runnable walkthroughs. Students use the fictional Northwind Outfitters order pipeline introduced in [`USECASE.md`](../USECASE.md).

## Learning Objectives

By the end of this module, students should be able to:

- Trace an event across application, Kafka, processing, and MongoDB layers.
- Assign monitoring and first-response responsibilities to the correct operational layer.
- Collect before-and-after evidence for deployments and configuration changes.
- Distinguish slow queries, broker pressure, worker failures, lag, hot partitions, and data drift.
- Choose a recovery action without restarting healthy components unnecessarily.

## Module Files

| Course-outline bullet | Walkthrough |
| --- | --- |
| How MongoDB, Kafka, and Kafka Connect work together | [01 - Production Event-Driven Architecture](01-Production-Architecture.md) |
| Operational responsibilities across layers | [02 - Operational Responsibilities](02-Operational-Responsibilities.md) |
| Maintenance windows, deployment patterns, and change control | [03 - Maintenance, Deployment, and Change Control](03-Maintenance-Deployment-Change-Control.md) |
| Slow queries, broker pressure, connector failures, lag, and data drift | [04 - Typical Failure Points](04-Typical-Failure-Points.md) |

After the walkthroughs, complete [Exercises.md](Exercises.md). Instructor guidance and expected findings are in [Exercises-Solutions.md](Exercises-Solutions.md).

## Lab Architecture

```text
demo/producer.py
      |
      v
Kafka topic: workshop-orders
      |
      v
demo/consumer.py  (Kafka Connect sink-worker analogue)
      |
      v
MongoDB: workshop.orders

Invalid records -> workshop-orders-dlq
```

The walkthroughs also provide a native command-line implementation using separate resources:

```text
demo/data/orders.jsonl
      |
      v  jq + kafka-console-producer.sh
Kafka topic: workshop-orders-cli
      |
      v  kafka-console-consumer.sh + jq + mongoimport
MongoDB: workshop.orders_cli

CLI invalid records -> workshop-orders-cli-dlq
CLI consumer group   -> workshop-order-processor-cli
```

The repository intentionally uses a small Python consumer instead of a Kafka Connect runtime. It exhibits the same introductory operational concepts:

| Python demo | Kafka Connect equivalent |
| --- | --- |
| `consumer.py` process | Connect worker running a sink connector |
| `workshop-order-processor` group | Connector task offset ownership |
| One running consumer | One sink task |
| Consumer exit on invalid JSON | Failed connector task |
| `--on-error dlq` | Error tolerance and dead-letter queue policy |
| Consumer output | Worker and task logs |

Kafka Connect REST status, plugin installation, distributed-worker coordination, and MongoDB Connector configuration are deferred. When those components are introduced, students should transfer the same evidence-first troubleshooting method to worker, connector, and task status.

## Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose v2
- Python 3.10 or newer
- A terminal opened at the repository root
- At least two terminal windows for concurrent producer and consumer work
- `jq` for the Bash command-line implementation

Confirm the tools are available:

```bash
docker --version
docker compose version
python3 --version
jq --version
```

On Windows, use `py --version` if `python3` is unavailable. The full CLI pipelines target Bash on Linux, macOS, WSL, or Git Bash.

## One-Time Python Setup

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

Activate this environment in every terminal that runs a Python demo program.

## Start the Lab Services

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
docker compose -f kafka/docker-compose.yml up -d --wait
python demo/setup_demo.py
```

Verify the baseline:

```bash
docker compose -f mongodb/docker-compose.yml ps
docker compose -f kafka/docker-compose.yml ps
python demo/inspect_mongodb.py health
```

Both containers should be healthy, and MongoDB should report `rs0` with one writable primary.

## Command-Line Resource Setup

Export these names in every Bash terminal used for the CLI path:

```bash
export CLI_TOPIC=workshop-orders-cli
export CLI_DLQ_TOPIC=workshop-orders-cli-dlq
export CLI_GROUP=workshop-order-processor-cli
export CLI_COLLECTION=orders_cli
```

Create the isolated CLI topics:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --create --if-not-exists \
  --topic "$CLI_TOPIC" --partitions 3 --replication-factor 1

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --create --if-not-exists \
  --topic "$CLI_DLQ_TOPIC" --partitions 1 --replication-factor 1
```

The Python and CLI paths are intentionally isolated so they can be compared without sharing records, offsets, or MongoDB documents.

### Reset the CLI Resources

Stop any running CLI consumer first. The following reset is destructive only to
the four exported CLI resources:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --delete --group "$CLI_GROUP" \
  2>/dev/null || true

for topic in "$CLI_TOPIC" "$CLI_DLQ_TOPIC"; do
  docker compose -f kafka/docker-compose.yml exec kafka \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 --delete --if-exists --topic "$topic"
done

for attempt in $(seq 1 20); do
  topics=$(docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list)
  if ! printf '%s\n' "$topics" | grep -Eq "^(${CLI_TOPIC}|${CLI_DLQ_TOPIC})$"; then
    break
  fi
  sleep 0.5
done

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --create \
  --topic "$CLI_TOPIC" --partitions 3 --replication-factor 1

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --create \
  --topic "$CLI_DLQ_TOPIC" --partitions 1 --replication-factor 1

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.orders_cli.drop()'
```

## Reset Between Walkthroughs

Use the scoped reset when a walkthrough requests a clean state:

```bash
python demo/setup_demo.py --reset
```

> [!WARNING]
> This deletes and recreates `workshop-orders` and `workshop-orders-dlq`, and drops `workshop.orders`. It does not affect other Kafka topics or MongoDB collections.

Exact offsets and partition assignments may differ between runs. Evaluate relationships such as `LOG-END-OFFSET - CURRENT-OFFSET = LAG`, not fixed numbers.

## Python and CLI Guarantee Difference

The Python consumer writes MongoDB first and commits the Kafka source offset only after the write succeeds. The teaching shell pipeline uses `kafka-console-consumer`, `jq`, and `mongoimport` as separate processes. It is transparent and useful for inspection, but it is not transactional: Kafka offset commits and downstream import success are not coordinated. Manual CLI DLQ steps similarly demonstrate preservation of a poison record without replacing a production worker error policy.

## Recommended Sequence

1. Complete walkthroughs 01 through 04 in order.
2. Reset the demo before starting the graded exercises.
3. Complete `Exercises.md` without opening the solutions.
4. Record commands, evidence, conclusions, recovery actions, and verification results.
5. Compare the work with `Exercises-Solutions.md` only after submitting answers.

## Stop the Lab

Stop Python consumers with `Ctrl+C`. Preserve service data while stopping containers:

```bash
docker compose -f kafka/docker-compose.yml down
docker compose -f mongodb/docker-compose.yml down
```

Do not use `--volumes` unless the instructor explicitly requests a complete data reset.
