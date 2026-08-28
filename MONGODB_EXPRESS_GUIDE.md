# MongoDB Administration with mongo-express

This guide shows how to perform simple MongoDB operations through the local mongo-express web application and how to troubleshoot those operations as an administrator.

The examples use an isolated database named `mongodb_express_guide` and a collection named `learners`. Do not perform the create, edit, or delete exercises in the course's `workshop` database.

This guide uses mongo-express as the primary workflow. Each database task also includes a collapsed Compose/`mongosh` equivalent for reference and comparison; the command-line blocks are optional unless an exercise explicitly says otherwise. For additional MongoDB concepts, see [MONGODB_PRIMER.md](MONGODB_PRIMER.md).

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

It also cannot display `explain("executionStats")`, replica-set member state, index usage counters, or atomic partial-update results. Those operations have no faithful mongo-express equivalent. This guide uses UI-observable evidence instead and labels where that evidence is insufficient for production validation.

> [!IMPORTANT]
> Treat each collapsed command-line block as an alternative demonstration of the preceding UI task. Do not run both versions of a write, import, repair, delete, or cleanup step against the same exercise data unless the instructions explicitly require it; doing so can duplicate data, conflict with existing objects, or apply a change twice. Read-only verification commands are safe to compare after the UI task.

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

These Compose commands cannot be replaced by mongo-express because the web application must already be running before it can be opened. They manage container lifecycle; the database sections below present the UI first and the command-line equivalent second.

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

### Verify in mongo-express

1. Return to the `mongodb_express_guide` database page.
2. Confirm that the collection table contains exactly one `learners` row.
3. Select **View** and confirm the collection page opens and reports zero documents.
4. Return to the database page and refresh once; confirm `learners` is still listed.

If the UI reports success but the collection is absent after refresh, preserve the browser error and mongo-express logs before retrying.

<details>
<summary>Command-line equivalent (reference only)</summary>

MongoDB creates the database when its first collection is created:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.createCollection("learners");
    printjson(db.getCollectionNames());'
```

</details>

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

### Verify in mongo-express

1. Clear all filters and refresh the `learners` collection page.
2. Confirm **Documents** reports `3`.
3. Select the `name` heading until the rows are ordered Ada, Ben, Cara.
4. Inspect each displayed document and confirm the expected email, Boolean `active`, and numeric `level` values.

<details>
<summary>Command-line equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.learners.insertMany([
      {
        name: "Ada Rivera",
        email: "ada@example.com",
        active: true,
        level: 1,
        skills: ["MongoDB"],
        enrolledAt: new Date()
      },
      {
        name: "Ben Santos",
        email: "ben@example.com",
        active: true,
        level: 1,
        skills: ["MongoDB", "Kafka"]
      },
      {
        name: "Cara Lim",
        email: "cara@example.com",
        active: false,
        level: 2,
        skills: ["Operations"]
      }
    ]);
    printjson({count: db.learners.countDocuments({})});'
```

</details>

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

### Verify in mongo-express

Refresh the collection, re-enter the same Advanced query and projection, and select **Find**. Confirm the result count and projected fields match the first run. Then clear the projection, run the same query again, and verify the hidden fields are still present in the stored documents.

