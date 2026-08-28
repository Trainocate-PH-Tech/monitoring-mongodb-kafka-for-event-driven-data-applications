# MongoDB Administration with mongo-express

This guide shows how to perform simple MongoDB operations through the local mongo-express web application and how to troubleshoot those operations as an administrator.

The examples use an isolated database named `mongodb_express_guide` and a collection named `learners`. Do not perform the create, edit, or delete exercises in the course's `workshop` database.

For MongoDB concepts and equivalent `mongosh` commands, see [MONGODB_PRIMER.md](MONGODB_PRIMER.md).

## 1. Scope and Limitations

mongo-express is useful for:

- browsing databases, collections, and documents;
- creating databases and collections;
- inserting, editing, and deleting documents;
- running simple and advanced document filters;
- creating basic indexes;
- viewing database and collection statistics;
- importing and exporting data in supported formats.

mongo-express is not a complete production monitoring or database-management platform. It does not replace:

- MongoDB metrics and alerting;
- replica-set and election monitoring;
- database authentication, authorization, or auditing;
- tested backups and restores;
- slow-query profiling and `explain("executionStats")`;
- change approval, rollback, and incident records.

The workshop UI has write and delete access to every local database. Treat every button as an administrative action.

## 2. Start MongoDB and mongo-express

Run commands from the repository root:

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
```

Confirm that both services are healthy:

```bash
docker compose -f mongodb/docker-compose.yml ps
```

Expected services:

```text
mongodb        Up ... (healthy)   127.0.0.1:27017->27017/tcp
mongo-express  Up ... (healthy)   127.0.0.1:8081->8081/tcp
```

Check the web application status endpoint:

```bash
curl -fsS http://localhost:8081/status
```

Expected response:

```json
{"status":"ok"}
```

The status endpoint proves that the web process is responding. It does not prove that a particular database operation is correct.

## 3. Sign In

Open this address in a browser:

```text
http://localhost:8081
```

Default workshop login:

```text
Username: workshop
Password: workshop
```

An unauthenticated request to the home page should return HTTP `401`:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8081/
```

Expected output:

```text
401
```

Verify the configured login:

```bash
curl -u workshop:workshop -sS -o /dev/null -w '%{http_code}\n' \
  http://localhost:8081/
```

Expected output:

```text
200
```

> [!IMPORTANT]
> The web username and password protect only mongo-express. The training MongoDB server itself has no authentication or TLS. Both published ports are restricted to `127.0.0.1`; never expose this configuration to another host or use it as a production security design.

## 4. Understand the Home Page

The home page contains:

- a **Database** sidebar;
- a **Create Database** field;
- **View** and **Del** controls for each database;
- server information such as hostname, MongoDB version, uptime, connections, and operation counters.

The server-information panel is a useful point-in-time check, but it is not a historical dashboard. A value shown once does not reveal a trend, alert duration, or root cause.

## 5. Create a Safe Practice Database

1. Return to the mongo-express home page.
2. In **Create Database**, enter:

   ```text
   mongodb_express_guide
   ```

3. Select **Create Database**.
4. Select **View** beside `mongodb_express_guide`.
5. In **Create collection**, enter:

   ```text
   learners
   ```

6. Select **Create collection**.

The database page should now list `learners`. The page also shows database statistics such as collection count, object count, data size, storage size, and index size.

### Administrator Verification

Verify the collection independently with `mongosh`:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.getCollectionNames())'
```

Expected output includes:

```javascript
[ "learners" ]
```

If the UI reports success but the collection is absent, preserve the UI and MongoDB logs before retrying.

## 6. Insert Documents

### Insert the First Document

1. Open `mongodb_express_guide`.
2. Select **View** beside `learners`.
3. Select **New Document**.
4. Replace the editor contents with:

   ```javascript
   {
     _id: ObjectId(),
     name: "Ada Rivera",
     email: "ada@example.com",
     active: true,
     level: 1,
     skills: ["MongoDB"],
     enrolledAt: ISODate()
   }
   ```

5. Select **Save**.

The collection page should display the generated `_id` and the inserted fields.

### Insert Two More Documents

Use **New Document** once for each of the following documents:

```javascript
{
  _id: ObjectId(),
  name: "Ben Santos",
  email: "ben@example.com",
  active: true,
  level: 1,
  skills: ["MongoDB", "Kafka"]
}
```

```javascript
{
  _id: ObjectId(),
  name: "Cara Lim",
  email: "cara@example.com",
  active: false,
  level: 2,
  skills: ["Operations"]
}
```

### Expected Evidence

- The collection page reports three documents.
- Each document has a different `_id`.
- Boolean values display as Boolean values, not quoted strings.
- `skills` displays as an array.
- `enrolledAt` on Ada's document is stored as a date.

### Administrator Verification

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson({count: db.learners.countDocuments({})});
    db.learners.find({}, {_id: 0, name: 1, email: 1, active: 1, level: 1})
      .sort({name: 1}).forEach(printjson);'
```

Expected count:

```javascript
{ count: 3 }
```

## 7. Fetch and Filter Documents

The collection page provides **Simple** and **Advanced** search modes.

### Simple String Filter

On the **Simple** tab, enter:

| Control | Value |
| --- | --- |
| Key | `email` |
| Value | `ada@example.com` |
| Type | `String` |

Select **Find**. Only Ada's document should be returned.

### Simple Boolean Filter

Enter:

| Control | Value |
| --- | --- |
| Key | `active` |
| Value | `true` |
| Type | `JSON, bool` |

Select **Find**. Ada and Ben should be returned before the update exercise.

Selecting `String` instead of `JSON, bool` searches for the string `"true"`, which is a different BSON type and should not match Boolean values.

### Advanced Filter and Projection

Select the **Advanced** tab.

In **Query**, enter:

```json
{"active": true, "level": {"$gte": 1}}
```

In **Projection**, enter:

```json
{"_id": 0, "name": 1, "email": 1, "level": 1}
```

Select **Find**. The result should contain only the selected fields for active learners at level 1 or higher.

### Sort Results

After loading the collection, select a field heading such as `name` to change its sort direction. Confirm the direction visually rather than assuming the first click is ascending.

### Administrator Verification

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.learners.find(
      {active: true, level: {$gte: 1}},
      {_id: 0, name: 1, email: 1, level: 1}
    ).sort({name: 1}).forEach(printjson)'
