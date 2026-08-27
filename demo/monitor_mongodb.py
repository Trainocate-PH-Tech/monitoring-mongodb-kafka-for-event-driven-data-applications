"""Capture operational MongoDB health, capacity, index, and profiler evidence."""

import argparse
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

from settings import MONGODB_COLLECTION, MONGODB_DATABASE, MONGODB_URI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=MONGODB_DATABASE)
    parser.add_argument("--collection", default=MONGODB_COLLECTION)
    parser.add_argument("--uri", default=MONGODB_URI)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("snapshot", help="print a concise operational snapshot")
    subparsers.add_parser("index-usage", help="show index definitions and usage counters")
    profile = subparsers.add_parser("profile", help="show recent profiler entries")
    profile.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def snapshot(client: MongoClient, database_name: str, collection_name: str) -> None:
    database = client[database_name]
    hello = client.admin.command("hello")
    status = client.admin.command("replSetGetStatus")
    server = client.admin.command("serverStatus")
    db_stats = database.command("dbStats", scale=1)
    try:
        coll_stats = database.command("collStats", collection_name, scale=1)
    except OperationFailure as error:
        if error.code != 26:
            raise
        coll_stats = {"count": 0, "size": 0, "storageSize": 0, "totalIndexSize": 0}
    connections = server.get("connections", {})
    wired_tiger = server.get("wiredTiger", {}).get("cache", {})
    print(f"captured_at: {datetime.now(timezone.utc).isoformat()}")
    print(f"replica_set: {hello.get('setName', 'none')}")
    print(f"writable_primary: {hello.get('isWritablePrimary', False)}")
    print("members: " + ", ".join(
        f"{member.get('name')}={member.get('stateStr')}/{member.get('health')}"
        for member in status.get("members", [])
    ))
    print(f"connections_current: {connections.get('current', 0)}")
    print(f"connections_available: {connections.get('available', 0)}")
    print(f"database_data_bytes: {db_stats.get('dataSize', 0)}")
    print(f"database_storage_bytes: {db_stats.get('storageSize', 0)}")
    print(f"documents: {coll_stats.get('count', 0)}")
    print(f"collection_data_bytes: {coll_stats.get('size', 0)}")
    print(f"collection_storage_bytes: {coll_stats.get('storageSize', 0)}")
    print(f"index_bytes: {coll_stats.get('totalIndexSize', 0)}")
    print(f"cache_bytes_in_use: {wired_tiger.get('bytes currently in the cache', 0)}")


def index_usage(client: MongoClient, database_name: str, collection_name: str) -> None:
    collection = client[database_name][collection_name]
    definitions = {item["name"]: dict(item["key"]) for item in collection.list_indexes()}
    usage = {
        item["name"]: item.get("accesses", {}).get("ops", 0)
        for item in collection.aggregate([{"$indexStats": {}}])
    }
    for name, keys in definitions.items():
        print(f"{name}: keys={keys} operations_since_start={usage.get(name, 0)}")


def profile(client: MongoClient, database_name: str, limit: int) -> None:
    entries = client[database_name]["system.profile"].find(
        {}, {"ts": 1, "millis": 1, "ns": 1, "op": 1, "planSummary": 1, "command": 1}
    ).sort("$natural", -1).limit(limit)
    found = False
    for entry in entries:
        found = True
        print(entry)
    if not found:
        print("No profiler entries. Enable profiling and run a query first.")


def main() -> int:
    args = parse_args()
    client = MongoClient(args.uri, serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        if args.command == "snapshot":
            snapshot(client, args.database, args.collection)
        elif args.command == "index-usage":
            index_usage(client, args.database, args.collection)
        else:
            profile(client, args.database, args.limit)
    except (OperationFailure, PyMongoError) as error:
        print(f"[error] MongoDB monitoring failed: {error}")
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