<details>
<summary>Command-line equivalents (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print("String filter:");
    db.learners.find({email: "ada@example.com"}).forEach(printjson);

    print("Boolean filter:");
    db.learners.find({active: true}).forEach(printjson);

    print("Advanced filter, projection, and sort:");
    db.learners.find(
      {active: true, level: {$gte: 1}},
      {_id: 0, name: 1, email: 1, level: 1}
    ).sort({name: 1}).forEach(printjson);'
```

</details>

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

### Verify in mongo-express

Run a Simple String filter for `email = ada@example.com`. Confirm exactly one document is returned and its fields include:

```javascript
{
  name: "Ada Rivera",
  active: false,
  level: 2,
  skills: [ "MongoDB", "Kafka" ]
}
```

<details>
<summary>Command-line equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.updateOne(
      {email: "ada@example.com"},
      {$set: {
        active: false,
        level: 2,
        skills: ["MongoDB", "Kafka"]
      }}
    ));
    printjson(db.learners.findOne({email: "ada@example.com"}));'
```

</details>

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

### Verify in mongo-express

Keep the exact `cara@example.com` filter active and confirm zero results. Clear the filter, select **Find**, and confirm **Documents** reports `2` and only Ada and Ben are displayed.

mongo-express does not provide an undo button or a database transaction history. Recovery requires a valid source of truth, backup, or approved replay procedure.

<details>
<summary>Command-line equivalent (reference only)</summary>

The command resolves the exact document first and deletes by `_id`:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const matches = db.learners.find({email: "cara@example.com"}).toArray();
    if (matches.length !== 1) {
      throw new Error(`Expected exactly one match; found ${matches.length}`);
    }
    printjson(db.learners.deleteOne({_id: matches[0]._id}));
    printjson({
      cara: db.learners.countDocuments({email: "cara@example.com"}),
      total: db.learners.countDocuments({})
    });'
```

</details>

## 10. Create and Inspect an Index

### Establish the Query First

The administration question is: does the collection need an index for frequent email lookups?

Open the collection page and inspect the **Indexes** table. Initially, only the automatic `_id_` index should exist. Record the index count and total index size.

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

### Verify the Index in mongo-express

1. Confirm the **Indexes** table contains `_id_` and `email_1`.
2. Record the new index count and total index size.
3. Run the exact Simple String filter `email = ada@example.com` and confirm one unchanged result.

This proves that the index exists and the query result remains correct. mongo-express cannot show whether MongoDB selected the index, so do not claim `IXSCAN`, documents examined, or a measured performance improvement from this UI evidence alone.

An index consumes storage and increases insert/update work. Create indexes for measured query needs, not merely because a field exists.

<details>
<summary>Command-line equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print(db.learners.createIndex({email: 1}));
    printjson(db.learners.getIndexes());
    printjson(db.learners.find({email: "ada@example.com"}).explain("executionStats"));'
```

</details>

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

Refresh each page once and confirm the values remain available. Record the observation time with the displayed values. These are point-in-time UI statistics; capacity administration requires repeated measurements, a growth rate, a threshold, and a forecast to that threshold.

<details>
<summary>Command-line equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.stats(1));
    printjson(db.learners.stats({scale: 1}));'
```

</details>

## 12. Administrator Debugging Method

Use the same order for every problem:

1. Record the exact operation, database, collection, filter, expected result, actual result, and time.
2. Preserve the browser error and avoid repeated clicks.
3. Check the web endpoint and authentication.
4. Check the mongo-express container and logs.
5. Check the MongoDB container health and logs.
6. Reproduce the read-only part of the operation with the same filter in mongo-express.
7. Identify whether the problem is browser/UI, web container, connectivity, MongoDB, query syntax/type, index, or data correctness.
8. Correct only the affected layer.
9. Refresh the UI and repeat the exact read-only verification.
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
```

Then collect UI evidence:

1. Sign in to mongo-express.
2. Confirm the home page lists databases and shows server information.
3. Open `mongodb_express_guide`, open `learners`, and repeat a known read-only filter.
4. Save the displayed result count, server-information values, browser error if any, and observation time.

Healthy Compose state plus a successful UI read proves the local workshop path is available for that operation. It does not expose replica-set member state or prove redundancy; mongo-express has no equivalent view for that evidence.

<details>
<summary>Command-line database-health check (reference only)</summary>

```bash
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

</details>

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
3. Confirm both containers are healthy and the home page can list databases.
4. Inspect the collection's **Indexes** table and filter for conflicting values.
5. Correct the document once and retry.
6. Query by the intended business key to ensure the first attempt did not already succeed.

To check a possible duplicate email, run the Simple String filter `email = ada@example.com`, record the matching count and `_id` values, and inspect the **Indexes** table for an email index.

<details>
<summary>Command-line equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.find({email: "ada@example.com"}).toArray());
    printjson(db.learners.getIndexes());'
```

</details>

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

