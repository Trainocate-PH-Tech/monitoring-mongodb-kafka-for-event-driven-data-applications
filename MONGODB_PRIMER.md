# MongoDB Primer for Complete Beginners

This primer introduces MongoDB, compares it with a relational database, and shows how to use the MongoDB client included in this repository. The examples use an isolated database named `mongodb_primer`; they do not modify the `workshop` database used by the course labs.

## 1. MongoDB in One Sentence

MongoDB is a database that stores records as flexible, JSON-like **documents** rather than rows in fixed tables.

The basic hierarchy is:

```text
MongoDB deployment
└── Database
    └── Collection
        └── Document
            └── Field
```

A document can contain strings, numbers, Boolean values, dates, arrays, nested objects, and references to other documents. MongoDB stores documents internally as BSON, a binary representation that supports more data types than JSON.

## 2. MongoDB Compared with a Relational Database

| Dimension | Relational database | MongoDB |
| --- | --- | --- |
| Primary structure | Tables containing rows | Collections containing documents |
| Record shape | Columns defined by a table schema | Fields can vary between documents |
| Relationships | Foreign keys and joins | Embedded documents, references, and `$lookup` |
| Query style | SQL | Document queries and aggregation pipelines |
| Identity | A primary key chosen in the schema | Every document has a unique `_id` |
| Transactions | Commonly used across related tables | Supported; good document modeling can reduce the need for multi-document transactions |
| Scale-out | Depends on the database platform | Replica sets and sharding are native MongoDB concepts |

Neither model is universally better. The choice depends on the shape of the data, the application's access patterns, consistency requirements, scaling needs, and operational constraints.

### Familiar Terms

| Relational term | MongoDB term | Course example |
| --- | --- | --- |
| Database | Database | `workshop` |
| Table | Collection | `orders` |
| Row | Document | One stored order |
| Column | Field | `customer_id` or `status` |
| Primary key | `_id`, plus optional business keys | `_id` and `order_id` |
| Index | Index | `customer_id_1` |
| Join | `$lookup`, embedding, or application-side modeling | Not needed for the basic order flow |

Collection and field names are case-sensitive. Use their exact names in commands and runbooks.

## 3. Example MongoDB Document

```javascript
{
  _id: ObjectId("..."),
  name: "Ada Rivera",
  email: "ada@example.com",
  active: true,
  level: 1,
  skills: ["MongoDB", "Kafka"],
  address: {
    city: "Manila",
    country: "PH"
  },
  enrolledAt: ISODate("2026-08-27T00:00:00Z")
}
```

Notice that:

- Field names describe the data.
- Values have types; they are not all text.
- Arrays and nested objects are stored directly in a document.
- `_id` uniquely identifies the document within its collection.
- MongoDB generates an `ObjectId` for `_id` when an insert does not supply one.

## 4. Flexible Schema Does Not Mean No Data Design

Documents in one collection can have different fields, but applications still need deliberate data modeling.

- Embed data that is normally read and changed with its parent document.
- Reference data that has an independent lifecycle or could grow without a practical bound.
- Design document shapes around common read and write patterns.
- Use schema validation when required fields and types must be enforced.
- Add indexes for measured query patterns, recognizing that indexes consume storage and add write work.
- Plan compatibility when document shapes change over time.

## 5. SQL and MongoDB CRUD Comparison

| Operation | Relational SQL | MongoDB in `mongosh` |
| --- | --- | --- |
| Create a data container | `CREATE TABLE learners (...);` | `db.createCollection("learners")` |
| Insert | `INSERT INTO learners ...` | `db.learners.insertOne({...})` |
| Fetch | `SELECT * FROM learners WHERE active = true;` | `db.learners.find({active: true})` |
| Update | `UPDATE learners SET active = false WHERE email = ...;` | `db.learners.updateOne({email: ...}, {$set: {active: false}})` |
| Delete | `DELETE FROM learners WHERE email = ...;` | `db.learners.deleteOne({email: ...})` |

MongoDB filters and updates are themselves documents. Operators such as `$set`, `$inc`, `$addToSet`, `$in`, and `$gte` begin with `$`.

## 6. Start the Current MongoDB Environment

Run all shell commands from the repository root.

Start MongoDB and the mongo-express web interface, then wait until their health checks succeed:

```bash
docker compose -f mongodb/docker-compose.yml up -d --wait
```

Check the container status:

```bash
docker compose -f mongodb/docker-compose.yml ps
```

The `mongodb` and `mongo-express` services should both be reported as running and healthy. If MongoDB is not healthy, inspect its logs:

```bash
docker compose -f mongodb/docker-compose.yml logs --tail=100 mongodb
```

The environment runs MongoDB 8.3.8 as a one-member replica set named `rs0`. This is useful for local training and change streams, but it has no redundant database member or automatic failover target.

## 7. Open the MongoDB Client

