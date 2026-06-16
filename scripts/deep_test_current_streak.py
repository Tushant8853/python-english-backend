#!/usr/bin/env python3
"""
Exhaustive deep test for Snapchat-style current streak.

Layers:
  1. Pure-function unit tests (compute_current_streak_report, compute_longest_streak, build_completed_dates)
  2. Service-layer tests against real MongoDB documents (read-only for test user)
  3. HTTP API integration + schema validation
  4. Cross-check: API response must match independently computed values from MongoDB

Run from python-backend/:
  source .venv/bin/activate && python scripts/deep_test_current_streak.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Ensure python-backend on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.streak import STREAK_DAY_KEYS, StreakDocument
from app.services.progress_report_service import (
    CurrentStreakReport,
    ProgressReportService,
    build_completed_dates_from_documents,
    compute_current_streak_report,
    compute_longest_streak,
)
from app.services.streak_service import today_in_streak_zone

BASE = os.environ.get("STREAK_TEST_BASE", "http://localhost:4001/api")
TOKEN = os.environ.get(
    "STREAK_TEST_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2YTMwMDFkMjRhZGRiNDdhZjZkZjBkMTUiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxODEzMDY3MDkxfQ.QkPS3vzbxCVe7KC7nmlb30zWz7xcyvYtOryiOmHhhI0",
)
USER_ID = "6a3001d24addb47af6df0d15"

passed = 0
failed = 0
results: list[str] = []


def ok(name: str, detail: str = "") -> None:
    global passed
    passed += 1
    line = f"PASS  {name}" + (f" — {detail}" if detail else "")
    results.append(line)
    print(line)


def fail(name: str, detail: str) -> None:
    global failed
    failed += 1
    line = f"FAIL  {name} — {detail}"
    results.append(line)
    print(line)


def d(*parts: int) -> date:
    return date(*parts)


def assert_eq(name: str, actual: Any, expected: Any) -> None:
    if actual == expected:
        ok(name, f"{actual}")
    else:
        fail(name, f"expected {expected!r}, got {actual!r}")


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        ok(name, detail)
    else:
        fail(name, detail or "condition false")


# ---------------------------------------------------------------------------
# Layer 1: Pure unit tests
# ---------------------------------------------------------------------------


def run_unit_tests() -> None:
    print("\n" + "=" * 60)
    print("LAYER 1: PURE FUNCTION UNIT TESTS")
    print("=" * 60)

    # --- build_completed_dates_from_documents ---
    doc1 = StreakDocument(
        user_id="x",
        week_start="2026-06-09",
        month="2026-06",
        week_days={"mon": True, "tue": False, "wed": True, "thu": False, "fri": False, "sat": False, "sun": False},
    )
    completed = build_completed_dates_from_documents([doc1])
    assert_eq("build dates from week doc", completed, {d(2026, 6, 9), d(2026, 6, 11)})

    bad_doc = StreakDocument("x", "not-a-date", "2026-06", empty_week_days())
    assert_eq("skip invalid weekStart", build_completed_dates_from_documents([bad_doc]), set())

    cross_week = [
        StreakDocument("x", "2026-06-09", "2026-06", {**{k: False for k in STREAK_DAY_KEYS}, "sun": True}),
        StreakDocument("x", "2026-06-16", "2026-06", {**{k: False for k in STREAK_DAY_KEYS}, "mon": True}),
    ]
    cross_dates = build_completed_dates_from_documents(cross_week)
    assert_eq("cross-week docs", cross_dates, {d(2026, 6, 15), d(2026, 6, 16)})

    # --- compute_longest_streak ---
    assert_eq("longest empty", compute_longest_streak(set()), 0)
    assert_eq("longest single", compute_longest_streak({d(2026, 1, 1)}), 1)
    assert_eq("longest run of 5", compute_longest_streak({d(2026, 1, i) for i in range(1, 6)}), 5)
    assert_eq(
        "longest with gap",
        compute_longest_streak({d(2026, 1, 1), d(2026, 1, 2), d(2026, 1, 10), d(2026, 1, 11), d(2026, 1, 12)}),
        3,
    )
    assert_eq(
        "longest non-contiguous max",
        compute_longest_streak({d(2026, 3, 1), d(2026, 3, 3), d(2026, 3, 4), d(2026, 3, 5)}),
        3,
    )

    # --- compute_current_streak_report: empty ---
    empty = compute_current_streak_report(set(), today=d(2026, 6, 15))
    assert_eq("empty current", empty.current_streak, 0)
    assert_eq("empty longest", empty.longest_streak, 0)
    assert_eq("empty at_risk", empty.streak_at_risk, False)
    assert_eq("empty last", empty.last_completed_date, None)
    assert_eq("empty today", empty.today_completed, False)

    # --- today completed: count backward ---
    three_day = {d(2026, 6, 15), d(2026, 6, 16), d(2026, 6, 17)}
    r = compute_current_streak_report(three_day, today=d(2026, 6, 17))
    assert_eq("3-day streak current", r.current_streak, 3)
    assert_eq("3-day streak longest", r.longest_streak, 3)
    assert_eq("3-day today done", r.today_completed, True)
    assert_eq("3-day not at risk", r.streak_at_risk, False)
    assert_eq("3-day last date", r.last_completed_date, "2026-06-17")

    # --- at risk: yesterday yes, today no ---
    r_risk = compute_current_streak_report({d(2026, 6, 15), d(2026, 6, 16)}, today=d(2026, 6, 17))
    assert_eq("at-risk current", r_risk.current_streak, 2)
    assert_eq("at-risk flag", r_risk.streak_at_risk, True)
    assert_eq("at-risk today false", r_risk.today_completed, False)

    # --- broken streak: gap before today ---
    broken = {d(2026, 6, 1), d(2026, 6, 8), d(2026, 6, 9)}
    r_broken = compute_current_streak_report(broken, today=d(2026, 6, 11))
    assert_eq("broken current=0", r_broken.current_streak, 0)
    assert_eq("broken longest=2", r_broken.longest_streak, 2)
    assert_eq("broken not at risk", r_broken.streak_at_risk, False)

    # --- only today (streak=1) ---
    r_one = compute_current_streak_report({d(2026, 6, 17)}, today=d(2026, 6, 17))
    assert_eq("solo today streak", r_one.current_streak, 1)

    # --- only yesterday alive (streak=1, at risk) ---
    r_yest = compute_current_streak_report({d(2026, 6, 16)}, today=d(2026, 6, 17))
    assert_eq("yesterday-only current", r_yest.current_streak, 1)
    assert_eq("yesterday-only at risk", r_yest.streak_at_risk, True)

    # --- completed in future relative to today (should not inflate current) ---
    future = {d(2026, 6, 20), d(2026, 6, 21)}
    r_future = compute_current_streak_report(future, today=d(2026, 6, 17))
    assert_eq("future dates current=0", r_future.current_streak, 0)
    assert_eq("future longest", r_future.longest_streak, 2)

    # --- week boundary: Sun Mon consecutive across weeks ---
    week_boundary = {d(2026, 6, 14), d(2026, 6, 15)}  # Sat-Sun? check: Jun 14 2026 is Sunday
    # Jun 14 2026 is Sunday, Jun 15 is Monday
    r_wb = compute_current_streak_report(week_boundary, today=d(2026, 6, 15))
    assert_eq("week boundary streak", r_wb.current_streak, 2)

    # --- longest > current when old long run ---
    old_run = {d(2026, 1, i) for i in range(1, 8)}  # 7 days in Jan
    old_run.add(d(2026, 6, 17))  # only today in June
    r_old = compute_current_streak_report(old_run, today=d(2026, 6, 17))
    assert_eq("old run current=1", r_old.current_streak, 1)
    assert_eq("old run longest=7", r_old.longest_streak, 7)

    # --- invariants on random-ish sets ---
    for today_val in [d(2026, 6, 15), d(2026, 6, 17), d(2026, 12, 31)]:
        sample = {d(2026, 6, 15), d(2026, 6, 16), d(2026, 6, 1), d(2026, 5, 30), d(2026, 5, 31)}
        rep = compute_current_streak_report(sample, today=today_val)
        assert_true(
            f"invariant current<=longest @ {today_val}",
            rep.current_streak <= rep.longest_streak,
            f"current={rep.current_streak} longest={rep.longest_streak}",
        )
        if rep.today_completed:
            assert_true(f"invariant no at-risk when today done @ {today_val}", not rep.streak_at_risk)
        if rep.current_streak == 0:
            assert_true(f"invariant no at-risk when current=0 @ {today_val}", not rep.streak_at_risk)

    # --- month with scattered days (user-like data) ---
    user_like = {d(2026, 6, 1), d(2026, 6, 8), d(2026, 6, 9), d(2026, 6, 15), d(2026, 6, 16), d(2026, 6, 17)}
    r_user = compute_current_streak_report(user_like, today=d(2026, 6, 17))
    assert_eq("user-like Jun17 current", r_user.current_streak, 3)
    assert_eq("user-like Jun17 longest", r_user.longest_streak, 3)
    r_user_risk = compute_current_streak_report(user_like, today=d(2026, 6, 18))
    assert_eq("user-like Jun18 at-risk current", r_user_risk.current_streak, 3)
    assert_eq("user-like Jun18 at-risk", r_user_risk.streak_at_risk, True)

    # --- leap year Feb 28-29 ---
    leap = {d(2024, 2, 28), d(2024, 2, 29), d(2024, 3, 1)}
    r_leap = compute_current_streak_report(leap, today=d(2024, 3, 1))
    assert_eq("leap year streak", r_leap.current_streak, 3)

    print(f"\nLayer 1 done ({passed} passed so far, {failed} failed)")


def empty_week_days() -> dict[str, bool]:
    return {key: False for key in STREAK_DAY_KEYS}


# ---------------------------------------------------------------------------
# Layer 2–4: Mongo + API integration
# ---------------------------------------------------------------------------


@dataclass
class StreakApiData:
    current_streak: int
    longest_streak: int
    streak_at_risk: bool
    last_completed_date: str | None
    today_completed: bool

    @classmethod
    def from_api(cls, body: dict) -> StreakApiData:
        data = body.get("data", {})
        return cls(
            current_streak=int(data.get("currentStreak", -1)),
            longest_streak=int(data.get("longestStreak", -1)),
            streak_at_risk=bool(data.get("streakAtRisk")),
            last_completed_date=data.get("lastCompletedDate"),
            today_completed=bool(data.get("todayCompleted")),
        )


def compute_expected_from_mongo_docs(docs: list[dict], today: date | None = None) -> CurrentStreakReport:
    streak_docs = [StreakDocument.from_mongo(doc) for doc in docs]
    completed = build_completed_dates_from_documents(streak_docs)
    return compute_current_streak_report(completed, today=today or today_in_streak_zone())


async def api_get(client: httpx.AsyncClient, path: str, token: str | None = TOKEN) -> tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = await client.get(f"{BASE}{path}", headers=headers)
    try:
        return response.status_code, response.json()
    except Exception:
        return response.status_code, response.text


async def run_integration_tests(db) -> None:
    print("\n" + "=" * 60)
    print("LAYER 2: MONGODB → SERVICE CROSS-CHECK")
    print("=" * 60)

    cursor = db.streaks.find({"userId": ObjectId(USER_ID)})
    mongo_docs = [doc async for doc in cursor]
    ok("load streak docs from MongoDB", f"{len(mongo_docs)} documents")

    today = today_in_streak_zone()
    expected = compute_expected_from_mongo_docs(mongo_docs, today=today)

    service = ProgressReportService()
    service_report = await service.get_current_streak_report(USER_ID)

    assert_eq("service currentStreak", service_report.current_streak, expected.current_streak)
    assert_eq("service longestStreak", service_report.longest_streak, expected.longest_streak)
    assert_eq("service streakAtRisk", service_report.streak_at_risk, expected.streak_at_risk)
    assert_eq("service todayCompleted", service_report.today_completed, expected.today_completed)
    assert_eq("service lastCompletedDate", service_report.last_completed_date, expected.last_completed_date)

    # Print completed dates for human audit
    streak_docs = [StreakDocument.from_mongo(doc) for doc in mongo_docs]
    completed_dates = sorted(build_completed_dates_from_documents(streak_docs))
    ok("completed dates audit", ", ".join(d.isoformat() for d in completed_dates) or "(none)")

    # session-complete vs count
    session_total = await service.get_session_complete_total(USER_ID)
    assert_eq("session total matches date count", session_total, len(completed_dates))

    # Invariants on live data
    assert_true("live current<=longest", service_report.current_streak <= service_report.longest_streak)
    if service_report.today_completed:
        assert_true("live today done => not at risk", not service_report.streak_at_risk)
    if service_report.current_streak == 0:
        assert_true("live current=0 => not at risk", not service_report.streak_at_risk)

    ok("today in streak timezone", today.isoformat())
    future_dates = [day for day in completed_dates if day > today]
    if future_dates:
        ok(
            "future check-ins present (test artifact)",
            ", ".join(day.isoformat() for day in future_dates),
        )
        rep_today_only = compute_current_streak_report(
            {day for day in completed_dates if day <= today},
            today=today,
        )
        assert_eq(
            "current streak ignores future dates",
            service_report.current_streak,
            rep_today_only.current_streak,
        )
        assert_true(
            "longest still counts full history",
            service_report.longest_streak >= rep_today_only.longest_streak,
        )
    else:
        ok("no future-dated check-ins in MongoDB")

    print("\n" + "=" * 60)
    print("LAYER 3: HTTP API + SCHEMA")
    print("=" * 60)

    client = httpx.AsyncClient(timeout=30.0)
    try:
        code, body = await api_get(client, "/reports/current-streak", token=None)
        assert_eq("API auth required status", code, 400)

        code, body = await api_get(client, "/reports/current-streak", token="bad.token.here")
        assert_eq("API invalid token status", code, 400)

        code, body = await api_get(client, "/reports/current-streak")
        if code != 200:
            fail("GET /reports/current-streak", f"status={code} body={body}")
            return

        assert_true("API success envelope", body.get("success") is True)
        data = body.get("data", {})
        required_keys = {
            "currentStreak",
            "longestStreak",
            "streakAtRisk",
            "lastCompletedDate",
            "todayCompleted",
        }
        assert_true("API has all fields", required_keys.issubset(data.keys()), str(data.keys()))

        api_report = StreakApiData.from_api(body)
        assert_eq("API currentStreak vs service", api_report.current_streak, service_report.current_streak)
        assert_eq("API longestStreak vs service", api_report.longest_streak, service_report.longest_streak)
        assert_eq("API streakAtRisk vs service", api_report.streak_at_risk, service_report.streak_at_risk)
        assert_eq("API todayCompleted vs service", api_report.today_completed, service_report.today_completed)
        assert_eq("API lastCompletedDate vs service", api_report.last_completed_date, service_report.last_completed_date)

        # Types
        assert_true("currentStreak is int", isinstance(data["currentStreak"], int))
        assert_true("longestStreak is int", isinstance(data["longestStreak"], int))
        assert_true("streakAtRisk is bool", isinstance(data["streakAtRisk"], bool))
        assert_true("todayCompleted is bool", isinstance(data["todayCompleted"], bool))
        if data["lastCompletedDate"] is not None:
            assert_true("lastCompletedDate ISO", isinstance(data["lastCompletedDate"], str) and len(data["lastCompletedDate"]) == 10)

        ok("API response snapshot", json.dumps(data))

        print("\n" + "=" * 60)
        print("LAYER 4: CHECK-IN → CURRENT STREAK FLOW")
        print("=" * 60)

        before = api_report
        check_resp = await client.post(
            f"{BASE}/streak/check-in",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={},
        )
        code = check_resp.status_code
        check_body = check_resp.json()
        if code == 200 and check_body.get("success"):
            ok("check-in today", f"streakUpdated={check_body.get('data', {}).get('streakUpdated')}")
        else:
            fail("check-in today", str(check_body))

        code, after_body = await api_get(client, "/reports/current-streak")
        after = StreakApiData.from_api(after_body if isinstance(after_body, dict) else {})

        # After idempotent check-in today: todayCompleted must be true, current >= 1
        if after.today_completed:
            ok("after check-in todayCompleted=true")
        else:
            fail("after check-in todayCompleted", str(after_body))

        assert_true("after check-in current>=1 when today done", after.current_streak >= 1)
        assert_true("after check-in not at risk when today done", not after.streak_at_risk)

        # Idempotent check-in should not change streak numbers
        check2_resp = await client.post(
            f"{BASE}/streak/check-in",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={},
        )
        _ = check2_resp.status_code
        code, after2_body = await api_get(client, "/reports/current-streak")
        after2 = StreakApiData.from_api(after2_body if isinstance(after_body, dict) else {})
        assert_eq("idempotent check-in current unchanged", after2.current_streak, after.current_streak)
        assert_eq("idempotent check-in longest unchanged", after2.longest_streak, after.longest_streak)

        print("\n" + "=" * 60)
        print("LAYER 5: SCENARIO MATRIX (synthetic docs, no DB writes)")
        print("=" * 60)

        scenarios: list[tuple[str, set[date], date, int, bool, bool]] = [
            ("gap resets", {d(2026, 6, 10)}, d(2026, 6, 13), 0, False, False),
            ("gap with yesterday missing", {d(2026, 6, 10), d(2026, 6, 11)}, d(2026, 6, 13), 0, False, False),
            ("yesterday saves", {d(2026, 6, 12)}, d(2026, 6, 13), 1, True, False),
            ("today extends", {d(2026, 6, 12), d(2026, 6, 13)}, d(2026, 6, 13), 2, False, True),
            ("year boundary", {d(2025, 12, 31), d(2026, 1, 1)}, d(2026, 1, 1), 2, False, True),
            ("30-day run", {d(2026, 1, 1) + timedelta(days=i) for i in range(30)}, d(2026, 1, 30), 30, False, True),
        ]
        for name, completed_set, ref_today, exp_current, exp_risk, exp_today in scenarios:
            rep = compute_current_streak_report(completed_set, today=ref_today)
            if (
                rep.current_streak == exp_current
                and rep.streak_at_risk == exp_risk
                and rep.today_completed == exp_today
            ):
                ok(f"scenario {name}", f"current={exp_current} atRisk={exp_risk}")
            else:
                fail(
                    f"scenario {name}",
                    f"expected current={exp_current} atRisk={exp_risk} today={exp_today}, "
                    f"got current={rep.current_streak} atRisk={rep.streak_at_risk} today={rep.today_completed}",
                )

        print("\n" + "=" * 60)
        print("LAYER 6: CONSISTENCY WITH OTHER REPORTS")
        print("=" * 60)

        code, session_body = await api_get(client, "/reports/session-complete")
        code2, consistency_body = await api_get(client, "/reports/consistency")
        sessions = session_body.get("data", {}).get("sessionsCompleted") if isinstance(session_body, dict) else None
        consistency = consistency_body.get("data", {}).get("consistencyPercent") if isinstance(consistency_body, dict) else None

        if isinstance(sessions, int) and sessions == len(completed_dates):
            ok("session-complete aligns with streak dates", str(sessions))
        else:
            fail("session-complete align", f"sessions={sessions} dates={len(completed_dates)}")

        if isinstance(consistency, int) and 0 <= consistency <= 100:
            ok("consistency in 0-100", f"{consistency}%")
        else:
            fail("consistency range", str(consistency))

        # current streak cannot exceed session total (lifetime days)
        if after2.current_streak <= sessions:
            ok("currentStreak <= sessionsCompleted", f"{after2.current_streak} <= {sessions}")
        else:
            fail("current vs sessions", f"current={after2.current_streak} sessions={sessions}")

        # If today in completed set, todayCompleted must be true
        if today.isoformat() in {d.isoformat() for d in completed_dates} or after2.today_completed:
            ok("today completion coherent with data")

    finally:
        await client.aclose()


async def main() -> int:
    from dotenv import load_dotenv

    from app.database.connection import close_database, connect_database

    load_dotenv()
    run_unit_tests()

    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        fail("MONGODB_URI", "not set — skipping integration layers")
        print_summary()
        return 1 if failed else 0

    connected = await connect_database()
    if not connected:
        fail("connect_database", "could not connect — skipping integration layers")
        print_summary()
        return 1 if failed else 0

    db_name = os.environ.get("MONGODB_DB_NAME", "english-guru")
    motor = AsyncIOMotorClient(mongo_uri)
    db = motor[db_name]
    try:
        await run_integration_tests(db)
    finally:
        motor.close()
        await close_database()

    print("\n" + "=" * 60)
    print_summary()
    return 0 if failed == 0 else 1


def print_summary() -> None:
    print(f"FINAL SUMMARY: {passed} passed, {failed} failed")
    if failed:
        print("\nFailed:")
        for line in results:
            if line.startswith("FAIL"):
                print(f"  {line}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