```

## 8. Update a Document

1. Clear any collection filter or run a specific filter for `ada@example.com`.
2. Select Ada's document row or its blue link button.
3. The page changes to **Editing Document**.
4. Preserve the existing `_id`.
5. Change the document to include:

   ```javascript
   active: false,
   level: 2,
   skills: ["MongoDB", "Kafka"]
   ```

6. Select **Save**.
7. Return to the collection and filter by `email = ada@example.com`.

mongo-express saves the edited document as a complete document representation. Review every field before saving so an unrelated field is not accidentally removed or given a different type.

### Administrator Verification

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.findOne(
      {email: "ada@example.com"},
      {_id: 0, name: 1, active: 1, level: 1, skills: 1}
    ))'
```

Expected fields include:

```javascript
{
  name: "Ada Rivera",
  active: false,
  level: 2,
  skills: [ "MongoDB", "Kafka" ]
}
```

## 9. Delete a Document Safely

1. Use the Simple filter to fetch exactly `email = cara@example.com`.
2. Confirm the result shows only Cara's document.
3. Record its `_id`, email, and the pre-delete collection count.
4. Select the red trash button on that document's row.
5. Confirm the deletion.
6. Run the same filter again; it should return no documents.
7. Clear the filter and verify that two documents remain.

> [!WARNING]
> The collection page includes **Delete all N documents retrieved**. If no filter is active, this can delete the entire collection contents. A filter can also be broader than intended. For routine administration, prefer the trash button on one verified document and confirm the `_id` independently.

### Administrator Verification

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson({
      cara: db.learners.countDocuments({email: "cara@example.com"}),
      total: db.learners.countDocuments({})
    })'
```

Expected result:

```javascript
{ cara: 0, total: 2 }
```

mongo-express does not provide an undo button or a database transaction history. Recovery requires a valid source of truth, backup, or approved replay procedure.

## 10. Create and Inspect an Index

### Establish the Query First

The administration question is: does the collection need an index for frequent email lookups?

Capture the current indexes:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.learners.getIndexes())'
```

Initially, only the automatic `_id_` index should exist.

### Create the Index in mongo-express

1. Open `mongodb_express_guide.learners`.
2. Select **New Index**.
3. Enter:

   ```json
   {"email": 1}
   ```

4. Select **Save**.
5. Refresh the collection page and inspect its index information.

The expected generated index name is `email_1`.

### Verify the Index and Query Plan

mongo-express can create and list basic indexes, but use `explain("executionStats")` to prove that a query uses the index:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.getIndexes());
    printjson(db.learners.find({email: "ada@example.com"}).explain("executionStats"));'
```

Look for `IXSCAN` in the winning plan. On this tiny collection, elapsed time is not meaningful; the plan and examined-document counts are the evidence.

An index consumes storage and increases insert/update work. Create indexes for measured query needs, not merely because a field exists.

## 11. Inspect Database and Collection Statistics

### In mongo-express

On a database page, inspect:

- collection count;
- object count;
- data and storage size;
- index count and index size.

On a collection page, inspect:

- document count;
- total and average document size;
- allocated storage;
- index count and total index size.

### Corroborate with MongoDB

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.stats(1));
    printjson(db.learners.stats({scale: 1}));'
```

A UI statistic is a point-in-time value. Capacity administration requires repeated measurements, a growth rate, a threshold, and a forecast to that threshold.

## 12. Administrator Debugging Method

Use the same order for every problem:

1. Record the exact operation, database, collection, filter, expected result, actual result, and time.
2. Preserve the browser error and avoid repeated clicks.
3. Check the web endpoint and authentication.
4. Check the mongo-express container and logs.
5. Check MongoDB health independently.
6. Reproduce the read-only part of the operation with `mongosh`.
7. Identify whether the problem is browser/UI, web container, connectivity, MongoDB, query syntax/type, index, or data correctness.
8. Correct only the affected layer.
9. Verify through both the UI and `mongosh`.
10. Record the outcome and any rollback or data-repair action.

Do not restart MongoDB merely because the web page failed. Prove which layer is unhealthy first.

## 13. Collect a Diagnostic Bundle

Run this bundle from the repository root:

```bash
date -u

docker compose -f mongodb/docker-compose.yml ps

curl -fsS http://localhost:8081/status
curl -u workshop:workshop -sS -o /dev/null -w '%{http_code}\n' \
  http://localhost:8081/

docker compose -f mongodb/docker-compose.yml logs --since=10m mongo-express
docker compose -f mongodb/docker-compose.yml logs --since=10m mongodb

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const hello = db.hello();
    const status = rs.status();
    printjson({
      setName: hello.setName,
      writablePrimary: hello.isWritablePrimary,
      members: status.members.map(member => ({
        name: member.name,
        state: member.stateStr,
        health: member.health
      }))
    });'
```

Expected healthy database evidence:

- replica set `rs0`;
- `writablePrimary: true`;
- member `mongodb:27017` in `PRIMARY` state;
- member health `1`.

This proves the one local member is available and writable. It does not prove redundancy, because the lab has only one member.

## 14. Troubleshoot Common Problems

### The Browser Requests Credentials

This is expected. Use the configured mongo-express web credentials.

Check the expected responses:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8081/
curl -u workshop:workshop -sS -o /dev/null -w '%{http_code}\n' \
  http://localhost:8081/
```

Expected results are `401` and `200`.

If customized credentials fail, render the Compose configuration carefully:

```bash
docker compose -f mongodb/docker-compose.yml config
```

This output can contain resolved credentials. Do not paste it into tickets or public chat without redaction.

### The Page Does Not Load

Check service and port state:

```bash
docker compose -f mongodb/docker-compose.yml ps
curl -v http://localhost:8081/status
docker compose -f mongodb/docker-compose.yml logs --tail=100 mongo-express
```

Interpretation:

- Connection refused: the UI is stopped, unhealthy, or port `8081` is unavailable.
- HTTP `401` at `/`: the UI is running and requires credentials.
- `{"status":"ok"}` at `/status`: the web process responds; continue to database-connectivity checks.

If MongoDB is healthy and only mongo-express is unhealthy, restart only the UI:

```bash
docker compose -f mongodb/docker-compose.yml restart mongo-express
docker compose -f mongodb/docker-compose.yml ps
curl -fsS http://localhost:8081/status
```

### mongo-express Cannot Connect to MongoDB

Check both services and UI logs:

```bash
docker compose -f mongodb/docker-compose.yml ps
docker compose -f mongodb/docker-compose.yml logs --tail=150 mongo-express
```

Confirm that the UI container resolves the MongoDB service name:

```bash
docker compose -f mongodb/docker-compose.yml exec mongo-express \
  getent hosts mongodb