The MongoDB image already includes `mongosh`, the MongoDB shell. Open it inside the running container:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/?replicaSet=rs0&directConnection=true'
```

The terminal remains at the `mongosh` prompt. Run the JavaScript-style database commands in the following sections at that prompt.

To leave `mongosh`, run:

```javascript
exit
```

You can also press `Ctrl+D`.

Useful connection strings are:

- From the host: `mongodb://localhost:27017/?replicaSet=rs0&directConnection=true`
- From a container on the MongoDB Docker network: `mongodb://mongodb:27017/?replicaSet=rs0`

## 8. Use the mongo-express Web Interface

The Compose project also starts [mongo-express](https://github.com/mongo-express/mongo-express), a browser-based interface for MongoDB. Open:

```text
http://localhost:8081
```

Use the default workshop web login:

```text
Username: workshop
Password: workshop
```

After signing in, mongo-express can be used to:

- browse databases, collections, and documents;
- create databases and collections;
- insert, edit, copy, and delete documents;
- enter document filters;
- inspect basic collection and server information.

The web container reaches MongoDB through the internal Docker connection string:

```text
mongodb://mongodb:27017/?replicaSet=rs0
```

Check the UI status from the host:

```bash
curl -fsS http://localhost:8081/status
curl -u workshop:workshop -sS -o /dev/null -w '%{http_code}\n' http://localhost:8081/
```

The status request returns `{"status":"ok"}`. The authenticated home-page request prints HTTP `200`; the same home-page request without `-u` returns HTTP `401`.

Inspect its logs if the page does not load:

```bash
docker compose -f mongodb/docker-compose.yml logs --tail=100 mongo-express
```

### Override the Workshop Login

Export overrides before starting the Compose project:

```bash
export MONGO_EXPRESS_USERNAME=courseadmin
export MONGO_EXPRESS_PASSWORD='replace-with-a-local-password'
export MONGO_EXPRESS_COOKIE_SECRET='replace-with-a-random-cookie-secret'
export MONGO_EXPRESS_SESSION_SECRET='replace-with-a-random-session-secret'
docker compose -f mongodb/docker-compose.yml up -d --wait
```

Keep these variables exported for later Compose commands. If they are omitted later, Compose evaluates the documented `workshop` defaults and may recreate the UI container with different settings.

> [!WARNING]
> These credentials protect only the mongo-express web page. They do not enable MongoDB authentication. The workshop MongoDB server has no authentication or TLS, and the UI provides destructive controls. Both published ports are restricted to `127.0.0.1`; do not expose them to another host or use this configuration in production.

The remaining examples use `mongosh` because commands are easier to record, review, repeat, and include in an operations runbook. You can use mongo-express alongside them to inspect the resulting collections and documents.

For a complete UI-based CRUD and administrator troubleshooting walkthrough, see [MONGODB_EXPRESS_GUIDE.md](MONGODB_EXPRESS_GUIDE.md).

## 9. Navigate Databases and Create a Collection

List the databases currently visible:

```javascript
show dbs
```

Select the isolated primer database:

```javascript
use mongodb_primer
```

Print the current database name:

```javascript
db
```

Expected output:

```text
mongodb_primer
```

Create a collection named `learners`:

```javascript
db.createCollection("learners")
```

Expected result:

```javascript
{ ok: 1 }
```

List the collections in the current database:

```javascript
show collections
```

Expected output includes:

```text
learners
```

MongoDB can also create a collection automatically on the first insert. Using `createCollection()` makes this introductory step explicit.

## 10. Insert Documents

### Insert One Document

```javascript
db.learners.insertOne({
  name: "Ada Rivera",
  email: "ada@example.com",
  active: true,
  level: 1,
  skills: ["MongoDB"],
  enrolledAt: new Date()
})
```

The result should contain `acknowledged: true` and the generated `_id`:

```javascript
{
  acknowledged: true,
  insertedId: ObjectId("...")
}
```

### Insert Multiple Documents

```javascript
db.learners.insertMany([
  {
    name: "Ben Santos",
    email: "ben@example.com",
    active: true,
    level: 1
  },
  {
    name: "Cara Lim",
    email: "cara@example.com",
    active: false,
    level: 2
  }
])
```

The result should contain `acknowledged: true` and two generated identifiers.

## 11. Fetch and Filter Documents

Fetch every document in the collection:

```javascript
db.learners.find()
```

Fetch one document using a business field:

```javascript
db.learners.findOne({email: "ada@example.com"})
```

Fetch only active learners at level 1 or higher:

```javascript
db.learners.find({
  active: true,
  level: {$gte: 1}
})
```

The first document passed to `find()` is the **filter**.

Return only selected fields. The second document is the **projection**:

```javascript
db.learners.find(
  {active: true, level: {$gte: 1}},
  {_id: 0, name: 1, email: 1, level: 1}
)
```

Sort the projected results by name:

```javascript
db.learners.find(
  {active: true},
  {_id: 0, name: 1, email: 1, level: 1}
).sort({name: 1})
```

Count active learners:

```javascript
db.learners.countDocuments({active: true})
```

Fetch learners whose email is in a supplied list:

```javascript
db.learners.find({
  email: {$in: ["ada@example.com", "ben@example.com"]}
})
```

## 12. Update Documents

Update selected fields without replacing the entire document:

```javascript
db.learners.updateOne(
  {email: "ada@example.com"},
  {
    $set: {active: false},
    $inc: {level: 1},
    $addToSet: {skills: "Kafka"}
  }
)
```

The result includes the number of documents matched and changed:

```javascript
{
  acknowledged: true,
  matchedCount: 1,
  modifiedCount: 1,
  upsertedId: null
}
```

Verify the stored result:

```javascript
db.learners.findOne(
  {email: "ada@example.com"},
  {_id: 0, name: 1, active: 1, level: 1, skills: 1}
)
```

Update every currently inactive learner:

```javascript
db.learners.updateMany(
  {active: false},
  {$set: {reviewRequired: true}}
)
```

Use `updateMany()` only when changing every matching document is intentional. Inspect the filter and `matchedCount` carefully.

## 13. Delete Documents

Before deleting, fetch the exact target using the same filter:

```javascript
db.learners.find({email: "cara@example.com"})
```

Delete one matching document:

```javascript
db.learners.deleteOne({email: "cara@example.com"})
```

Expected result:

```javascript
{
  acknowledged: true,
  deletedCount: 1
}
```

Verify the remaining documents:

```javascript
db.learners.find(
  {},
  {_id: 0, name: 1, email: 1}
).sort({name: 1})
```

`deleteMany({})` deletes every document in a collection. Do not run it unless that exact scope is intended and verified.

## 14. Optional Index Example

Create a unique index so two learners cannot use the same email address:

```javascript
db.learners.createIndex(
  {email: 1},
  {name: "email_1", unique: true}
)
```

List collection indexes:

```javascript
db.learners.getIndexes()
```

MongoDB automatically maintains the `_id_` index. The new `email_1` index supports email lookups and enforces uniqueness, but it also consumes storage and adds work to inserts and updates.

Remove only the demonstration index if needed:

```javascript
db.learners.dropIndex("email_1")
```

## 15. Clean Up the Primer Data

Confirm the current database before any cleanup:

```javascript
db
```

It must print:

```text
mongodb_primer
```

To remove only the `learners` collection:

```javascript
db.learners.drop()
```

To remove the entire isolated primer database:

```javascript
db.dropDatabase()
```

Expected result:

```javascript
{ ok: 1, dropped: "mongodb_primer" }
```

> [!WARNING]
> `drop()`, `dropDatabase()`, and broad delete filters are destructive. Verify the active database, collection, and filter before running them. Never substitute `workshop` for `mongodb_primer` in these cleanup examples unless a course exercise explicitly requires a scoped reset.

## 16. Run a One-Shot CRUD Example from Bash

Instead of opening an interactive prompt, `mongosh --eval` can run a short script and exit. The following command uses its own `quick_demo` collection inside `mongodb_primer`:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/mongodb_primer?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    db.quick_demo.drop();
    printjson(db.quick_demo.insertOne({name: "Example", status: "new"}));
    printjson(db.quick_demo.findOne({name: "Example"}));
    printjson(db.quick_demo.updateOne({name: "Example"}, {$set: {status: "updated"}}));
    printjson(db.quick_demo.findOne({name: "Example"}));
    printjson(db.quick_demo.deleteOne({name: "Example"}));
    printjson({remaining: db.quick_demo.countDocuments({})});
    db.quick_demo.drop();'
```

The final object should report:

```javascript
{ remaining: 0 }
```

This command deletes and recreates only `mongodb_primer.quick_demo`.

## 17. Practice Exercise

Complete the following without copying the `learners` commands exactly:

1. Start MongoDB and open `mongosh`.
2. Select the `mongodb_primer` database.
3. Create a collection named `courses`.
4. Insert two course documents containing `title`, `durationHours`, `active`, and `topics` fields.
5. Fetch active courses and return only `title` and `durationHours`.
6. Update one course using `$set` and `$addToSet`.
7. Verify `matchedCount`, `modifiedCount`, and the stored document.
8. Delete one course using a specific `title` filter.
9. Verify the remaining document count.
10. Explain which parts resemble a relational table and which document features differ.

## 18. Stop the Environment

Leave `mongosh`, then stop the container without deleting its persistent volume:

```bash
docker compose -f mongodb/docker-compose.yml down
```

Starting the Compose project again reuses the existing MongoDB volume. The isolated primer data remains unless it was removed with `drop()` or `dropDatabase()`.
