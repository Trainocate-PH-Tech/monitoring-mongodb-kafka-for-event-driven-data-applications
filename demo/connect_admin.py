"""Small Kafka Connect REST client used by Module 4."""

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(base_url: str, path: str, method: str = "GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        with urlopen(Request(base_url + path, data=data, headers=headers, method=method), timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"Connect returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Cannot reach Kafka Connect at {base_url}: {error.reason}") from error
    except TimeoutError as error:
        raise RuntimeError(f"Kafka Connect request timed out at {base_url + path}") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8083")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plugins")
    commands.add_parser("list")
    status = commands.add_parser("status")
    status.add_argument("name")
    apply = commands.add_parser("apply")
    apply.add_argument("file", type=Path)
    delete = commands.add_parser("delete")
    delete.add_argument("name")
    wait = commands.add_parser("wait")
    wait.add_argument("name")
    wait.add_argument("--state", default="RUNNING", choices=("RUNNING", "FAILED", "PAUSED"))
    wait.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def print_json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    args = parse_args()
    try:
        if args.command == "plugins":
            print_json(request(args.url, "/connector-plugins"))
        elif args.command == "list":
            print_json(request(args.url, "/connectors?expand=status&expand=info"))
        elif args.command == "status":
            print_json(request(args.url, f"/connectors/{args.name}/status"))
        elif args.command == "apply":
            definition = json.loads(args.file.read_text(encoding="utf-8"))
            name, config = definition["name"], definition["config"]
            try:
                request(args.url, f"/connectors/{name}/config")
            except RuntimeError as error:
                if "HTTP 404" not in str(error):
                    raise
                result = request(args.url, "/connectors", "POST", definition)
            else:
                result = request(args.url, f"/connectors/{name}/config", "PUT", config)
            print_json(result)
        elif args.command == "delete":
            request(args.url, f"/connectors/{args.name}", "DELETE")
            print(f"[ok] Deleted connector {args.name!r}")
        else:
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                status = request(args.url, f"/connectors/{args.name}/status")
                states = [status["connector"]["state"]] + [task["state"] for task in status.get("tasks", [])]
                reached = (
                    any(state == "FAILED" for state in states)
                    if args.state == "FAILED"
                    else bool(states) and all(state == args.state for state in states)
                )
                if reached:
                    print_json(status)
                    return 0
                time.sleep(1)
            raise RuntimeError(f"Timed out waiting for {args.name!r} to reach {args.state}")
    except (KeyError, OSError, json.JSONDecodeError, RuntimeError) as error:
        print(f"[error] {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