```

Confirm TCP connectivity from the UI container:

```bash
docker compose -f mongodb/docker-compose.yml exec mongo-express \
  node -e "const net=require('net'); const s=net.connect(27017,'mongodb',()=>{console.log('connected');s.end()});s.on('error',e=>{console.error(e.message);process.exit(1)})"
```

Expected output:

```text
connected
```

The container connection string must use the Docker service hostname, not host-local `localhost`:

```text
mongodb://mongodb:27017/?replicaSet=rs0
```

Inside the mongo-express container, `localhost` refers to mongo-express itself.

### A New Document Will Not Save

Common causes:

- invalid document syntax;
- missing commas or unmatched braces;
- quoted Boolean/number values with the wrong type;
- duplicate `_id` or another unique-index value;
- an attempt to change the immutable `_id` field;
- MongoDB unavailable or no writable primary.

Actions:

1. Copy the unsaved document text into a local incident note.
2. Read the browser error and mongo-express logs.
3. Confirm MongoDB writable-primary state.
4. Check existing indexes and conflicting values.
5. Correct the document once and retry.
6. Query by the intended business key to ensure the first attempt did not already succeed.

Check a possible duplicate email:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.find({email: "ada@example.com"}).toArray());
    printjson(db.learners.getIndexes());'
```

### A Filter Returns No Documents

Check:

- exact database and collection;
- exact field name and capitalization;
- whether the field is nested;
- selected Simple-filter type;
- string versus Boolean, number, date, or `ObjectId`;
- spaces or punctuation in the value;
- whether an Advanced query is valid JSON.

Type differences matter:

```javascript
{active: true}       // Boolean
{active: "true"}     // String
{level: 2}           // Number
{level: "2"}         // String
```

Use `mongosh` to inspect the actual BSON types:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.learners.aggregate([
      {$project: {_id: 0, email: 1, activeType: {$type: "$active"}, levelType: {$type: "$level"}}}
    ]).forEach(printjson)'
```

### An Update Appears to Lose Fields

mongo-express edits the displayed document representation. If a field is removed from the editor and the document is saved, that field can be removed from the stored document.

Actions:

1. Stop further editing.
2. Record the document `_id` and current content.
3. Compare with the source event, approved record, backup, or application system of record.
4. Repair only with authorization and a documented source of truth.
5. Verify required fields after repair.

For controlled partial updates, prefer a reviewed `mongosh` command using `$set`, `$unset`, `$inc`, or `$addToSet` because it states exactly which fields change.

### A Query Is Slow

Do not create an index based only on elapsed time in the browser.

1. Record the exact query and result count.
2. Run `explain("executionStats")`.
3. Check the winning plan, documents examined, keys examined, and documents returned.
4. Review existing indexes.
5. Treat a new index as a controlled change with cost, validation, and rollback.

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.find({email: "ada@example.com"}).explain("executionStats"));
    printjson(db.learners.getIndexes());'
```

Evidence of inefficient work is typically `COLLSCAN` plus a high examined-to-returned ratio. Evidence of an index-supported query includes `IXSCAN` and fewer examined documents.

### A Document Was Deleted Accidentally

1. Stop additional edits or bulk actions.
2. Record the database, collection, `_id`, operator, time, and filter.
3. Preserve UI and MongoDB logs.
4. Identify the approved source of truth.
5. Determine whether recovery comes from a backup, Kafka replay, application source, or auditable manual repair.
6. Obtain authorization before restoration or replay.
7. Verify counts and business fields after recovery.

The local UI does not provide undo, point-in-time recovery, or an administrative audit trail.

## 15. Symptom-to-Evidence Matrix

| Symptom | First evidence | Likely layer | First response |
| --- | --- | --- | --- |
| Browser cannot connect | `curl /status`, Compose `ps` | UI process or host port | Inspect mongo-express state and logs |
| Home page returns `401` | Authenticated and unauthenticated curl results | Web authentication | Use or correct configured web credentials |
| UI loads but databases fail | UI logs, MongoDB health, container DNS/TCP | UI-to-MongoDB connectivity | Verify service hostname and MongoDB health |
| Insert/update fails | Browser error, UI logs, document syntax, indexes | Data operation or MongoDB | Preserve input; classify syntax/type/duplicate/health |
| Filter returns nothing | DB/collection, field, value, selected type | Query or data | Inspect actual document and BSON types |
| Query is slow | `explain("executionStats")`, indexes | Query/index/workload | Measure plan before proposing index |
| Counts or fields differ | `countDocuments`, field-level comparison | Data correctness | Identify source of truth and approved repair |
| Delete was too broad | Operation/filter/time, counts, logs | Administrative action | Stop changes; escalate for restore/replay |

## 16. Safe Administrative Practices

- Use a dedicated test database for demonstrations.
- Confirm database, collection, filter, and result count before edits or deletes.
- Record the `_id` and business key before changing a document.
- Avoid **Delete all N documents retrieved** for routine administration.
- Do not use **Compact**, **Reindex**, rename, import, or collection delete as casual troubleshooting actions.
- Capture evidence before restarting a service.
- Restart only the unhealthy layer.
- Verify UI results independently with `mongosh`.
- Treat indexes and schema changes as controlled production changes.
- Do not paste resolved credentials or sensitive document contents into tickets.
- Keep ports `8081` and `27017` bound to `127.0.0.1` in this workshop.
- Use MongoDB authentication, TLS, least-privilege roles, protected networks, backups, auditing, and a supported management platform in production.

## 17. Practice Activity

Using only `mongodb_express_guide.practice_courses`:

1. Create the `practice_courses` collection.
2. Insert three documents with `title`, `durationHours`, `active`, and `topics` fields.
3. Use a Simple filter to find one course by title.
4. Use an Advanced query to find active courses lasting at least four hours.
5. Use a projection to return only title and duration.
6. Edit one course and add a topic.
7. Create an ascending index on `title`.
8. Verify the plan for a title lookup using `mongosh`.
9. Delete one document only after filtering it by an exact title.
10. Produce a short evidence report containing commands, UI observations, result counts, index evidence, and final verification.

## 18. Exercises

Complete these exercises only in `mongodb_express_guide`. Each exercise uses a separate collection so its documents, indexes, and cleanup actions remain isolated. The small data sets make the plan changes easy to inspect, but elapsed time is not meaningful evidence of performance. Compare the winning plan, `totalDocsExamined`, `totalKeysExamined`, and `nReturned` instead.