Use type-specific Simple filters to test the stored values. For example, run `active = true` once as **JSON, bool** and once as **String**; only the Boolean query should match. Open a returned document in the editor and verify that Boolean and numeric values are unquoted. mongo-express cannot project `$type` results in the normal document view, so the command-line equivalent can provide stronger type evidence.

<details>
<summary>Command-line equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.learners.aggregate([
      {$project: {
        _id: 0,
        email: 1,
        activeType: {$type: "$active"},
        levelType: {$type: "$level"}
      }}
    ]).forEach(printjson);'
```

</details>

### An Update Appears to Lose Fields

mongo-express edits the displayed document representation. If a field is removed from the editor and the document is saved, that field can be removed from the stored document.

Actions:

1. Stop further editing.
2. Record the document `_id` and current content.
3. Compare with the source event, approved record, backup, or application system of record.
4. Repair only with authorization and a documented source of truth.
5. Verify required fields after repair.

mongo-express does not offer a guarded, atomic partial-update editor. If a repair requires `$set`, `$unset`, `$inc`, array filters, or a compare-and-update guard, stop the UI procedure and use an approved database-administration workflow. Do not imitate a partial update by casually replacing a production document in the browser.

<details>
<summary>Command-line partial-update pattern (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.updateOne(
      {email: "ada@example.com"},
      {$set: {level: 2}}
    ));
    printjson(db.learners.findOne({email: "ada@example.com"}));'
```

</details>

### A Query Is Slow

Do not create an index based only on elapsed time in the browser.

1. Record the exact query, result count, and current **Indexes** table.
2. Use the repeatable browser-timing procedure in Section 19 for workshop-only comparison.
3. Confirm the result count and order remain unchanged after any approved index addition.
4. Record the new index name and storage cost.

mongo-express cannot display the winning plan, documents examined, keys examined, `COLLSCAN`, or `IXSCAN`. Browser duration is end-to-end and is not production-grade proof that an index was selected.

<details>
<summary>Command-line query-plan equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.learners.find({email: "ada@example.com"}).explain("executionStats"));
    printjson(db.learners.getIndexes());'
```

</details>

### A Document Was Deleted Accidentally

1. Stop additional edits or bulk actions.
2. Record the database, collection, `_id`, operator, time, and filter.
3. Preserve UI and MongoDB logs.
4. Identify the approved source of truth.
5. Determine whether recovery comes from a backup, Kafka replay, application source, or auditable manual repair.
6. Obtain authorization before restoration or replay.
7. Verify counts and business fields after recovery.

The local UI does not provide undo, point-in-time recovery, or an administrative audit trail.

There is no safe generic command-line undo equivalent either. Restoration must use the approved backup, replay, or source-of-truth procedure for the affected data.

## 15. Symptom-to-Evidence Matrix

| Symptom | First evidence | Likely layer | First response |
| --- | --- | --- | --- |
| Browser cannot connect | `curl /status`, Compose `ps` | UI process or host port | Inspect mongo-express state and logs |
| Home page returns `401` | Authenticated and unauthenticated curl results | Web authentication | Use or correct configured web credentials |
| UI loads but databases fail | UI logs, MongoDB health, container DNS/TCP | UI-to-MongoDB connectivity | Verify service hostname and MongoDB health |
| Insert/update fails | Browser error, UI logs, document syntax, indexes | Data operation or MongoDB | Preserve input; classify syntax/type/duplicate/health |
| Filter returns nothing | DB/collection, field, value, selected type | Query or data | Inspect actual document and BSON types |
| Query is slow | Exact UI query, browser timing, **Indexes** table | Query/index/workload | Preserve results; use Section 19's comparison method |
| Counts or fields differ | UI result count and field-level comparison | Data correctness | Identify source of truth and approved repair |
| Delete was too broad | Operation/filter/time, counts, logs | Administrative action | Stop changes; escalate for restore/replay |

## 16. Safe Administrative Practices

- Use a dedicated test database for demonstrations.
- Confirm database, collection, filter, and result count before edits or deletes.
- Record the `_id` and business key before changing a document.
- Avoid **Delete all N documents retrieved** for routine administration.
- Do not use **Compact**, **Reindex**, rename, import, or collection delete as casual troubleshooting actions.
- Capture evidence before restarting a service.
- Restart only the unhealthy layer.
- Refresh and repeat the exact UI filter before and after a change.
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
8. Verify that the **Indexes** table contains `title_1`, then repeat the exact title lookup and confirm the result is unchanged.
9. Delete one document only after filtering it by an exact title.
10. Produce a short evidence report containing UI actions, observations, result counts, index evidence, and final verification.

## 18. Exercises

Complete these exercises only in `mongodb_express_guide`. Each exercise uses a separate collection so its documents, indexes, and cleanup actions remain isolated. The small data sets demonstrate query shape and index definitions, but their elapsed time is not meaningful evidence of performance. In the UI workflow, verify the index definition, returned count, and order; use the optional command-line equivalent to inspect the execution plan. Section 19 provides larger data sets for approximate browser timing.

### Exercise 1: Prioritize an Adjuster's Claims Work Queue

An adjuster dashboard repeatedly requests open claims in priority order and, within the same priority, oldest report first. A separate lookup index supports searches by claim number; uniqueness enforcement is outside this mongo-express exercise.

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

#### Capture the UI Baseline

1. Confirm the **Indexes** table contains only `_id_`.
2. Run `{"status": "OPEN"}` on the **Advanced** tab.
3. Select `priority` until it is descending, then select `reportedAt` until it is ascending. Confirm both sort indicators remain visible.
4. Record the two returned claim numbers and their order: `CLM-26002`, then `CLM-26001`.

<details>
<summary>Command-line baseline (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.exercise_claim_work_queue
      .find({status: "OPEN"})
      .sort({priority: -1, reportedAt: 1})
      .explain("executionStats"));'
```

