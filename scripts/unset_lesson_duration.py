#!/usr/bin/env python3
"""Remove durationMinutes field from all lesson_library documents."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import close_database, connect_database, get_database


async def run() -> int:
    if not await connect_database():
        print("FAIL: Could not connect to MongoDB")
        return 1

    result = await get_database()["lesson_library"].update_many(
        {},
        {"$unset": {"durationMinutes": ""}},
    )
    print(f"PASS: Removed durationMinutes from {result.modified_count} lessons.")
    await close_database()
    return 0


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
