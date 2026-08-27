# Walkthrough 03: Index Maintenance for a Changing Workload

## Goal

Treat an index as a controlled production change with measurable benefit and cost.

## Baseline and Proposal

The support team filters by `customer_id`. Capture the unindexed plan from walkthrough 02 and current index size:

```bash
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/monitor_mongodb.py snapshot
```

Proposed change: create `{customer_id: 1}` named `customer_id_1`. Success means `IXSCAN`, fewer documents examined, correct results, and acceptable index storage.

## Apply and Validate

Python:

```bash
python demo/inspect_mongodb.py create-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/monitor_mongodb.py index-usage
```

Equivalent native commands:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print(db.orders.createIndex({customer_id: 1}, {name: "customer_id_1"}));
    printjson(db.orders.find({customer_id: "CUST-1001"}).explain("executionStats"));
    db.orders.aggregate([{$indexStats: {}}]).forEach(printjson)'
```

Run the lookup more than once, then inspect index operations again. `$indexStats` counters reset when the process restarts and therefore require monitoring over time.

## Rollback

```bash
python demo/inspect_mongodb.py drop-index
```

Rollback is appropriate if write cost, storage, or a regression exceeds the approved boundary—not merely because creation took time. Recreate the index before continuing:

```bash
python demo/inspect_mongodb.py create-index
```

## Discussion

Explain why prefix order matters for a future compound index such as `{region: 1, created_at: -1}` and why indexes with zero observed use should be reviewed, not automatically deleted.