### Exercise 1: Prioritize an Adjuster's Claims Work Queue

An adjuster dashboard repeatedly requests open claims in priority order and, within the same priority, oldest report first. The collection also needs to prevent two claims from using the same claim number.

#### Create the Collection and Insert Claims

1. Open `mongodb_express_guide` in mongo-express.
2. In **Create collection**, enter `exercise_claim_work_queue` and select **Create collection**.
3. Open the new collection and select **New Document**.
4. Insert each of these documents separately:

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-CLAIMS-01",
     claimNumber: "CLM-26001",
     status: "OPEN",
     priority: 3,
     reportedAt: ISODate("2026-08-25T01:00:00Z"),
     insured: {customerId: "CUS-1001", name: "Maya Cruz"},
     loss: {type: "collision", state: "CA"}
   }
   ```

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-CLAIMS-01",
     claimNumber: "CLM-26002",
     status: "OPEN",
     priority: 3,
     reportedAt: ISODate("2026-08-24T09:30:00Z"),
     insured: {customerId: "CUS-1002", name: "Luis Reyes"},
     loss: {type: "theft", state: "CA"}
   }
   ```

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-CLAIMS-01",
     claimNumber: "CLM-26003",
     status: "CLOSED",
     priority: 1,
     reportedAt: ISODate("2026-08-20T03:15:00Z"),
     insured: {customerId: "CUS-1003", name: "Noah Tan"},
     loss: {type: "water", state: "NV"}
   }
   ```

5. On the **Advanced** filter tab, enter `{"status": "OPEN"}` and select **Find**. Confirm that `CLM-26001` and `CLM-26002` are returned.

#### Capture the Plan Before Adding Indexes

Run the exact dashboard query with execution statistics:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const plan = db.exercise_claim_work_queue
      .find({status: "OPEN"})
      .sort({priority: -1, reportedAt: 1})
      .explain("executionStats");
    printjson(plan);'
```

Before any user-created index exists, the winning plan should contain `COLLSCAN` and a blocking `SORT`. Record `nReturned`, `totalDocsExamined`, and `totalKeysExamined`.

#### Create the Business-Key and Work-Queue Indexes

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print(db.exercise_claim_work_queue.createIndex(
      {claimNumber: 1},
      {name: "uq_claim_number", unique: true}
    ));
    print(db.exercise_claim_work_queue.createIndex(
      {status: 1, priority: -1, reportedAt: 1},
      {name: "claim_work_queue"}
    ));
    printjson(db.exercise_claim_work_queue.getIndexes());'
```

`uq_claim_number` enforces the insurance business rule that a claim number identifies only one claim. `claim_work_queue` places the equality field first and the two requested sort fields next, in their requested directions. This lets MongoDB read the open portion of the index in dashboard order instead of sorting fetched claims in memory.

Re-run the earlier `explain("executionStats")`. The winning plan should now contain `IXSCAN` using `claim_work_queue`, should not contain a blocking `SORT`, and should examine only the index keys and documents needed for the two open claims. The returned claim order must remain `CLM-26002`, then `CLM-26001` because both have the same priority and `CLM-26002` was reported first.

### Exercise 2: Find Policies Approaching Renewal

A renewal team requests active policies for one carrier and risk state within a date window. A separate unique index protects policy identity.

#### Create the Collection and Insert Policies

1. In `mongodb_express_guide`, create `exercise_policy_renewals` and open it.
2. Use **New Document** to insert each document:

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-RENEWALS-02",
     policyNumber: "POL-CA-1001",
     carrierId: "CAR-01",
     status: "ACTIVE",
     renewalDate: ISODate("2026-09-05T00:00:00Z"),
     holder: {customerId: "CUS-2001", name: "Ava Garcia"},
     risk: {state: "CA", line: "AUTO"}
   }
   ```

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-RENEWALS-02",
     policyNumber: "POL-CA-1002",
     carrierId: "CAR-01",
     status: "ACTIVE",
     renewalDate: ISODate("2026-09-18T00:00:00Z"),
     holder: {customerId: "CUS-2002", name: "Eli Ramos"},
     risk: {state: "CA", line: "HOME"}
   }
   ```

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-RENEWALS-02",
     policyNumber: "POL-NV-1003",
     carrierId: "CAR-01",
     status: "ACTIVE",
     renewalDate: ISODate("2026-09-12T00:00:00Z"),
     holder: {customerId: "CUS-2003", name: "Zoe Lim"},
     risk: {state: "NV", line: "AUTO"}
   }
   ```

3. On the **Simple** tab, query `policyNumber` as a String with value `POL-CA-1001`. Confirm exactly one record is returned.

#### Compare the Unindexed and Indexed Plans

Capture the baseline plan:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.exercise_policy_renewals.find({
      carrierId: "CAR-01",
      "risk.state": "CA",
      status: "ACTIVE",
      renewalDate: {
        $gte: ISODate("2026-09-01T00:00:00Z"),
        $lt: ISODate("2026-10-01T00:00:00Z")
      }
    }).sort({renewalDate: 1}).explain("executionStats"));'
```

Confirm that the initial winning plan contains `COLLSCAN`, then create both required indexes:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print(db.exercise_policy_renewals.createIndex(
      {policyNumber: 1},
      {name: "uq_policy_number", unique: true}
    ));
    print(db.exercise_policy_renewals.createIndex(
      {carrierId: 1, "risk.state": 1, status: 1, renewalDate: 1},
      {name: "renewal_work_queue"}
    ));
    printjson(db.exercise_policy_renewals.getIndexes());'
```

The unique index prevents duplicate policy identities. In `renewal_work_queue`, exact-match fields precede the renewal-date range. The date is also the sort field, so MongoDB can scan the matching date interval in renewal order. This pattern supports timely notices without indexing every holder or risk attribute.

Re-run the baseline explain. Look for `IXSCAN` using `renewal_work_queue`, confirm the query returns the two California policies in renewal-date order, and compare examined keys and documents with the baseline.

### Exercise 3: Review Pending Provider Payments

A claims-payment team reviews pending payments for one medical provider, newest submission first. The provider identifier is nested because provider details are managed as one embedded business object.

#### Create the Collection and Insert Payments