</details>

#### Create the Lookup and Work-Queue Indexes

Use **New Index** twice, saving one definition at a time:

```json
{"claimNumber": 1}
```

```json
{"status": 1, "priority": -1, "reportedAt": 1}
```

Refresh and confirm the generated indexes `claimNumber_1` and `status_1_priority_-1_reportedAt_1` appear. The compound index places the equality field first and the requested sort fields next in their requested directions.

Repeat the identical filter and sorting steps. The result count and order must remain unchanged. This verifies correctness and index existence, but mongo-express cannot prove that the compound index was selected or that a blocking sort was avoided.

> [!NOTE]
> The mongo-express index form used in this workshop creates basic indexes and does not expose a reliable unique-index option. `claimNumber_1` therefore demonstrates lookup indexing only; it does not enforce claim-number uniqueness.

<details>
<summary>Command-line index creation and verification (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    print(db.exercise_claim_work_queue.createIndex({claimNumber: 1}));
    print(db.exercise_claim_work_queue.createIndex(
      {status: 1, priority: -1, reportedAt: 1}
    ));
    printjson(db.exercise_claim_work_queue.getIndexes());
    printjson(db.exercise_claim_work_queue
      .find({status: "OPEN"})
      .sort({priority: -1, reportedAt: 1})
      .explain("executionStats"));'
```

</details>

### Exercise 2: Find Policies Approaching Renewal

A renewal team requests active policies for one carrier and risk state within a date window. A separate lookup index supports policy-number searches; uniqueness enforcement is outside this mongo-express exercise.

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

#### Compare the UI Result Before and After Indexing

1. Confirm only `_id_` exists.
2. On the **Advanced** tab, run:

   ```javascript
   {
     "carrierId": "CAR-01",
     "risk.state": "CA",
     "status": "ACTIVE",
     "renewalDate": {
       "$gte": ISODate("2026-09-01T00:00:00Z"),
       "$lt": ISODate("2026-10-01T00:00:00Z")
     }
   }
   ```

3. Sort `renewalDate` ascending. Record the two returned policies and their order.
4. Use **New Index** twice to create `{"policyNumber": 1}` and `{"carrierId": 1, "risk.state": 1, "status": 1, "renewalDate": 1}`.
5. Refresh and confirm `policyNumber_1` and `carrierId_1_risk.state_1_status_1_renewalDate_1` appear.
6. Repeat the exact query and sort. Confirm the same policies are returned in renewal-date order.

The compound definition puts exact-match fields before the renewal-date range and sort field. The first index supports policy lookup but is not unique; mongo-express does not expose the uniqueness control needed to enforce policy identity in this workflow.

<details>
<summary>Command-line equivalent (reference only)</summary>

Run the `explain` before creating the indexes for a baseline, then run the same command again afterward:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const query = {
      carrierId: "CAR-01",
      "risk.state": "CA",
      status: "ACTIVE",
      renewalDate: {
        $gte: ISODate("2026-09-01T00:00:00Z"),
        $lt: ISODate("2026-10-01T00:00:00Z")
      }
    };
    printjson(db.exercise_policy_renewals
      .find(query).sort({renewalDate: 1}).explain("executionStats"));
    print(db.exercise_policy_renewals.createIndex({policyNumber: 1}));
    print(db.exercise_policy_renewals.createIndex(
      {carrierId: 1, "risk.state": 1, status: 1, renewalDate: 1}
    ));
    printjson(db.exercise_policy_renewals.getIndexes());
    printjson(db.exercise_policy_renewals
      .find(query).sort({renewalDate: 1}).explain("executionStats"));'
```

</details>

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

Confirm only `_id_` exists, run the stated Advanced query, and sort `submittedAt` descending. Record `PAY-9002`, then `PAY-9001`.

Use **New Index** twice to create:

```json
{"paymentReference": 1}
```

```json
{"provider.npi": 1, "status": 1, "submittedAt": -1}
```

Refresh and confirm `paymentReference_1` and `provider.npi_1_status_1_submittedAt_-1` appear. Repeat the exact query and descending sort; the same two payments must appear in the same order. The compound definition uses provider and workflow status as equality prefixes and the required newest-first field. The payment-reference index supports lookup but is not a uniqueness constraint in this UI workflow.

<details>
<summary>Command-line equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const query = {"provider.npi": "1234567890", status: "PENDING_REVIEW"};
    printjson(db.exercise_provider_payments
      .find(query).sort({submittedAt: -1}).explain("executionStats"));
    print(db.exercise_provider_payments.createIndex({paymentReference: 1}));
    print(db.exercise_provider_payments.createIndex(
      {"provider.npi": 1, status: 1, submittedAt: -1}
    ));
    printjson(db.exercise_provider_payments.getIndexes());
    printjson(db.exercise_provider_payments
      .find(query).sort({submittedAt: -1}).explain("executionStats"));'
```

</details>

### Monitor and Debug the Exercise Indexes Daily

Open each exercise collection and use this UI review procedure:

1. Record the exact slow or incorrect query, expected count, actual count, and observation time.
2. Run the query without changing it and record the returned count and order.
3. Capture the **Indexes** table, collection storage, and total index size.
4. Compare each displayed index definition with the application query pattern.
5. Track collection storage and total index storage for unexpected growth.
6. Inspect BSON types and document shape before assuming that a missing result is an index problem.
7. Record any proposed index or data change, its expected benefit, UI verification, and exact rollback target.

mongo-express does not show index access counters or query plans. Never drop an index merely because it is unfamiliar or because a short browser test shows no obvious difference; first review production query history, uniqueness requirements, application owners, and an approved rollback plan.

<details>
<summary>Command-line monitoring equivalent (reference only)</summary>

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    for (const name of [
      "exercise_claim_work_queue",
      "exercise_policy_renewals",
      "exercise_provider_payments"
    ]) {
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

</details>

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

Inspect the array shape with UI filters:

1. Run `{"coveredDrivers": {"$type": "array"}}` and confirm both policies match.
2. Run `{"coveredDrivers.0": {"$type": "string"}}` and confirm only `POL-DRV-4002` matches.
3. Run `{"coveredDrivers.0": {"$type": "object"}}` and confirm only `POL-DRV-4001` matches.
4. Open each document and visually confirm that the broken policy has string elements while the valid policy has object elements.

<details>
<summary>Command-line type inspection (reference only)</summary>

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

</details>

#### Back Up, Repair, and Verify the Policy

Before editing, make a UI-visible copy:

1. Filter `exercise_policy_drivers` for `policyNumber = POL-DRV-4002` and confirm one result.
2. Open the document, copy its complete representation, and record its `_id`.
3. Create `exercise_data_repair_backup` if it does not exist.
4. In that collection, select **New Document** and insert a backup record containing a new `_id`, `sourceCollection: "exercise_policy_drivers"`, the recorded `sourceId`, `backedUpAt: ISODate()`, and the copied source document in a `document` field.
5. Filter the backup collection by `sourceId` using the Simple filter's **ObjectId** type and the recorded hexadecimal value, then confirm one backup exists.

After checking the approved policy-administration source, filter the source collection again for the exact policy number, open that one document, preserve `_id` and every unrelated field, and replace only `coveredDrivers` with:

```javascript
[
  {licenseNumber: "D20001", name: "Rina Patel", status: "ACTIVE"},
  {licenseNumber: "D20002", name: "Omar Diaz", status: "ACTIVE"}
]
```

Save once. Re-run the original `$elemMatch` query and confirm exactly `POL-DRV-4002` is returned. Then repeat the string-element filter and confirm it returns zero results.

mongo-express replaces the displayed document and provides no compare-and-update guard or `matchedCount`. If the exact pre-edit filter does not return one document, stop. The names and statuses in a real repair must come from an authorized system of record, not from inference based on the license strings.

<details>
<summary>Command-line backup and guarded repair (reference only)</summary>

Use this as an alternative to the UI repair, not after the UI has already changed the document:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const source = db.exercise_policy_drivers.findOne({policyNumber: "POL-DRV-4002"});
    if (!source) throw new Error("POL-DRV-4002 was not found");

    db.exercise_data_repair_backup.replaceOne(
      {sourceCollection: "exercise_policy_drivers", sourceId: source._id},
      {
        sourceCollection: "exercise_policy_drivers",
        sourceId: source._id,
        backedUpAt: new Date(),
        document: source
      },
      {upsert: true}
    );

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

</details>

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

4. On the **Advanced** tab, run this typed query:

   ```javascript
   {
     "financials.reserves": {"$elemMatch": {
       "category": "INDEMNITY",
       "amount": {"$gte": NumberDecimal("10000.00")},
       "effectiveAt": {
         "$gte": ISODate("2026-08-01T00:00:00Z"),
         "$lt": ISODate("2026-09-01T00:00:00Z")
       }
     }}
   }
   ```

Only `CLM-RSV-5001` is returned. MongoDB comparisons are type-sensitive; a value that looks like a date or decimal in the UI is not compatible with a query that uses BSON `Date` and `Decimal128` values if it is stored as a string.

Inspect the incompatible types with an Advanced filter:

```json
{
  "financials.reserves": {"$elemMatch": {
    "category": "INDEMNITY",
    "$or": [
      {"amount": {"$type": "string"}},
      {"effectiveAt": {"$type": "string"}}
    ]
  }}
}
```

Confirm only `CLM-RSV-5002` matches. Open it and verify that the indemnity strings are quoted while the expense reserve retains Decimal128 and Date values.

<details>
<summary>Command-line typed query and inspection (reference only)</summary>

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
    }, {_id: 0, claimNumber: 1}).forEach(printjson);

    db.exercise_claim_reserves.aggregate([
      {$unwind: "$financials.reserves"},
      {$project: {
        _id: 0,
        claimNumber: 1,
        category: "$financials.reserves.category",
        amountType: {$type: "$financials.reserves.amount"},
        effectiveAtType: {$type: "$financials.reserves.effectiveAt"}
      }}
    ]).forEach(printjson);'
```

</details>

#### Back Up, Repair, and Verify the Nested Element

Back up the affected claim through `exercise_data_repair_backup` using the same five UI steps from Exercise 4, with `sourceCollection: "exercise_claim_reserves"`. Verify the backup by its `sourceId` before editing.

Filter the source collection for `claimNumber = CLM-RSV-5002`, confirm exactly one result, open it, and preserve `_id`, currency, the complete expense reserve, and all other fields. Change only the indemnity element to:

```javascript
{category: "INDEMNITY", amount: NumberDecimal("12500.00"), effectiveAt: ISODate("2026-08-15T00:00:00Z")}
```

Save once. Re-run the typed business query and confirm both claims are returned. Re-run the incompatible-type filter and confirm zero results. Finally, open `CLM-RSV-5002` and confirm the expense reserve remains `1800.00` with its original date.

This whole-document UI edit is suitable only for the isolated exercise. mongo-express cannot perform the guarded array-filter update that a production repair requires.

<details>
<summary>Command-line backup and guarded repair (reference only)</summary>

Use this as an alternative to the UI repair, not after the UI has already changed the document:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const source = db.exercise_claim_reserves.findOne({claimNumber: "CLM-RSV-5002"});
    if (!source) throw new Error("CLM-RSV-5002 was not found");

    db.exercise_data_repair_backup.replaceOne(
      {sourceCollection: "exercise_claim_reserves", sourceId: source._id},
      {
        sourceCollection: "exercise_claim_reserves",
        sourceId: source._id,
        backedUpAt: new Date(),
        document: source
      },
      {upsert: true}
    );

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

</details>

### Daily Data Debugging and Safe Exercise Cleanup

Search for incompatible exercise data by running the two type filters from Exercises 4 and 5 in their respective collection pages. Record each UI result count before changing anything.

For daily debugging, record the business identifier and current document, compare it with the approved source, inspect nested field types, back up the exact document, and verify the business query plus unaffected fields. A production repair that needs a guarded partial update is outside mongo-express. Never repair every document merely because one example has the wrong shape.

To remove only the records created by one exercise, run an exact Advanced filter such as `{"exerciseId": "IDX-CLAIMS-01"}`, confirm the expected count, record each `_id`, and use the red per-document trash button for those rows. Repeat the exact filter and confirm zero results.

This cleanup leaves the collection and its indexes in place. To remove a known exercise index after an approved review, record the **Indexes** table, then select **DEL** only beside the exact generated name. Do not delete `_id_` or treat index deletion as routine housekeeping.

<details>
<summary>Command-line inspection and cleanup equivalents (reference only)</summary>

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
    });

    const filter = {exerciseId: "IDX-CLAIMS-01"};
    const before = db.exercise_claim_work_queue.countDocuments(filter);
    if (before !== 3) {
      throw new Error(`Expected 3 exercise records; found ${before}. Nothing deleted.`);
    }
    printjson(db.exercise_claim_work_queue.deleteMany(filter));
    printjson({remaining: db.exercise_claim_work_queue.countDocuments(filter)});'
