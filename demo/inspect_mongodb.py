"""Inspect MongoDB order statistics and the customer lookup query plan."""

import argparse

from pymongo import ASCENDING, MongoClient
from pymongo.errors import OperationFailure, PyMongoError

from settings import (
    CUSTOMER_INDEX_NAME,
    MONGODB_COLLECTION,
    MONGODB_DATABASE,
    MONGODB_URI,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="show replica-set and server health")
    subparsers.add_parser("stats", help="show collection and index statistics")

    query = subparsers.add_parser("query", help="explain a customer lookup")
    query.add_argument("--customer-id", default="CUST-1001")

    subparsers.add_parser("create-index", help="create the customer_id index")
    subparsers.add_parser("drop-index", help="drop the customer_id index")
    return parser.parse_args()


def find_stages(value) -> set[str]:
    stages = set()
    if isinstance(value, dict):
        if isinstance(value.get("stage"), str):
            stages.add(value["stage"])
        for child in value.values():
            stages.update(find_stages(child))
    elif isinstance(value, list):
        for child in value:
            stages.update(find_stages(child))
    return stages


def show_stats(database, collection) -> None:
    try:
        stats = database.command("collStats", MONGODB_COLLECTION)
    except OperationFailure as error:
        if error.code == 26:
            print("[info] The orders collection does not exist yet. Run the consumer first.")
            return
        raise

    print(f"documents: {stats.get('count', 0)}")
    print(f"storage bytes: {stats.get('storageSize', 0)}")
    print(f"total index bytes: {stats.get('totalIndexSize', 0)}")
    print("indexes:")
    for index in collection.list_indexes():
        print(f"  - {index['name']}: {dict(index['key'])}")


def show_health(client) -> None:
    hello = client.admin.command("hello")
    status = client.admin.command("replSetGetStatus")
    server = client.admin.command("serverStatus")

    print(f"replica set: {hello.get('setName', 'not configured')}")
    print(f"is writable primary: {hello.get('isWritablePrimary', False)}")
    print(f"uptime seconds: {server.get('uptime', 0)}")
    connections = server.get("connections", {})
    print(
        f"connections: current={connections.get('current', 0)} "
        f"available={connections.get('available', 0)}"
    )
    print("replica members:")
    for member in status.get("members", []):
        print(
            f"  - {member.get('name')}: state={member.get('stateStr')} "
            f"health={member.get('health')}"
        )


def explain_query(database, customer_id: str) -> None:
    explanation = database.command(
        "explain",
        {
            "find": MONGODB_COLLECTION,
            "filter": {"customer_id": customer_id},
        },
        verbosity="executionStats",
    )
    execution = explanation["executionStats"]
    stages = sorted(find_stages(explanation["queryPlanner"]["winningPlan"]))

    print(f"customer_id: {customer_id}")
    print(f"plan stages: {', '.join(stages)}")
    print(f"returned: {execution['nReturned']}")
    print(f"documents examined: {execution['totalDocsExamined']}")
    print(f"index keys examined: {execution['totalKeysExamined']}")


def main() -> int:
    args = parse_args()
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        database = client[MONGODB_DATABASE]
        collection = database[MONGODB_COLLECTION]

        if args.command == "health":
            show_health(client)
        elif args.command == "stats":
            show_stats(database, collection)
        elif args.command == "query":
            explain_query(database, args.customer_id)
        elif args.command == "create-index":
            name = collection.create_index(
                [("customer_id", ASCENDING)], name=CUSTOMER_INDEX_NAME
            )
            print(f"[ok] Created index {name!r}")
        elif args.command == "drop-index":
            if CUSTOMER_INDEX_NAME not in collection.index_information():
                print(f"[ok] Index {CUSTOMER_INDEX_NAME!r} is already absent")
            else:
                collection.drop_index(CUSTOMER_INDEX_NAME)
                print(f"[ok] Dropped index {CUSTOMER_INDEX_NAME!r}")
    except (KeyError, OperationFailure, PyMongoError) as error:
        print(f"[error] MongoDB inspection failed: {error}")
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