1. In `mongodb_express_guide`, create `exercise_provider_payments` and open it.
2. Insert the following documents with **New Document**:

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-PAYMENTS-03",
     paymentReference: "PAY-9001",
     claimNumber: "CLM-26010",
     status: "PENDING_REVIEW",
     submittedAt: ISODate("2026-08-27T02:00:00Z"),
     provider: {npi: "1234567890", name: "Central Care Clinic"},
     amount: NumberDecimal("8400.00")
   }
   ```

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-PAYMENTS-03",
     paymentReference: "PAY-9002",
     claimNumber: "CLM-26011",
     status: "PENDING_REVIEW",
     submittedAt: ISODate("2026-08-27T05:30:00Z"),
     provider: {npi: "1234567890", name: "Central Care Clinic"},
     amount: NumberDecimal("12650.00")
   }
   ```

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "IDX-PAYMENTS-03",
     paymentReference: "PAY-9003",
     claimNumber: "CLM-26012",
     status: "APPROVED",
     submittedAt: ISODate("2026-08-26T04:10:00Z"),
     provider: {npi: "5555555555", name: "North Diagnostic Center"},
     amount: NumberDecimal("2100.00")
   }
   ```

3. On the **Advanced** tab, query `{"provider.npi": "1234567890", "status": "PENDING_REVIEW"}`. Confirm two payments are returned.

Capture the unindexed payment-queue plan:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.exercise_provider_payments
      .find({"provider.npi": "1234567890", status: "PENDING_REVIEW"})
      .sort({submittedAt: -1})
      .explain("executionStats"));'
```

The initial plan should contain `COLLSCAN` and `SORT`. Create the integrity and operations indexes:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print(db.exercise_provider_payments.createIndex(
      {paymentReference: 1},
      {name: "uq_payment_reference", unique: true}
    ));
    print(db.exercise_provider_payments.createIndex(
      {"provider.npi": 1, status: 1, submittedAt: -1},
      {name: "provider_payment_review"}
    ));
    printjson(db.exercise_provider_payments.getIndexes());'
```

`uq_payment_reference` prevents duplicate payment instructions. `provider_payment_review` uses the provider and workflow status as equality prefixes and maintains the required newest-first order. This supports adjuster review and provider-level fraud investigation without scanning unrelated providers or approved payments.

Re-run the explain. Confirm `IXSCAN` uses `provider_payment_review`, no blocking `SORT` remains, and `PAY-9002` is returned before `PAY-9001`.

### Monitor and Debug the Exercise Indexes Daily

Run each exercise query normally at least once after creating its indexes; remove `.explain("executionStats")` from the demonstrated expression and iterate or call `.toArray()` on the cursor. Explain operations alone may not increment the usage counter. Then collect index definitions, access counters, and storage statistics:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const names = [
      "exercise_claim_work_queue",
      "exercise_policy_renewals",
      "exercise_provider_payments"
    ];
    for (const name of names) {
      const collection = db.getCollection(name);
      print(`\n=== ${name} ===`);
      printjson(collection.getIndexes());
      collection.aggregate([{$indexStats: {}}]).forEach(printjson);
      const stats = collection.stats({scale: 1});
      printjson({
        documents: stats.count,
        storageBytes: stats.storageSize,
        totalIndexBytes: stats.totalIndexSize,
        indexBytes: stats.indexSizes
      });
    }'
```

Use this daily review procedure:

1. Record the exact slow or incorrect query, expected count, actual count, and observation time.
2. Run the query without changing it and capture `explain("executionStats")`.
3. Check the winning stage, index name, `nReturned`, `totalDocsExamined`, `totalKeysExamined`, and any blocking `SORT`.
4. Compare `getIndexes()` with the application query patterns and review `$indexStats` over a representative workload window.
5. Track collection storage and total index storage for unexpected growth.
6. Inspect BSON types and document shape before assuming that a missing result is an index problem.
7. Record any proposed index or data change, its expected benefit, verification, and rollback command.

`$indexStats.accesses.ops` is a usage counter, not proof that an index is still required or safe to remove. Its values reset when the MongoDB process restarts. Never drop an index solely because it reports zero operations during a short observation window; first review production query history, uniqueness requirements, application owners, and an approved rollback plan.

### Exercise 4: Repair an Incompatible Array of Covered Drivers

A policy search uses `$elemMatch` to find an active covered driver by license number. One migrated policy stores `coveredDrivers` as an array of strings instead of an array of driver objects, so the search misses an important covered person.

#### Create the Collection and Reproduce the Miss

1. In `mongodb_express_guide`, create `exercise_policy_drivers` and open it.
2. Insert the correctly shaped policy:

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "DATA-DRIVERS-04",
     policyNumber: "POL-DRV-4001",
     coveredDrivers: [
       {licenseNumber: "D10001", name: "Ana Flores", status: "ACTIVE"},
       {licenseNumber: "D10002", name: "Sam Lee", status: "EXCLUDED"}
     ]
   }
   ```

3. Insert the incompatible migrated policy:

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "DATA-DRIVERS-04",
     policyNumber: "POL-DRV-4002",
     coveredDrivers: ["D20001", "D20002"]
   }
   ```

4. On the **Advanced** tab, run:

   ```json
   {"coveredDrivers": {"$elemMatch": {"licenseNumber": "D20001", "status": "ACTIVE"}}}
   ```

The query returns no records even though the migration source says `D20001` is covered by `POL-DRV-4002`. Do not broaden the production query to accept every historical shape; first prove and correct the incompatible data.

Inspect the array and its element types:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.exercise_policy_drivers.aggregate([
      {$project: {
        _id: 0,
        policyNumber: 1,
        coveredDriversType: {$type: "$coveredDrivers"},
        isArray: {$isArray: "$coveredDrivers"},
        elementTypes: {
          $map: {input: "$coveredDrivers", as: "driver", in: {$type: "$$driver"}}
        }
      }}
    ]).forEach(printjson);'
```

The broken policy reports an array whose element types are `string`; the valid policy reports `object` elements.

#### Back Up, Repair, and Verify the Policy

Before editing, copy the affected document into a repair backup collection and verify the copy:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const source = db.exercise_policy_drivers.findOne({policyNumber: "POL-DRV-4002"});
    if (!source) throw new Error("POL-DRV-4002 was not found");
    db.exercise_data_repair_backup.replaceOne(
      {sourceCollection: "exercise_policy_drivers", sourceId: source._id},
      {sourceCollection: "exercise_policy_drivers", sourceId: source._id, backedUpAt: new Date(), document: source},
      {upsert: true}
    );
    printjson(db.exercise_data_repair_backup.findOne({
      sourceCollection: "exercise_policy_drivers",
      sourceId: source._id
    }));'
```