```

</details>

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

<details>
<summary>Command-line import equivalent (reference only)</summary>

Run from the repository root. Change both the collection name and input filename together for the other four imports:

```bash
docker compose -f mongodb/docker-compose.yml exec -T mongodb \
  mongoimport \
    --uri 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
    --collection slow_query_claim_lookup \
    --jsonArray \
  < mongodb/mongo-express-imports/slow_query_claim_lookup.json
```

</details>

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

<details>
<summary>Command-line before/after equivalent (reference only)</summary>

Use this instead of the UI before/after steps on a clean, unindexed exercise collection:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const query = {claimNumber: "CLM-049999"};
    print("Before index:");
    printjson(db.slow_query_claim_lookup.find(query).explain("executionStats"));
    print(db.slow_query_claim_lookup.createIndex({claimNumber: 1}));
    print("After index:");
    printjson(db.slow_query_claim_lookup.find(query).explain("executionStats"));'
```

</details>

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

<details>
<summary>Command-line before/after equivalent (reference only)</summary>

Use this instead of the UI before/after steps on a clean, unindexed exercise collection:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const query = {status: "OPEN"};
    const sort = {priority: -1, reportedAt: 1};
    print("Before index:");
    printjson(db.slow_query_claim_queue.find(query).sort(sort).explain("executionStats"));
    print(db.slow_query_claim_queue.createIndex(
      {status: 1, priority: -1, reportedAt: 1}
    ));
    print("After index:");
    printjson(db.slow_query_claim_queue.find(query).sort(sort).explain("executionStats"));'
