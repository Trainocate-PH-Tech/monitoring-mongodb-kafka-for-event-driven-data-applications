# Walkthrough 03: Index Maintenance for a Changing Workload

## Goal

Treat an index as a controlled production change with measurable benefit and cost.

## Baseline and Proposal

The support team filters by `customer_id`. Capture the unindexed plan from walkthrough 02 and current index size:

```bash
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/monitor_mongodb.py snapshot
```

**Expected output:** `COLLSCAN`, high documents examined, zero index keys, plus baseline index bytes. **Meaning:** the proposed index has a quantified problem and storage baseline.

Proposed change: create `{customer_id: 1}` named `customer_id_1`. Success means `IXSCAN`, fewer documents examined, correct results, and acceptable index storage.

## Apply and Validate

Python:

```bash
python demo/inspect_mongodb.py create-index
python demo/inspect_mongodb.py query --customer-id CUST-1001
python demo/monitor_mongodb.py index-usage
```

**Expected output:** creation reports `customer_id_1`; explain changes to `IXSCAN`/`FETCH`; index usage lists `_id_` and `customer_id_1` with operation counters. **Meaning:** the index exists, supports the query, and can be monitored for actual use.

Equivalent native commands:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print(db.orders.createIndex({customer_id: 1}, {name: "customer_id_1"}));
    printjson(db.orders.find({customer_id: "CUST-1001"}).explain("executionStats"));
    db.orders.aggregate([{$indexStats: {}}]).forEach(printjson)'
```

**Expected output:** the index name, an `executionStats` plan containing `IXSCAN`, and `$indexStats` documents with `accesses.ops`. **Meaning:** native evidence confirms definition, plan selection, and observed usage.

Run the lookup more than once, then inspect index operations again. `$indexStats` counters reset when the process restarts and therefore require monitoring over time.

## Rollback

```bash
python demo/inspect_mongodb.py drop-index
```

**Expected output:** `[ok] Dropped index 'customer_id_1'`. **Meaning:** the rollback targets only the proposed index.

Rollback is appropriate if write cost, storage, or a regression exceeds the approved boundary—not merely because creation took time. Recreate the index before continuing:

```bash
python demo/inspect_mongodb.py create-index
```

**Expected output:** `[ok] Created index 'customer_id_1'`. **Meaning:** the approved final state is restored for later walkthroughs.

## Discussion

Explain why prefix order matters for a future compound index such as `{region: 1, created_at: -1}` and why indexes with zero observed use should be reviewed, not automatically deleted.