After checking the approved policy-administration source, apply only the verified replacement values:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const result = db.exercise_policy_drivers.updateOne(
      {
        policyNumber: "POL-DRV-4002",
        coveredDrivers: {$type: "array"},
        "coveredDrivers.0": {$type: "string"}
      },
      {$set: {coveredDrivers: [
        {licenseNumber: "D20001", name: "Rina Patel", status: "ACTIVE"},
        {licenseNumber: "D20002", name: "Omar Diaz", status: "ACTIVE"}
      ]}}
    );
    printjson(result);
    printjson(db.exercise_policy_drivers.findOne({
      coveredDrivers: {$elemMatch: {licenseNumber: "D20001", status: "ACTIVE"}}
    }));'
```

Expected evidence is `matchedCount: 1`, `modifiedCount: 1`, and the repaired `POL-DRV-4002` result. If `matchedCount` is zero, stop and investigate rather than issuing a broader update. The names and statuses in a real repair must come from an authorized system of record, not from inference based on the license strings.

### Exercise 5: Repair Types in Nested Claim-Reserve Objects

A severity report finds claims whose indemnity reserve is at least `10000.00` and effective during August 2026. One migrated claim contains the right visible values, but stores both the reserve amount and date as strings inside a nested array of objects.

#### Create the Collection and Reproduce the Miss

1. In `mongodb_express_guide`, create `exercise_claim_reserves` and open it.
2. Insert the correctly typed claim:

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "DATA-RESERVES-05",
     claimNumber: "CLM-RSV-5001",
     financials: {
       currency: "USD",
       reserves: [
         {category: "INDEMNITY", amount: NumberDecimal("15000.00"), effectiveAt: ISODate("2026-08-10T00:00:00Z")},
         {category: "EXPENSE", amount: NumberDecimal("2500.00"), effectiveAt: ISODate("2026-08-10T00:00:00Z")}
       ]
     }
   }
   ```

3. Insert the incompatible migrated claim:

   ```javascript
   {
     _id: ObjectId(),
     exerciseId: "DATA-RESERVES-05",
     claimNumber: "CLM-RSV-5002",
     financials: {
       currency: "USD",
       reserves: [
         {category: "INDEMNITY", amount: "12500.00", effectiveAt: "2026-08-15T00:00:00Z"},
         {category: "EXPENSE", amount: NumberDecimal("1800.00"), effectiveAt: ISODate("2026-08-15T00:00:00Z")}
       ]
     }
   }
   ```

4. Run the typed query with `mongosh`:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.exercise_claim_reserves.find({
      "financials.reserves": {$elemMatch: {
        category: "INDEMNITY",
        amount: {$gte: NumberDecimal("10000.00")},
        effectiveAt: {
          $gte: ISODate("2026-08-01T00:00:00Z"),
          $lt: ISODate("2026-09-01T00:00:00Z")
        }
      }}
    }, {_id: 0, claimNumber: 1}).forEach(printjson);'
```

Only `CLM-RSV-5001` is returned. MongoDB comparisons are type-sensitive; a value that looks like a date or decimal in the UI is not compatible with a query that uses BSON `Date` and `Decimal128` values if it is stored as a string.

Inspect every reserve element rather than relying on its displayed text:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.exercise_claim_reserves.aggregate([
      {$unwind: "$financials.reserves"},
      {$project: {
        _id: 0,
        claimNumber: 1,
        category: "$financials.reserves.category",
        amount: "$financials.reserves.amount",
        amountType: {$type: "$financials.reserves.amount"},
        effectiveAt: "$financials.reserves.effectiveAt",
        effectiveAtType: {$type: "$financials.reserves.effectiveAt"}
      }}
    ]).forEach(printjson);'
```

#### Back Up, Repair, and Verify the Nested Element

Back up the affected claim and verify the copy:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const source = db.exercise_claim_reserves.findOne({claimNumber: "CLM-RSV-5002"});
    if (!source) throw new Error("CLM-RSV-5002 was not found");
    db.exercise_data_repair_backup.replaceOne(
      {sourceCollection: "exercise_claim_reserves", sourceId: source._id},
      {sourceCollection: "exercise_claim_reserves", sourceId: source._id, backedUpAt: new Date(), document: source},
      {upsert: true}
    );
    printjson(db.exercise_data_repair_backup.findOne({
      sourceCollection: "exercise_claim_reserves",
      sourceId: source._id
    }));'
```

Then apply a guarded, element-level repair:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const result = db.exercise_claim_reserves.updateOne(
      {claimNumber: "CLM-RSV-5002"},
      {$set: {
        "financials.reserves.$[reserve].amount": NumberDecimal("12500.00"),
        "financials.reserves.$[reserve].effectiveAt": ISODate("2026-08-15T00:00:00Z")
      }},
      {arrayFilters: [{
        "reserve.category": "INDEMNITY",
        "reserve.amount": {$type: "string"},
        "reserve.effectiveAt": {$type: "string"}
      }]}
    );
    printjson(result);'
```

Expected evidence is `matchedCount: 1` and `modifiedCount: 1`. Re-run both the typed query and type-inspection aggregation. Both claims should now be returned, while `CLM-RSV-5002` should report `decimal` for the indemnity amount and `date` for its effective date. The expense reserve must remain unchanged.

### Daily Data Debugging and Safe Exercise Cleanup

Search for incompatible exercise data before changing it:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson({
      malformedDriverPolicies: db.exercise_policy_drivers.countDocuments({
        "coveredDrivers.0": {$type: "string"}
      }),
      stringReserveValues: db.exercise_claim_reserves.countDocuments({
        "financials.reserves": {$elemMatch: {
          $or: [
            {amount: {$type: "string"}},
            {effectiveAt: {$type: "string"}}
          ]
        }}
      })
    });'
```

For daily debugging, record the business identifier and current document, compare it with the approved source, inspect nested field types, back up the exact document, use a guarded `updateOne`, and verify the business query plus unaffected fields. Never repair every document merely because one example has the wrong shape.

To remove only the records created by one exercise, first count the exact marker, then delete using the same filter and verify zero remain:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const filter = {exerciseId: "IDX-CLAIMS-01"};
    const before = db.exercise_claim_work_queue.countDocuments(filter);
    printjson({collection: "exercise_claim_work_queue", filter, before});
    if (before !== 3) throw new Error(`Expected 3 exercise records; found ${before}. Nothing deleted.`);
    printjson(db.exercise_claim_work_queue.deleteMany(filter));
    printjson({remaining: db.exercise_claim_work_queue.countDocuments(filter)});'
```

