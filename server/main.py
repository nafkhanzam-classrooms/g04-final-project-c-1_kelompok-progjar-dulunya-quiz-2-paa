"""Titik masuk server. Jalanin dari root project: python -m server.main"""

import argparse
import os
import sys

# biar `python server/main.py` juga jalan, ga cuma `-m server.main`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.core.controller import (
    ServerController,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_STORAGE,
)


def main():
    import logging
    from server.log_config import setup_logging

    parser = argparse.ArgumentParser(description="Collaborative editor server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="bind port")
    parser.add_argument("--storage", default=DEFAULT_STORAGE, help="storage root folder")
    parser.add_argument("--debug", action="store_true",
                        help="log lebih detail (tiap event edit/typing ikut dicatat)")
    args = parser.parse_args()

    log = setup_logging(logging.DEBUG if args.debug else logging.INFO)

    controller = ServerController(host=args.host, port=args.port, storage_root=args.storage)
    try:
        controller.start()
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
