# Walkthrough 03: Retention, Compaction, Topic Configuration, and Lifecycle

## Goal

Inspect effective settings, apply a scoped change, and remove the override as rollback.

## Create an Isolated Topic

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic workshop-lifecycle \
  --partitions 3 --replication-factor 1
```

Describe topic overrides and broker defaults:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-lifecycle --describe

docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type brokers --entity-default --describe
```

An absent topic override means the broker default is effective; it does not mean retention is unlimited.

## Apply a Reviewed Lifecycle Change

For a keyed latest-state topic, apply compaction plus seven-day delete retention:

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-lifecycle --alter \
  --add-config 'cleanup.policy=[compact,delete],retention.ms=604800000,min.cleanable.dirty.ratio=0.5'
```

Verify with `--describe`. `compact,delete` means compaction retains the latest value per key while delete retention can remove old segments. Neither action is immediate, and neither guarantees a fixed record count.

Produce updates and a tombstone with native tools:

```bash
printf '%s\n' \
  'customer-1|{"status":"bronze"}' \
  'customer-1|{"status":"silver"}' \
  'customer-2|{"status":"gold"}' \
  'customer-2|NULL' \
| docker compose -f kafka/docker-compose.yml exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 \
    --topic workshop-lifecycle \
    --reader-property parse.key=true --reader-property key.separator='|' \
    --reader-property null.marker=NULL
```

The final line produces a null-valued tombstone for `customer-2`.

## Rollback and Cleanup

```bash
docker compose -f kafka/docker-compose.yml exec kafka \
  /opt/kafka/bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --entity-type topics --entity-name workshop-lifecycle --alter \
  --delete-config cleanup.policy,retention.ms,min.cleanable.dirty.ratio
```

Confirm the overrides disappeared, then use the cleanup command in `README.md`. Never test aggressive retention on the primary order topic.