This cleanup leaves the collection and its indexes in place. To remove a known exercise index after an approved review, capture `getIndexes()` and the query plan first, then target its exact name, for example `db.exercise_claim_work_queue.dropIndex("claim_work_queue")`. Do not use a wildcard, drop `_id_`, or treat index deletion as routine housekeeping.

## 19. Slow Query Management

These exercises demonstrate how a query that scans many documents can become more efficient after a matching index is added. They are deliberately isolated from the earlier exercises and use collections whose names begin with `slow_query_`.

mongo-express does not display a MongoDB query plan, `executionStats`, or server-only execution time. The browser measurements below include the mongo-express request, MongoDB work, network transfer, document counting, and page rendering. Use them as approximate workshop observations, not as production proof or a promised speedup. Production validation still requires `explain("executionStats")`, profiler or slow-query evidence, and representative workload monitoring.

### Import the Exercise Data with mongo-express

The repository contains one pre-generated Extended JSON file for each exercise. Each file contains a JSON array of 50,000 deterministic documents. Dates and decimal values use Extended JSON so mongo-express imports them as their intended BSON types.

| Exercise collection | Import file |
| --- | --- |
| `slow_query_claim_lookup` | [`mongodb/mongo-express-imports/slow_query_claim_lookup.json`](mongodb/mongo-express-imports/slow_query_claim_lookup.json) |
| `slow_query_claim_queue` | [`mongodb/mongo-express-imports/slow_query_claim_queue.json`](mongodb/mongo-express-imports/slow_query_claim_queue.json) |
| `slow_query_policy_renewals` | [`mongodb/mongo-express-imports/slow_query_policy_renewals.json`](mongodb/mongo-express-imports/slow_query_policy_renewals.json) |
| `slow_query_provider_payments` | [`mongodb/mongo-express-imports/slow_query_provider_payments.json`](mongodb/mongo-express-imports/slow_query_provider_payments.json) |
| `slow_query_investigation_tags` | [`mongodb/mongo-express-imports/slow_query_investigation_tags.json`](mongodb/mongo-express-imports/slow_query_investigation_tags.json) |

Prepare one exercise collection at a time:

1. Open `mongodb_express_guide` in mongo-express and verify the database name at the top of the page.
2. If the exercise collection already exists, select **Del** only beside its exact name, type that collection name in the confirmation dialog, and confirm. This removes earlier documents and exercise indexes so the new run has a valid unindexed baseline.
3. In **Create collection**, enter the exact collection name from the table and select **Create collection**.
4. Return to the `mongodb_express_guide` database page. Locate the new collection's row and select **Import**.
5. In the file picker, open this repository, browse to `mongodb/mongo-express-imports`, and select the matching `.json` file.
6. Keep the page open while the file uploads. A successful import displays an alert containing `50000 document(s) inserted`.
7. Select **View** for the collection. Confirm **Documents** is `50000`, **Indexes** is `1`, and the **Indexes** table contains only `_id_`.

> [!IMPORTANT]
> Import appends documents; it does not replace the collection. Do not upload the same file twice. If the count is not exactly 50,000 or a user-created index already exists, delete and recreate only that exercise collection before continuing. Never perform these reset steps in `workshop` or another database.

### Measure Before and After the Index

Use the same measurement procedure for all five exercises:

1. Open the exercise collection in mongo-express and scroll to **Indexes**. Confirm that only `_id_` exists, then record **Indexes** and **Total index size** from **Collection Statistics**.
2. Open the browser developer tools and select **Network**.
3. Enable **Disable cache** while the developer tools remain open. Select the **Doc** request type if the browser offers that filter.
4. Enter the stated query in mongo-express. Perform any stated sort steps, then select **Find** once as a warm-up.
5. Select **Find** five more times. For each run, select the document request whose URL contains `/db/mongodb_express_guide/<collection-name>/`, open **Timing**, and record its total duration.
6. Use the middle value of the five ordered durations as the median. Do not compare the fastest unindexed request with the slowest indexed request.
7. Complete the exercise's **After: Create the Index and Compare** steps. Select **New Index**, replace the editor content with the specified index document, and select **Save**.
8. Refresh the collection page. Confirm the generated index name, index count, and total index size.
9. Repeat the identical query, sort, warm-up, and five timed requests. The returned count and ordering must remain unchanged.

Record the evidence for each exercise:

| Measurement | Before index | After index |
| --- | ---: | ---: |
| Matching documents |  |  |
| Median browser request time |  |  |
| Index count |  |  |
| Total index size |  |  |
| Relevant index name | `_id_` only |  |

Timing can vary because of CPU load, caches, storage, and browser rendering. If the indexed median is not lower, repeat the complete five-request samples and report the result honestly. The invariant is that the query results remain correct and that the intended index exists; mongo-express alone cannot prove which plan MongoDB selected.

### Slow Query Exercise 1: Find One Claim by Claim Number

This support lookup should return one claim, but without an index MongoDB must inspect the collection to locate it.

#### Populate in mongo-express

Create `slow_query_claim_lookup` and import [`slow_query_claim_lookup.json`](mongodb/mongo-express-imports/slow_query_claim_lookup.json) using the earlier import procedure. Verify 50,000 documents and only `_id_` before measuring.

#### Before: Query Without the Index

In the **Simple** tab, enter:

| Control | Value |
| --- | --- |
| Key | `claimNumber` |
| Value | `CLM-049999` |
| Type | `String` |

The query must return exactly one document. Complete the warm-up and five-request timing sample, then record the **Before index** column in the evidence table.

#### After: Create the Index and Compare

Select **New Index** and create:

```json
{"claimNumber": 1}
```

The generated name is `claimNumber_1`. Confirm the index count is now two and record the new total index size. Repeat the identical query and timing sample, complete the **After index** column, and confirm exactly one document still matches. Explain why an exact lookup benefits from an index whose first key is `claimNumber`.

### Slow Query Exercise 2: Sort an Open-Claims Work Queue

An adjuster needs open claims ordered by highest priority first and, within a priority, oldest report first. The index must support both the equality filter and the requested order.

#### Populate in mongo-express

