# Walkthrough 04: Replication, Backup, Restore Readiness, and Capacity

## Goal

Prove the database is writable, create a backup, restore it into isolation, and evaluate capacity limitations.

## Replication Health

```bash
python demo/monitor_mongodb.py snapshot

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/admin?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    const hello = db.hello();
    const status = rs.status();
    printjson({set: hello.setName, writablePrimary: hello.isWritablePrimary, members: status.members.map(m => ({name: m.name, state: m.stateStr, health: m.health, optimeDate: m.optimeDate}))});'
```

**Expected output:** both views report replica set `rs0`, writable primary `true`, and one member `mongodb:27017` in `PRIMARY` state with health `1`. **Meaning:** the node accepts writes but has no redundant member.

This one-member replica set can demonstrate state and change streams but has no failover or redundant copy.

## Backup and Restore Drill

Create a timestamped archive in the persistent backup volume:

```bash
export BACKUP_NAME="workshop-$(date -u +%Y%m%dT%H%M%SZ).archive"
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongodump --uri 'mongodb://localhost:27017/?replicaSet=rs0&directConnection=true' \
  --db workshop --archive="/backups/$BACKUP_NAME" --gzip
```

**Expected output:** export assignment is silent; `mongodump` reports writing each `workshop` collection and the number of documents dumped. **Meaning:** a timestamped compressed archive was created in the persistent backup volume.

List evidence and restore to an isolated namespace:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb ls -lh "/backups/$BACKUP_NAME"
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongorestore --uri 'mongodb://localhost:27017/?replicaSet=rs0&directConnection=true' \
  --archive="/backups/$BACKUP_NAME" --gzip \
  --nsFrom='workshop.*' --nsTo='workshop_restore.*' --drop

docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/?replicaSet=rs0&directConnection=true' \
  --quiet --eval '
    printjson({source: db.getSiblingDB("workshop").orders.countDocuments({}), restored: db.getSiblingDB("workshop_restore").orders.countDocuments({}), indexes: db.getSiblingDB("workshop_restore").orders.getIndexes()})'
```

**Expected output:** `ls` shows a nonzero archive; `mongorestore` reports zero failures; the final object shows equal source/restored counts and required indexes. **Meaning:** the archive is readable and restores into an isolated namespace with matching logical content.

Counts and required indexes must match. A backup without a tested restore is not restore-readiness evidence.

Clean only the validation database; keep the archive as workshop evidence:

```bash
docker compose -f mongodb/docker-compose.yml exec mongodb \
  mongosh 'mongodb://localhost:27017/workshop_restore?replicaSet=rs0&directConnection=true' \
  --quiet --eval 'db.dropDatabase()'
```

**Expected output:** `{ ok: 1, dropped: 'workshop_restore' }`. **Meaning:** only the validation database was removed; the source database and backup archive remain.

## Capacity Review

Compare `/data/db` usage, collection/index growth rate, connections, cache use, oplog window, backup size, and projected time to the operational limit. The lab’s single node is itself the largest availability risk.