```

</details>

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

<details>
<summary>Command-line before/after equivalent (reference only)</summary>

Use this instead of the UI before/after steps on a clean, unindexed exercise collection:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const query = {
      carrierId: "CAR-02",
      "risk.state": "CA",
      status: "ACTIVE",
      renewalDate: {
        $gte: ISODate("2026-09-01T00:00:00Z"),
        $lt: ISODate("2026-10-01T00:00:00Z")
      }
    };
    print("Before index:");
    printjson(db.slow_query_policy_renewals.find(query).explain("executionStats"));
    print(db.slow_query_policy_renewals.createIndex(
      {carrierId: 1, "risk.state": 1, status: 1, renewalDate: 1}
    ));
    print("After index:");
    printjson(db.slow_query_policy_renewals.find(query).explain("executionStats"));'
```

</details>

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

<details>
<summary>Command-line before/after equivalent (reference only)</summary>

Use this instead of the UI before/after steps on a clean, unindexed exercise collection:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const query = {"provider.npi": "1000001999", status: "PENDING_REVIEW"};
    print("Before index:");
    printjson(db.slow_query_provider_payments.find(query).explain("executionStats"));
    print(db.slow_query_provider_payments.createIndex({"provider.npi": 1, status: 1}));
    print("After index:");
    printjson(db.slow_query_provider_payments.find(query).explain("executionStats"));'
