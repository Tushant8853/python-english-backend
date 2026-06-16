#!/usr/bin/env python3
"""Deep integration test for streak APIs + MongoDB (run from python-backend/)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date, timedelta
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

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


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


async def api(
    client_http: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
    token: str | None = TOKEN,
) -> tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = await client_http.request(method, f"{BASE}{path}", headers=headers, json=json_body, params=params)
    try:
        body = response.json()
    except Exception:
        body = response.text
    return response.status_code, body


async def count_true_flags_in_mongo(db) -> tuple[int, list[dict]]:
    cursor = db.streaks.find({"userId": ObjectId(USER_ID)})
    docs = [doc async for doc in cursor]
    total = 0
    for doc in docs:
        wd = doc.get("weekDays") or {}
        total += sum(1 for v in wd.values() if v)
    return total, docs


async def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    mongo_uri = os.environ["MONGODB_URI"]
    db_name = os.environ.get("MONGODB_DB_NAME", "english-guru")

    client_http = httpx.AsyncClient(timeout=30.0)
    motor = AsyncIOMotorClient(mongo_uri)
    db = motor[db_name]
    try:
        print("=" * 60)
        print("STREAK DEEP TEST")
        print(f"BASE={BASE}  USER_ID={USER_ID}")
        print("=" * 60)

        # --- Auth / health ---
        code, body = await api(client_http, "GET", "/health", token=None)
        if code == 200:
            ok("health")
        else:
            fail("health", f"status={code} body={body}")

        code, body = await api(client_http, "GET", "/streak/status", token="invalid.jwt")
        if code == 400:
            ok("auth rejects invalid token", f"status={code}")
        else:
            fail("auth rejects invalid token", f"expected 400 got {code} {body}")

        code, body = await api(client_http, "GET", "/streak/status", token=None)
        if code == 400:
            ok("auth requires bearer", f"status={code}")
        else:
            fail("auth requires bearer", f"expected 400 got {code}")

        # --- Baseline ---
        code, status_before = await api(client_http, "GET", "/streak/status")
        if code != 200 or not status_before.get("success"):
            fail("GET /streak/status baseline", str(status_before))
            print_summary()
            return 1
        ok("GET /streak/status", json.dumps(status_before.get("data"), default=str))

        code, session_before = await api(client_http, "GET", "/reports/session-complete")
        code2, consistency_before = await api(client_http, "GET", "/reports/consistency")
        code3, current_before = await api(client_http, "GET", "/reports/current-streak")
        if code == 200 and code2 == 200 and code3 == 200:
            ok(
                "reports baseline",
                f"sessions={session_before.get('data')} consistency={consistency_before.get('data')} "
                f"currentStreak={current_before.get('data')}",
            )
        else:
            fail("reports baseline", f"session={code} consistency={code2} current={code3}")

        mongo_total_before, mongo_docs_before = await count_true_flags_in_mongo(db)
        api_total_before = session_before.get("data", {}).get("sessionsCompleted", -1)
        if mongo_total_before == api_total_before:
            ok("session-complete matches MongoDB count", str(mongo_total_before))
        else:
            fail(
                "session-complete matches MongoDB",
                f"api={api_total_before} mongo={mongo_total_before}",
            )

        # --- Invalid inputs ---
        code, body = await api(client_http, "POST", "/streak/update", json_body={"day": "nope"})
        if code == 400 or (isinstance(body, dict) and body.get("status") == "error"):
            ok("POST /streak/update invalid day rejected")
        else:
            fail("invalid day", f"code={code} body={body}")

        code, body = await api(client_http, "POST", "/streak/check-in", json_body={"dateKey": "bad-date"})
        if code == 400 or (isinstance(body, dict) and "Invalid" in str(body)):
            ok("POST /streak/check-in invalid dateKey rejected")
        else:
            fail("invalid dateKey", f"code={code} body={body}")

        code, body = await api(client_http, "GET", "/streak/month", params={"year": 1999, "month": 6})
        if code == 422 or code == 400:
            ok("GET /streak/month invalid year rejected", f"status={code}")
        else:
            fail("invalid year", f"code={code}")

        # --- Today check-in (idempotent) ---
        code, check1 = await api(client_http, "POST", "/streak/check-in", json_body={})
        if code != 200 or not check1.get("success"):
            fail("check-in first", str(check1))
        else:
            d1 = check1["data"]
            ok(
                "check-in first",
                f"dateKey={d1.get('dateKey')} streakUpdated={d1.get('streakUpdated')} weekStart={d1.get('weekStart')}",
            )

        code, check2 = await api(client_http, "POST", "/streak/check-in", json_body={})
        if code == 200 and check2.get("data", {}).get("streakUpdated") is False:
            ok("check-in idempotent", "streakUpdated=false on second call")
        else:
            fail("check-in idempotent", str(check2))

        code, status_after_checkin = await api(client_http, "GET", "/streak/status")
        week_days = status_after_checkin.get("data", {}).get("weekDays", {})
        from app.services.streak_service import day_key_from_date_key, today_in_streak_zone

        today = today_in_streak_zone().isoformat()
        today_key = day_key_from_date_key(today)
        if today_key and week_days.get(today_key) is True:
            ok("status reflects today after check-in", f"{today_key}=true")
        else:
            fail("status after check-in", f"today={today} weekDays={week_days}")

        # --- MongoDB doc for current week ---
        week_start = status_after_checkin["data"]["weekStart"]
        mongo_week = await db.streaks.find_one(
            {"userId": ObjectId(USER_ID), "weekStart": week_start},
        )
        if mongo_week and mongo_week.get("weekDays", {}).get(today_key):
            ok("MongoDB week doc matches API", f"weekStart={week_start}")
        else:
            fail("MongoDB week doc", str(mongo_week))

        # --- POST /streak/update another day in current week ---
        # Pick wed if today is mon, else tue
        other_day = "wed" if today_key == "mon" else "tue"
        code, upd = await api(client_http, "POST", "/streak/update", json_body={"day": other_day})
        if code == 200 and upd.get("data", {}).get("weekDays", {}).get(other_day):
            ok(f"POST /streak/update marks {other_day}")
        else:
            fail(f"update {other_day}", str(upd))

        # --- Historical dateKey in same week ---
        try:
            monday = date.fromisoformat(week_start)
            historical = (monday + timedelta(days=1)).isoformat()  # Tuesday of this week
        except ValueError:
            historical = today
        code, hist = await api(
            client_http,
            "POST",
            "/streak/check-in",
            json_body={"dateKey": historical},
        )
        if code == 200:
            ok("check-in historical dateKey in week", f"{historical} streakUpdated={hist['data'].get('streakUpdated')}")
        else:
            fail("historical check-in", str(hist))

        # --- Month map ---
        today_d = today_in_streak_zone()
        code, month_res = await api(
            client_http,
            "GET",
            "/streak/month",
            params={"year": today_d.year, "month": today_d.month},
        )
        if code == 200:
            days_map = month_res.get("data", {}).get("days", {})
            if today in days_map and days_map[today]:
                ok("month map includes today", f"{len(days_map)} days in map")
            else:
                fail("month map today", f"today={today} map={days_map}")
        else:
            fail("GET /streak/month", str(month_res))

        # --- Reports after mutations ---
        code, session_after = await api(client_http, "GET", "/reports/session-complete")
        code2, consistency_after = await api(client_http, "GET", "/reports/consistency")
        mongo_total_after, _ = await count_true_flags_in_mongo(db)
        api_total_after = session_after.get("data", {}).get("sessionsCompleted", 0)
        if mongo_total_after == api_total_after:
            ok("session-complete after mutations", f"total={api_total_after}")
        else:
            fail("session-complete after", f"api={api_total_after} mongo={mongo_total_after}")

        if code2 == 200:
            pct = consistency_after.get("data", {}).get("consistencyPercent")
            if isinstance(pct, int) and 0 <= pct <= 100:
                ok("consistency percent in range", f"{pct}%")
            else:
                fail("consistency range", str(consistency_after))

        code3, current_after = await api(client_http, "GET", "/reports/current-streak")
        if code3 == 200 and current_after.get("success"):
            cs = current_after.get("data", {})
            cur = cs.get("currentStreak")
            lng = cs.get("longestStreak")
            if isinstance(cur, int) and isinstance(lng, int) and cur <= lng:
                ok("current-streak after mutations", json.dumps(cs))
            else:
                fail("current-streak invariants", str(cs))
        else:
            fail("GET /reports/current-streak", str(current_after))

        if api_total_after >= api_total_before:
            ok("total monotonic after check-ins", f"{api_total_before} -> {api_total_after}")
        else:
            fail("total decreased", f"{api_total_before} -> {api_total_after}")

        # --- Unique index exists ---
        indexes = await db.streaks.index_information()
        has_unique = any(
            spec.get("unique") and spec.get("key") == [("userId", 1), ("weekStart", 1)]
            for spec in indexes.values()
        )
        if has_unique:
            ok("MongoDB unique index userId+weekStart")
        else:
            fail("unique index", str(list(indexes.keys())))

        # --- User exists and active ---
        user = await db.users.find_one({"_id": ObjectId(USER_ID), "status": "active"})
        if user:
            ok("JWT user active in MongoDB", user.get("email", ""))
        else:
            fail("user active", "not found or not active")

        print("\n" + "=" * 60)
        print_summary()
        return 0 if failed == 0 else 1
    finally:
        await client_http.aclose()
        motor.close()


def print_summary() -> None:
    print(f"SUMMARY: {passed} passed, {failed} failed")
    if failed:
        print("Failed tests listed above.")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
