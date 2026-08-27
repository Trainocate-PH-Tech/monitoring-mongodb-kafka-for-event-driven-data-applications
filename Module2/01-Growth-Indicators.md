# Walkthrough 01: Database, Collection, Index, and Storage Growth

## Goal

Measure growth at two points and distinguish logical data size, allocated storage, and index size.

## Python Walkthrough

Capture a 100-document baseline:

```bash
python demo/monitor_mongodb.py snapshot
python demo/inspect_mongodb.py stats
```

Add and process 400 more orders, then repeat the commands:

```bash
python demo/producer.py --repeat 20 --interval-ms 0
python demo/consumer.py --max-messages 400
python demo/monitor_mongodb.py snapshot
```

Calculate the deltas for documents, collection data bytes, allocated storage bytes, and index bytes. Allocated storage need not grow in exact proportion to logical data.

## Native Command Walkthrough

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const d = db.stats(1);
    const c = db.orders.stats({scale: 1});
    printjson({database: {collections: d.collections, dataSize: d.dataSize, storageSize: d.storageSize, indexSize: d.indexSize}});
    printjson({collection: {count: c.count, size: c.size, storageSize: c.storageSize, totalIndexSize: c.totalIndexSize, indexSizes: c.indexSizes}});
    printjson({indexes: db.orders.getIndexes()});'
```

Check the volume and database process independently:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb du -sh /data/db
docker compose -f mongodb/docker-compose.yml stats --no-stream mongodb
```

## Interpretation

- `count` and `size` describe logical workload growth.
- `storageSize` describes allocated collection storage.
- `totalIndexSize` is capacity consumed by all indexes.
- Filesystem usage includes journal, oplog, metadata, and free space, so it will not equal collection storage.
- A single reading is not a trend. Alerts require a rate and a forecast to a capacity limit.

Record which measure answers “how much business data exists?” and which answers “when will the disk fill?”