```

</details>

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

<details>
<summary>Command-line before/after equivalent (reference only)</summary>

Use this instead of the UI before/after steps on a clean, unindexed exercise collection:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const query = {investigationTags: "catastrophe-watch"};
    print("Before index:");
    printjson(db.slow_query_investigation_tags.find(query).explain("executionStats"));
    print(db.slow_query_investigation_tags.createIndex({investigationTags: 1}));
    print("After index:");
    printjson(db.slow_query_investigation_tags.find(query).explain("executionStats"));'
```

</details>

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

<details>
<summary>Command-line rollback equivalent (reference only)</summary>

Target one exact generated name, for example:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson(db.slow_query_claim_lookup.getIndexes());
    printjson(db.slow_query_claim_lookup.dropIndex("claimNumber_1"));'
```

</details>

The database cleanup in the next section removes all five collections together with the rest of the isolated guide database. Do not delete similarly named collections from `workshop` or another database.

## 20. Clean Up Only the Guide Database

Verify and remove the target in mongo-express:

1. Return to the home page.
2. Select **View** beside `mongodb_express_guide` and record its collection names. Confirm every listed collection belongs to this guide.
3. Return home and separately select **View** beside `workshop`. Record its collection count and names, then return home without changing anything.
4. Find the exact `mongodb_express_guide` row and select **Del**.
5. Type the exact database name when prompted and confirm deletion.
6. Refresh the home page and confirm `mongodb_express_guide` is absent.
7. Open `workshop` again and confirm its collection count and names match the pre-delete record.

The UI has no independent second connection for this verification. Carefully preserving and comparing the pre-delete `workshop` inventory is therefore required in the UI procedure.

<details>
<summary>Command-line equivalent (reference only)</summary>

> [!WARNING]
> This command drops the entire `mongodb_express_guide` database. Verify the resolved database name and collection list before allowing it to continue.

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_express_guide?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const expected = "mongodb_express_guide";
    const actual = db.getName();
    printjson({database: actual, collections: db.getCollectionNames()});
    if (actual !== expected) {
      throw new Error(`Refusing to drop unexpected database: ${actual}`);
    }
    printjson(db.dropDatabase());'
```

Verify the remaining databases separately:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'printjson(db.adminCommand({listDatabases: 1, nameOnly: true}).databases)'
```

</details>

## 21. Stop the Local Environment

Stop MongoDB and mongo-express without deleting their persistent MongoDB volume:

```bash
docker compose -f mongodb/docker-compose.yml down
```

Do not add `-v` unless deletion of the named MongoDB data and backup volumes is explicitly intended.
