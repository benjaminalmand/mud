from __future__ import annotations

import argparse

from mud.server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Applehill MUD server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
