#!/usr/bin/env python3
"""Zet CCV Shop-orders met status "Nieuw" (1) die betaald zijn en maximaal
MAX_AGE_DAYS dagen oud zijn automatisch op "In behandeling" (2)."""

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SHOP_URL = os.environ.get("CCV_SHOP_URL", "https://www.lampionwebshop.nl").rstrip("/")
API_KEY = os.environ.get("CCV_API_KEY", "")
API_SECRET = os.environ.get("CCV_API_SECRET", "")
API_BASE = "/api/rest/v1"

STATUS_NIEUW = 1
STATUS_IN_BEHANDELING = 2
MAX_AGE_DAYS = 32
PAGE_SIZE = 100
PATCH_DELAY_SECONDS = 0.7


class CcvApiError(RuntimeError):
    pass


def request(method: str, uri: str, data: str | None = None, retries: int = 3) -> bytes:
    if not API_KEY or not API_SECRET:
        raise SystemExit("CCV_API_KEY en/of CCV_API_SECRET zijn niet ingesteld.")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    body = (data or "") if method in ("POST", "PATCH", "PUT") else ""
    hash_string = f"{API_KEY}|{method}|{uri}|{body}|{timestamp}"
    request_hash = hmac.new(API_SECRET.encode(), hash_string.encode(), hashlib.sha512).hexdigest()

    req = urllib.request.Request(SHOP_URL + uri, data=body.encode("utf-8") if body else None, method=method)
    req.add_header("x-public", API_KEY)
    req.add_header("x-date", timestamp)
    req.add_header("x-hash", request_hash)
    if body:
        req.add_header("Content-Type", "application/json")

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:400]
            if error.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise CcvApiError(f"{method} {uri} -> HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise CcvApiError(f"{method} {uri} -> netwerkfout: {error}") from error
    raise CcvApiError(f"{method} {uri} -> onbereikbaar")


def fetch_new_orders(min_create_date: str) -> list[dict]:
    orders: list[dict] = []
    start = 0
    for _ in range(50):
        uri = (
            f"{API_BASE}/orders?status={STATUS_NIEUW}"
            f"&min_create_date={urllib.parse.quote(min_create_date)}"
            f"&start={start}&size={PAGE_SIZE}"
        )
        payload = json.loads(request("GET", uri))
        items = payload if isinstance(payload, list) else payload.get("orders") or payload.get("items") or []
        if not items:
            break
        orders.extend(items)
        if len(items) < PAGE_SIZE:
            break
        start += PAGE_SIZE
        time.sleep(PATCH_DELAY_SECONDS)
    return orders


def order_created_at(order: dict) -> datetime | None:
    for key in ("create_date", "created_at", "date", "order_date"):
        value = order.get(key)
        if value:
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def main() -> int:
    dry_run = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

    now = datetime.now(timezone.utc)
    min_create_date = (now - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d")

    print(f"Shop: {SHOP_URL}")
    print("Zoeken naar orders: status=Nieuw(1), betaald, create_date >=", min_create_date)
    if dry_run:
        print("DRY RUN: er worden geen statussen gewijzigd.")

    raw = fetch_new_orders(min_create_date)
    print(f"Ontvangen: {len(raw)} order(s) met status Nieuw.")

    candidates = []
    for order in raw:
        if order.get("status") != STATUS_NIEUW or not order.get("paid"):
            continue
        created = order_created_at(order)
        if created and now - created > timedelta(days=MAX_AGE_DAYS):
            continue
        candidates.append(order)
    print(f"Gevonden: {len(candidates)} kandidaat-order(s) (betaald, binnen {MAX_AGE_DAYS} dagen).")

    changed = 0
    for order in candidates:
        order_id = order.get("id")
        if order_id is None:
            continue
        if order.get("status") != STATUS_NIEUW or not order.get("paid"):
            continue

        created = order_created_at(order)
        if created and now - created > timedelta(days=MAX_AGE_DAYS):
            continue

        print(f"Order #{order.get('order_number', order_id)} (id {order_id}) -> In behandeling (2)")
        if not dry_run:
            request("PATCH", f"{API_BASE}/orders/{order_id}", json.dumps({"status": STATUS_IN_BEHANDELING}, separators=(",", ":")))
            time.sleep(PATCH_DELAY_SECONDS)
        changed += 1

    print(f"Klaar: {changed} order(s) op 'In behandeling' gezet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
