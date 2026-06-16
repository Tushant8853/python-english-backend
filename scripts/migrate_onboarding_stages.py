#!/usr/bin/env python3
"""Migrate existing users to three-stage onboarding flags."""

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

    collection = get_database()["users"]

    legacy_complete = await collection.update_many(
        {
            "onboardingComplete": True,
            "basicOnboardingComplete": {"$exists": False},
        },
        {
            "$set": {
                "basicOnboardingComplete": True,
                "intakeOnboardingComplete": True,
                "testOnboardingComplete": True,
            }
        },
    )

    partial = await collection.update_many(
        {
            "onboardingComplete": False,
            "basicOnboardingComplete": {"$exists": False},
        },
        {
            "$set": {
                "basicOnboardingComplete": False,
                "intakeOnboardingComplete": False,
                "testOnboardingComplete": False,
            }
        },
    )

    print(
        f"PASS: Migrated {legacy_complete.modified_count} completed users and "
        f"initialized {partial.modified_count} incomplete users."
    )
    await close_database()
    return 0


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
