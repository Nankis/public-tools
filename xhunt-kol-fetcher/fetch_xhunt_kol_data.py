#!/usr/bin/env python3
"""Fetch XHunt KOL ability model and soul score data.

Input lines may be X handles, @handles, or x.com profile URLs. The script writes
JSONL incrementally for safe resume, plus a final JSON bundle when it finishes.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


USER_INFO_URL = "https://kol.xhunt.ai/api/twitter/user-info?username={handle}&domain=web3"
SOUL_URL = "https://kol.xhunt.ai/api/twitter/soul?username={handle}"
DEFAULT_FIELD_CANDIDATES = (
    "twitter_user_name",
    "twitter_username",
    "twitterUserName",
    "user_name",
    "username",
    "handle",
)


@dataclass(frozen=True)
class KolInput:
    raw: str
    handle: str
    x_url: str


def normalize_kol_id(raw: str) -> KolInput | None:
    value = raw.strip()
    if not value or value.startswith("#"):
        return None

    value = value.split(",", 1)[0].strip()
    if not value:
        return None

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urllib.parse.urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        if parts[:2] == ["i", "user"] and len(parts) >= 3:
            handle = parts[2]
            return KolInput(raw=raw.strip(), handle=handle, x_url=f"https://x.com/i/user/{handle}")
        handle = parts[0].lstrip("@")
        return KolInput(raw=raw.strip(), handle=handle, x_url=f"https://x.com/{handle}")

    handle = value.lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,30}", handle):
        return None
    x_url = f"https://x.com/i/user/{handle}" if handle.isdigit() else f"https://x.com/{handle}"
    return KolInput(raw=raw.strip(), handle=handle, x_url=x_url)


def add_input(items: list[KolInput], seen: set[str], raw: Any) -> None:
    if raw is None:
        return
    item = normalize_kol_id(str(raw))
    if not item:
        return
    key = item.handle.lower()
    if key in seen:
        return
    seen.add(key)
    items.append(item)


def first_present(record: dict[str, Any], field: str) -> Any:
    if field in record:
        return record[field]
    lower_map = {str(key).lower(): value for key, value in record.items()}
    if field.lower() in lower_map:
        return lower_map[field.lower()]
    for candidate in DEFAULT_FIELD_CANDIDATES:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def read_csv_inputs(path: Path, field: str, seen: set[str]) -> list[KolInput]:
    items: list[KolInput] = []
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:4096]
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
    except csv.Error:
        pass
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames:
        for line in text.splitlines():
            add_input(items, seen, line)
        return items
    for record in reader:
        add_input(items, seen, first_present(record, field))
    return items


def iter_json_records(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("items", "data", "rows", "list", "result"):
            child = value.get(key)
            if isinstance(child, list):
                return child
        return [value]
    return []


def read_json_inputs(path: Path, field: str, seen: set[str]) -> list[KolInput]:
    items: list[KolInput] = []
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                add_input(items, seen, line)
                continue
            if isinstance(record, dict):
                add_input(items, seen, first_present(record, field))
            else:
                add_input(items, seen, record)
        return items

    value = json.loads(path.read_text(encoding="utf-8"))
    for record in iter_json_records(value):
        if isinstance(record, dict):
            add_input(items, seen, first_present(record, field))
        else:
            add_input(items, seen, record)
    return items


def read_inputs(path: Path, field: str) -> list[KolInput]:
    seen: set[str] = set()
    items: list[KolInput] = []
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return read_csv_inputs(path, field, seen)
    if suffix in {".json", ".jsonl"}:
        return read_json_inputs(path, field, seen)
    for line in path.read_text(encoding="utf-8").splitlines():
        add_input(items, seen, line)
    return items


def log_event(log_path: Path | None, level: str, message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    line = f"[{timestamp}] {level.upper()} {message}"
    print(line)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def is_finished(row: dict[str, Any]) -> bool:
    status = row.get("fetchStatus")
    if not isinstance(status, dict):
        return False
    ability = str(status.get("ability", ""))
    soul = str(status.get("soul", ""))
    return not ability.startswith("failed:") and not soul.startswith("failed:")


def load_existing_results(jsonl_path: Path) -> dict[str, dict[str, Any]]:
    if not jsonl_path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        handle = row.get("handle")
        if isinstance(handle, str) and handle:
            rows[handle.lower()] = row
    return rows


def fetch_json(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 XHunt research collector",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def load_or_fetch(
    cache_path: Path,
    url: str,
    *,
    label: str,
    log_path: Path | None,
    timeout: float,
    max_retries: int,
    base_backoff: float,
) -> tuple[dict[str, Any] | None, str]:
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8")), "cache"
        except json.JSONDecodeError:
            cache_path.unlink(missing_ok=True)

    last_error = ""
    for attempt in range(max_retries):
        try:
            data = fetch_json(url, timeout)
            if data.get("err") == "rate_limit":
                last_error = "rate_limit"
                wait = min(300.0, base_backoff * (attempt + 1) * 2)
                log_event(
                    log_path,
                    "warn",
                    f"{label} rate_limit retry={attempt + 1}/{max_retries} sleep={wait:.1f}s",
                )
                time.sleep(wait + random.uniform(0, base_backoff))
                continue
            if data.get("data") is None:
                cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                return data, "network"
            cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data, "network"
        except urllib.error.HTTPError as exc:
            last_error = f"http_{exc.code}"
            wait = min(300.0, base_backoff * (2**attempt))
            log_event(
                log_path,
                "warn",
                f"{label} http_error={exc.code} retry={attempt + 1}/{max_retries} sleep={wait:.1f}s",
            )
            time.sleep(wait + random.uniform(0, base_backoff))
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            wait = min(300.0, base_backoff * (2**attempt))
            log_event(
                log_path,
                "warn",
                f"{label} error={last_error[:120]} retry={attempt + 1}/{max_retries} sleep={wait:.1f}s",
            )
            time.sleep(wait + random.uniform(0, base_backoff))

    return None, f"failed:{last_error[:180]}"


def flatten_fields(fields: Any) -> dict[str, int]:
    scores: dict[str, int] = {}
    if not isinstance(fields, list):
        return scores
    for item in fields:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if isinstance(value, int):
                scores[key] = value
    return scores


def parse_ability(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    data = payload.get("data") or {}
    feature = data.get("feature") or {}
    multi = feature.get("multi_field") or {}
    cn = multi.get("cn") or {}
    en = multi.get("en") or {}
    scores = flatten_fields(cn.get("fields"))
    if not scores and not cn.get("summary"):
        return None
    return {
        "modelName": "KOL能力模型",
        "scores": scores,
        "summary": cn.get("summary") or None,
        "scores_en": flatten_fields(en.get("fields")),
        "summary_en": en.get("summary") or None,
        "updatedAt": multi.get("update") or None,
        "source": "XHunt user-info feature.multi_field",
    }


def parse_soul(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    data = payload.get("data") or {}
    if not isinstance(data.get("score"), int):
        return None
    scores = {
        "账户": data.get("profile_analysis"),
        "内容": data.get("content_analysis"),
        "互动数据": data.get("engagement_analysis"),
        "XHunt排名": data.get("xhunt_analysis"),
        "KOL互动": data.get("kol_interaction"),
    }
    return {
        "modelName": "灵魂指数",
        "score": data.get("score"),
        "scores": {key: value for key, value in scores.items() if isinstance(value, int)},
        "reason": data.get("reason") or None,
        "reason_en": data.get("reason_en") or None,
        "updatedAt": data.get("update_time") or None,
        "source": "XHunt soul endpoint",
    }


def payload_name(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    name = (payload.get("data") or {}).get("name")
    return name if isinstance(name, str) and name else None


def compact_row(
    item: KolInput,
    ability: dict[str, Any] | None,
    soul: dict[str, Any] | None,
    kol_name: str | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kolId": item.raw,
        "handle": item.handle,
        "kolName": kol_name,
        "x链接": item.x_url,
    }
    if ability:
        ability["handle"] = item.handle
        row["能力模型json"] = ability
    if soul:
        soul["handle"] = item.handle
        row["灵魂指数json"] = soul
    return row


def endpoint_status(parsed: dict[str, Any] | None, payload: dict[str, Any] | None, source: str) -> str:
    if parsed:
        return "ok"
    if payload and source in {"network", "cache"}:
        return "missing"
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch XHunt KOL ability model and soul score data.")
    parser.add_argument("--input", required=True, type=Path, help="CSV/TSV/JSON/JSONL/text input file.")
    parser.add_argument("--field", default="twitter_user_name", help="Input field name for CSV/JSON records.")
    parser.add_argument("--output", type=Path, default=Path("outputs/xhunt_kol_data.json"))
    parser.add_argument("--jsonl", type=Path, default=Path("outputs/xhunt_kol_data.jsonl"))
    parser.add_argument("--log", type=Path, default=Path("outputs/xhunt_kol_fetch.log"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/xhunt_kol"))
    parser.add_argument("--delay", type=float, default=20.0, help="Base delay between KOLs in seconds.")
    parser.add_argument("--jitter", type=float, default=10.0, help="Random extra delay between KOLs.")
    parser.add_argument("--endpoint-delay", type=float, default=5.0, help="Delay between ability and soul requests.")
    parser.add_argument("--endpoint-jitter", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--base-backoff", type=float, default=20.0)
    parser.add_argument("--max-consecutive-rate-limits", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="Optional test limit.")
    parser.add_argument("--force", action="store_true", help="Ignore existing JSONL resume state.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    items = read_inputs(args.input, args.field)
    if args.limit:
        items = items[: args.limit]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print(json.dumps([item.__dict__ for item in items[:10]], ensure_ascii=False, indent=2))
        print(f"total={len(items)}")
        return

    existing = {} if args.force else load_existing_results(args.jsonl)
    done = {handle for handle, row in existing.items() if is_finished(row)}
    results_by_handle: dict[str, dict[str, Any]] = dict(existing)
    consecutive_rate_limits = 0

    mode = "w" if args.force else "a"
    with args.jsonl.open(mode, encoding="utf-8") as stream:
        for index, item in enumerate(items, start=1):
            if item.handle.lower() in done:
                log_event(args.log, "info", f"{index}/{len(items)} {item.handle} skip")
                continue

            encoded = urllib.parse.quote(item.handle)
            ability_payload, ability_source = load_or_fetch(
                args.cache_dir / f"{item.handle.lower()}_ability.json",
                USER_INFO_URL.format(handle=encoded),
                label=f"{item.handle}:ability",
                log_path=args.log,
                timeout=args.timeout,
                max_retries=args.max_retries,
                base_backoff=args.base_backoff,
            )
            time.sleep(args.endpoint_delay + random.uniform(0, args.endpoint_jitter))
            soul_payload, soul_source = load_or_fetch(
                args.cache_dir / f"{item.handle.lower()}_soul.json",
                SOUL_URL.format(handle=encoded),
                label=f"{item.handle}:soul",
                log_path=args.log,
                timeout=args.timeout,
                max_retries=args.max_retries,
                base_backoff=args.base_backoff,
            )

            ability = parse_ability(ability_payload)
            soul = parse_soul(soul_payload)
            kol_name = payload_name(ability_payload) or payload_name(soul_payload)
            row = compact_row(item, ability, soul, kol_name)
            row["fetchStatus"] = {
                "ability": endpoint_status(ability, ability_payload, ability_source),
                "soul": endpoint_status(soul, soul_payload, soul_source),
            }
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            results_by_handle[item.handle.lower()] = row

            ability_status = row["fetchStatus"]["ability"]
            soul_status = row["fetchStatus"]["soul"]
            log_event(
                args.log,
                "info",
                f"{index}/{len(items)} {item.handle} ability={ability_status} soul={soul_status}",
            )

            if ability_status == "failed:rate_limit" or soul_status == "failed:rate_limit":
                consecutive_rate_limits += 1
            else:
                consecutive_rate_limits = 0
            if consecutive_rate_limits >= args.max_consecutive_rate_limits:
                log_event(
                    args.log,
                    "error",
                    f"stop: consecutive_rate_limits={consecutive_rate_limits}; resume later with same jsonl/cache",
                )
                break
            time.sleep(args.delay + random.uniform(0, args.jitter))

    rows = list(results_by_handle.values())
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    log_event(
        args.log,
        "info",
        "done "
        f"count={len(rows)} "
        f"withAbilityModel={sum(1 for row in rows if '能力模型json' in row)} "
        f"withSoulIndex={sum(1 for row in rows if '灵魂指数json' in row)} "
        f"output={args.output}",
    )


if __name__ == "__main__":
    main()
