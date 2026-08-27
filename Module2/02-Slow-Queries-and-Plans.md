# Walkthrough 02: Slow-Query Signals and Query Plans

## Goal

Correlate a captured operation with its execution plan, then prove why the query is inefficient.

## Create the Signal

Remove the demonstration index, briefly profile all operations, run the customer lookup, and disable profiling immediately afterward:

```bash
python demo/inspect_mongodb.py drop-index

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.setProfilingLevel(1, {slowms: 0, sampleRate: 1})'

python demo/inspect_mongodb.py query --customer-id CUST-1001

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.setProfilingLevel(0)'
```

Profiling every operation has overhead; the zero-millisecond threshold is only for this short lab.

## Read the Evidence

Python summary:

```bash
python demo/monitor_mongodb.py profile --limit 5
python demo/inspect_mongodb.py query --customer-id CUST-1001
```

Native profiler and explain evidence:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.system.profile.find(
      {ns: "workshop.orders"},
      {ts: 1, millis: 1, planSummary: 1, docsExamined: 1, nreturned: 1, command: 1}
    ).sort({$natural: -1}).limit(5).forEach(printjson)'
```

Evidence of inefficiency is `COLLSCAN` plus a high `totalDocsExamined / nReturned` ratio. Milliseconds alone are not enough: this small lab can execute a wasteful scan quickly.

## Log Check

```bash
docker compose -f mongodb/docker-compose.yml logs --tail=150 mongodb \
  | grep -E 'Slow query|planSummary|COLLSCAN' || true
```

Do not create an index yet; preserve the plan as the pre-change baseline for walkthrough 03.