Create `slow_query_claim_queue` and import [`slow_query_claim_queue.json`](mongodb/mongo-express-imports/slow_query_claim_queue.json). Verify 50,000 documents and only `_id_`.

#### Before: Filter and Sort Without the Index

On the **Advanced** tab, enter:

```json
{"status": "OPEN"}
```

Select **Find**, select the `priority` heading twice so it shows descending order, and then select `reportedAt` once so it shows ascending order. Confirm that both sort indicators remain visible and 10,000 claims match. Use this filtered and sorted request for the warm-up and five-request **Before index** timing sample.

#### After: Create the Compound Index and Compare

Select **New Index** and create:

```json
{"status": 1, "priority": -1, "reportedAt": 1}
```

The generated name is `status_1_priority_-1_reportedAt_1`. Confirm the index count is two and record the new total index size. Repeat the same filter, sort, warm-up, and five-request sample for the **After index** column. Confirm that 10,000 documents still match and that the displayed claims remain in descending priority and ascending report-time order. The equality field comes first, followed by the two sort fields in their requested directions.

### Slow Query Exercise 3: Find Policies in a Renewal Window

The renewal team searches active policies for one carrier and risk state during a date window. This demonstrates a compound index with equality fields before a range field.

#### Populate in mongo-express

Create `slow_query_policy_renewals` and import [`slow_query_policy_renewals.json`](mongodb/mongo-express-imports/slow_query_policy_renewals.json). Verify 50,000 documents and only `_id_`.

#### Before: Query the Date Range Without the Index

On the **Advanced** tab, enter:

```javascript
{
  "carrierId": "CAR-02",
  "risk.state": "CA",
  "status": "ACTIVE",
  "renewalDate": {
    "$gte": ISODate("2026-09-01T00:00:00Z"),
    "$lt": ISODate("2026-10-01T00:00:00Z")
  }
}
```

Confirm 206 policies match. Complete the warm-up and five-request sample and record the **Before index** evidence.

#### After: Create the Equality-and-Range Index

Select **New Index** and create:

```json
{"carrierId": 1, "risk.state": 1, "status": 1, "renewalDate": 1}
```

The generated name is `carrierId_1_risk.state_1_status_1_renewalDate_1`. Confirm two indexes and record the new total index size. Repeat the exact query, warm-up, and five timed requests for the **After index** evidence. Confirm the count remains 206. The carrier, state, and status equality keys narrow the index scan before MongoDB evaluates the renewal-date interval.

### Slow Query Exercise 4: Review One Provider's Pending Payments

The payment team repeatedly searches a nested provider identifier and workflow status. This demonstrates indexing a nested field as part of a compound key.

#### Populate in mongo-express

Create `slow_query_provider_payments` and import [`slow_query_provider_payments.json`](mongodb/mongo-express-imports/slow_query_provider_payments.json). Verify 50,000 documents and only `_id_`.

#### Before: Query the Nested Field Without the Index

In **Advanced** query mode, enter:

```json
{"provider.npi": "1000001999", "status": "PENDING_REVIEW"}
```

Confirm eight payments match. Complete the warm-up and five-request sample and record the **Before index** evidence.

#### After: Create the Nested-Field Index and Compare

Select **New Index** and create:

```json
{"provider.npi": 1, "status": 1}
```

The generated name is `provider.npi_1_status_1`. Confirm two indexes and record the new total index size. Repeat the exact query, warm-up, and five-request sample for the **After index** evidence. Confirm the same eight payments match. Explain why indexing `provider.name` would not solve a query whose predicate uses `provider.npi`.

### Slow Query Exercise 5: Find Claims with a Rare Investigation Tag

Claims may have several investigation tags. MongoDB automatically makes an index on an array field multikey, allowing it to locate documents containing one array value.

#### Populate in mongo-express

Create `slow_query_investigation_tags` and import [`slow_query_investigation_tags.json`](mongodb/mongo-express-imports/slow_query_investigation_tags.json). Verify 50,000 documents and only `_id_`.

#### Before: Query the Array Without the Index

On the **Simple** tab, enter:

| Control | Value |
| --- | --- |
| Key | `investigationTags` |
| Value | `catastrophe-watch` |
| Type | `String` |

Confirm 13 claims match. Complete the warm-up and five-request sample and record the **Before index** evidence.

#### After: Create the Multikey Index and Compare

Select **New Index** and create:

```json
{"investigationTags": 1}
```

The generated name is `investigationTags_1`. Confirm two indexes and record the new total index size. Because `investigationTags` contains arrays, MongoDB manages this as a multikey index even though the mongo-express **Attributes** column may not label it as multikey. Repeat the identical query, warm-up, and five-request sample for the **After index** evidence, and confirm the same 13 documents match.

### Interpret, Roll Back, and Clean Up Safely

For each exercise, explain the improvement in terms of the query shape, not only the browser duration. Also record the additional index storage and note that inserts, deletes, and updates to indexed fields now require index maintenance.

If an exercise index must be rolled back, use **DEL** only beside its exact generated name in the collection's **Indexes** table:

| Collection | Exercise index |
| --- | --- |
| `slow_query_claim_lookup` | `claimNumber_1` |
| `slow_query_claim_queue` | `status_1_priority_-1_reportedAt_1` |
| `slow_query_policy_renewals` | `carrierId_1_risk.state_1_status_1_renewalDate_1` |
| `slow_query_provider_payments` | `provider.npi_1_status_1` |
| `slow_query_investigation_tags` | `investigationTags_1` |

Never delete `_id_`. After rollback, repeat the same query and capture a fresh measurement rather than assuming the earlier baseline still applies.

The database cleanup in the next section removes all five collections together with the rest of the isolated guide database. Do not delete similarly named collections from `workshop` or another database.

## 20. Clean Up Only the Guide Database

First verify the target independently:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson({database: db.getName(), collections: db.getCollectionNames()})'
```

In mongo-express:

1. Return to the home page.
2. Find `mongodb_express_guide`.
3. Select **Del** for that database.
4. Type the exact database name when prompted.
5. Confirm deletion.

Verify that only the guide database was removed:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.adminCommand({listDatabases: 1, nameOnly: true}).databases)'
```

The `workshop` database and its collections must remain unchanged.

## 21. Stop the Local Environment

Stop MongoDB and mongo-express without deleting their persistent MongoDB volume:

```bash
docker compose -f mongodb/docker-compose.yml down
```

Do not add `-v` unless deletion of the named MongoDB data and backup volumes is explicitly intended.
