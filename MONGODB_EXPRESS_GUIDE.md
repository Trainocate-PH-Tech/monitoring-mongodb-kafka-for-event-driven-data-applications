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

## 18. Clean Up Only the Guide Database

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

## 19. Stop the Local Environment

Stop MongoDB and mongo-express without deleting their persistent MongoDB volume:

```bash
docker compose -f mongodb/docker-compose.yml down
```

Do not add `-v` unless deletion of the named MongoDB data and backup volumes is explicitly intended.
