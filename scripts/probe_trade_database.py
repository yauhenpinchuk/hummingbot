#!/usr/bin/env python
"""Write a row via the same DB stack as the running bot (SQLConnectionManager + Metadata).

Usage from repo root:
  PYTHONPATH=. conda run -n hummingbot python scripts/probe_trade_database.py

Requires conf/conf_client.yml db_mode pointing at a reachable Postgres/SQLite.
"""
from __future__ import annotations

import time

from hummingbot.client.config.config_helpers import load_client_config_map_from_file
from hummingbot.model.metadata import Metadata
from hummingbot.model.sql_connection_manager import SQLConnectionManager, SQLConnectionType


def main() -> None:
    cm = load_client_config_map_from_file()
    mgr = SQLConnectionManager(cm, SQLConnectionType.TRADE_FILLS, db_name="hummingbot_trades")
    key = f"probe_{int(time.time() * 1000)}"
    with mgr.get_new_session() as session:
        session.merge(Metadata(key=key, value="ok"))
        session.commit()
    with mgr.get_new_session() as session:
        row = session.query(Metadata).filter(Metadata.key == key).one()
        print(f"read back Metadata: {row.key}={row.value}")
    print("OK: trade DB read/write uses the same path as Hummingbot.")


if __name__ == "__main__":
    main()
