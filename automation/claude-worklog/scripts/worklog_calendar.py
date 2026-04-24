"""
Stop hook용: Claude/Codex 세션을 Google Calendar의 Worklog(auto)에 등록한다.

원칙:
- session_id 단위로 idempotent (extendedProperties.private.claude_session_id)
- 같은 프로젝트의 30분 내 인접 이벤트가 있으면 update (extend end + append summary)
- 짧은 throwaway는 skip: duration<5min AND no git changes AND msg<3
- timeZone=Asia/Seoul 고정
- 캘린더 설명은 짧은 인덱스만 남기고, 상세 흐름은 업무일지/세션 노트에 둔다.
- 제목은 기본적으로 규칙 기반 생성. Gemini 제목은 WORKLOG_USE_GEMINI=1일 때만 사용.

CLI:
  python worklog_calendar.py --session-id <SID>          # Stop hook 1건
  python worklog_calendar.py --date 2026-04-20           # 그날 전체
  python worklog_calendar.py --backfill 7                # 최근 N일
  --dry-run 으로 호출 안 하고 출력만
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Iterable

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
USE_GEMINI_TITLES = os.environ.get("WORKLOG_USE_GEMINI", "").lower() in {
    "1",
    "true",
    "yes",
}
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_metrics import (
    KST,
    aggregate_day,
    collect_metrics_for_date,
    extract_session_metrics,
    find_codex_session_jsonl,
    find_session_jsonl,
    fmt_duration,
    git_changes_in_window,
    kst_hhmm,
    kst_iso,
)

CAL_ID = os.environ.get("WORKLOG_CALENDAR_ID", "")
if not CAL_ID:
    raise SystemExit(
        "WORKLOG_CALENDAR_ID env var is required. "
        "Create a Google Calendar (e.g. 'Worklog(auto)') and set its ID."
    )

# 프로젝트 이름 → Google Calendar colorId 매핑. 본인 프로젝트에 맞게 수정.
# color 코드: https://developers.google.com/calendar/api/v3/reference/colors
PROJECT_COLOR = {
    # "my-project": "10",  # basil
    # "side-project": "6", # tangerine
}
DEFAULT_COLOR = "9"  # blueberry

MIN_DURATION_SEC = 5 * 60
MIN_MSG_FALLBACK = 3
MERGE_GAP_SEC = 30 * 60  # 30분


# ── gws 호출 래퍼 ──────────────────────────────────────────
def _gws(args: list[str], params: dict, body: dict | None = None) -> dict:
    env = os.environ.copy()
    env["GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND"] = "file"
    cmd = ["gws"] + args + ["--params", json.dumps(params)]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        # API 에러는 stdout에 JSON으로 들어옴
        detail = out or r.stderr.strip()
        raise RuntimeError(f"gws failed: {' '.join(args)} :: {detail[:300]}")
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"gws stdout not JSON: {e} :: {out[:200]}")


def list_events_by_session(session_id: str) -> list[dict]:
    res = _gws(
        ["calendar", "events", "list"],
        {
            "calendarId": CAL_ID,
            "privateExtendedProperty": [f"claude_session_id={session_id}"],
            "maxResults": 5,
            "showDeleted": False,
        },
    )
    return res.get("items", [])


def list_events_in_range(
    start: dt.datetime, end: dt.datetime, project: str | None = None
) -> list[dict]:
    params = {
        "calendarId": CAL_ID,
        "timeMin": start.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeMax": end.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "maxResults": 50,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if project:
        params["privateExtendedProperty"] = [f"claude_project={project}"]
    res = _gws(["calendar", "events", "list"], params)
    return res.get("items", [])


def insert_event(body: dict) -> dict:
    return _gws(
        ["calendar", "events", "insert"],
        {"calendarId": CAL_ID},
        body=body,
    )


def patch_event(event_id: str, body: dict) -> dict:
    return _gws(
        ["calendar", "events", "patch"],
        {"calendarId": CAL_ID, "eventId": event_id},
        body=body,
    )


# ── 이벤트 본문 빌더 ──────────────────────────────────────
def _fallback_title(metrics: dict) -> str:
    if metrics["user_messages"]:
        first = metrics["user_messages"][0]["text"]
        return _compact_text(first, 30)
    return f"{metrics['tool']} 세션"


def _compact_text(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _gemini_title(metrics: dict) -> str:
    """첫 사용자 메시지들에서 8~20자 한국어 제목 생성. 실패 시 fallback."""
    if not USE_GEMINI_TITLES or not GEMINI_API_KEY or not metrics["user_messages"]:
        return _fallback_title(metrics)
    msgs = "\n".join(
        f"- [{kst_hhmm(m['ts'])}] {m['text'][:240]}"
        for m in metrics["user_messages"][:10]
    )
    top_tools = ", ".join(
        f"{k}×{v}"
        for k, v in sorted(metrics["tool_counts"].items(), key=lambda x: -x[1])[:3]
    ) or "—"
    prompt = (
        "아래는 한 작업 세션의 사용자 요청 흐름입니다. "
        "캘린더 이벤트 제목으로 쓸 수 있게, **이 세션에서 한 작업의 핵심**을 "
        "**한국어 8~20자, 명사구**로 압축하세요.\n\n"
        "규칙:\n"
        "- 동사보다 결과/대상물을 명시 (예: '구글 드라이브 마이그레이션', 'n8n 뉴스레터 초안')\n"
        "- '구글', '원고' 같은 단답 금지 — 무엇에 대한 작업인지 알 수 있어야 함\n"
        "- 따옴표·마침표·설명·접두어 금지, 제목 텍스트만\n\n"
        f"프로젝트: {metrics['project']}\n"
        f"활성 시간: {fmt_duration(metrics['duration_sec'])}\n"
        f"주 도구: {top_tools}\n"
        f"사용자 요청 흐름:\n{msgs}"
    )
    try:
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 80,
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            }
        ).encode()
        req = urllib.request.Request(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        text = ""
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                t = (part.get("text") or "").strip()
                if t:
                    text = t
                    break
            if text:
                break
        text = text.strip(" \"'`*\n.。").split("\n")[0]
        if len(text) < 5:
            return _fallback_title(metrics)
        return text[:40]
    except Exception as e:
        print(f"  WARN  Gemini title failed: {e}")
        return _fallback_title(metrics)


def _description(metrics: dict, git: dict, *, session_count: int = 1) -> str:
    lines = []
    lines.append(f"프로젝트: {metrics['project']} ({metrics['tool']})")
    lines.append(
        f"활성: {fmt_duration(metrics['duration_sec'])} "
        f"({kst_hhmm(metrics['first_ts'])}–{kst_hhmm(metrics['last_ts'])})"
    )
    if session_count > 1:
        lines.append(f"세션: {session_count}개 머지")
    lines.append(
        f"메시지: {metrics['user_msg_count']}건 / "
        f"Tool: {sum(metrics['tool_counts'].values())}회 "
        f"({_top_tools(metrics['tool_counts'])})"
    )
    if git["commits"] or git["files"]:
        lines.append(
            f"Git: {git['commits']} commit / "
            f"{git['files']} files / +{git['insertions']} -{git['deletions']}"
        )
    if metrics.get("token_usage"):
        u = metrics["token_usage"]
        lines.append(
            f"토큰: {u['total_tokens']:,} (추정 ${u['total_cost']:.2f}, "
            f"{u['primary_model']})"
        )
    if metrics.get("project_dir"):
        lines.append(f"경로: {metrics['project_dir']}")
    if metrics["user_messages"]:
        lines.append("")
        lines.append("핵심 요청:")
        first = metrics["user_messages"][0]
        lines.append(f"- [{kst_hhmm(first['ts'])}] {_compact_text(first['text'], 90)}")
        if len(metrics["user_messages"]) > 1:
            last = metrics["user_messages"][-1]
            if last["text"] != first["text"]:
                lines.append(
                    f"- [{kst_hhmm(last['ts'])}] {_compact_text(last['text'], 90)}"
                )
    lines.append("")
    lines.append(f"session_id: {metrics['session_id']}")
    return "\n".join(lines)


def _top_tools(counts: dict[str, int]) -> str:
    if not counts:
        return "—"
    items = sorted(counts.items(), key=lambda x: -x[1])[:4]
    return ", ".join(f"{k}×{v}" for k, v in items)


def build_event_body(metrics: dict, git: dict, *, title: str | None = None) -> dict:
    color = PROJECT_COLOR.get(metrics["project"], DEFAULT_COLOR)
    if title is None:
        title = _gemini_title(metrics)
    return {
        "summary": f"[{metrics['project']}] {title}",
        "description": _description(metrics, git),
        "start": {
            "dateTime": kst_iso(metrics["first_ts"]),
            "timeZone": "Asia/Seoul",
        },
        "end": {
            "dateTime": kst_iso(metrics["last_ts"]),
            "timeZone": "Asia/Seoul",
        },
        "colorId": color,
        "transparency": "transparent",  # busy로 안 보이게
        "extendedProperties": {
            "private": {
                "claude_session_id": metrics["session_id"],
                "claude_project": metrics["project"],
                "claude_tool": metrics["tool"],
            }
        },
    }


# ── 머지/upsert 로직 ──────────────────────────────────────
def find_mergeable_event(metrics: dict) -> dict | None:
    """같은 프로젝트의 이벤트 중, 종료 시각과 새 세션 시작 시각의 gap이 30분 이내."""
    window_start = metrics["first_ts"] - dt.timedelta(seconds=MERGE_GAP_SEC)
    window_end = metrics["last_ts"] + dt.timedelta(seconds=MERGE_GAP_SEC)
    candidates = list_events_in_range(window_start, window_end, project=metrics["project"])
    best = None
    best_gap = MERGE_GAP_SEC + 1
    for ev in candidates:
        # 같은 session_id면 머지 대상이 아니라 update 대상 (앞 단계에서 처리)
        ext = (ev.get("extendedProperties") or {}).get("private") or {}
        if ext.get("claude_session_id") == metrics["session_id"]:
            continue
        end_str = (ev.get("end") or {}).get("dateTime")
        start_str = (ev.get("start") or {}).get("dateTime")
        if not end_str or not start_str:
            continue
        try:
            ev_end = dt.datetime.fromisoformat(end_str)
            ev_start = dt.datetime.fromisoformat(start_str)
        except Exception:
            continue
        # 시간 비교는 KST 기준
        if ev_end.tzinfo is None:
            ev_end = ev_end.replace(tzinfo=KST)
        if ev_start.tzinfo is None:
            ev_start = ev_start.replace(tzinfo=KST)
        # 새 세션이 기존 이벤트 끝나고 30분 이내에 시작했나, 또는 겹치나
        gap_after = (metrics["first_ts"] - ev_end).total_seconds()
        gap_before = (ev_start - metrics["last_ts"]).total_seconds()
        gap = max(0, min(abs(gap_after), abs(gap_before)))
        # 시간 겹치면 무조건 머지
        if metrics["first_ts"] <= ev_end and metrics["last_ts"] >= ev_start:
            gap = 0
        elif gap_after > MERGE_GAP_SEC or gap_before > MERGE_GAP_SEC:
            continue
        if gap < best_gap:
            best = ev
            best_gap = gap
    return best


def merged_body(existing: dict, metrics: dict, git: dict) -> dict:
    """기존 이벤트 + 새 세션을 머지한 body. (제목 보존 — Gemini 호출 없음)"""
    try:
        ex_start = dt.datetime.fromisoformat(existing["start"]["dateTime"])
        ex_end = dt.datetime.fromisoformat(existing["end"]["dateTime"])
    except Exception:
        return build_event_body(metrics, git)
    if ex_start.tzinfo is None:
        ex_start = ex_start.replace(tzinfo=KST)
    if ex_end.tzinfo is None:
        ex_end = ex_end.replace(tzinfo=KST)
    new_start = min(ex_start, metrics["first_ts"])
    new_end = max(ex_end, metrics["last_ts"])

    title = existing.get("summary", "").strip()
    if not title:
        title = f"[{metrics['project']}] {_fallback_title(metrics)}"
    if "(+세션" not in title:
        title = f"{title} (+세션)"

    ext_priv = (existing.get("extendedProperties") or {}).get("private") or {}
    merged_ids = ext_priv.get("claude_merged_session_ids", "")
    merged_list = [s for s in merged_ids.split(",") if s]
    if metrics["session_id"] not in merged_list:
        merged_list.append(metrics["session_id"])
    ext_priv["claude_merged_session_ids"] = ",".join(merged_list)
    display_metrics = dict(metrics)
    display_metrics["first_ts"] = new_start
    display_metrics["last_ts"] = new_end
    display_metrics["duration_sec"] = int((new_end - new_start).total_seconds())
    new_desc = _description(display_metrics, git, session_count=len(merged_list) + 1)

    color = existing.get("colorId") or PROJECT_COLOR.get(
        metrics["project"], DEFAULT_COLOR
    )
    return {
        "summary": title,
        "description": new_desc,
        "start": {"dateTime": kst_iso(new_start), "timeZone": "Asia/Seoul"},
        "end": {"dateTime": kst_iso(new_end), "timeZone": "Asia/Seoul"},
        "colorId": color,
        "transparency": "transparent",
        "extendedProperties": {"private": ext_priv},
    }


def should_skip(metrics: dict, git: dict) -> tuple[bool, str]:
    if metrics["duration_sec"] < MIN_DURATION_SEC:
        if git["commits"] == 0 and metrics["user_msg_count"] < MIN_MSG_FALLBACK:
            return True, (
                f"throwaway: dur={fmt_duration(metrics['duration_sec'])}, "
                f"git=0, msgs={metrics['user_msg_count']}"
            )
    return False, ""


# ── 메인 액션 ──────────────────────────────────────────────
def upsert_one(
    metrics: dict,
    *,
    dry_run: bool,
    verbose: bool = True,
    allow_new: bool = True,
) -> str:
    git = git_changes_in_window(
        metrics["project_dir"], metrics["first_ts"], metrics["last_ts"]
    )
    skip, reason = should_skip(metrics, git)
    sid = metrics["session_id"]
    label = (
        f"{kst_hhmm(metrics['first_ts'])}-{kst_hhmm(metrics['last_ts'])} "
        f"[{metrics['project']}] {sid[:8]}"
    )
    if skip:
        if verbose:
            print(f"  SKIP  {label} — {reason}")
        return "skip"

    # 1) 같은 session_id 이벤트가 이미 있으면 partial patch (제목 보존, Gemini 호출 0)
    existing = []
    try:
        existing = list_events_by_session(sid)
    except RuntimeError as e:
        print(f"  WARN  {label} — list failed: {e}")
    if existing:
        partial = {
            "description": _description(metrics, git),
            "start": {
                "dateTime": kst_iso(metrics["first_ts"]),
                "timeZone": "Asia/Seoul",
            },
            "end": {
                "dateTime": kst_iso(metrics["last_ts"]),
                "timeZone": "Asia/Seoul",
            },
        }
        if dry_run:
            print(f"  PATCH {label} ← same session (dry, would update {existing[0]['id']})")
        else:
            patch_event(existing[0]["id"], partial)
            print(f"  PATCH {label} ← updated existing event {existing[0]['id']}")
        return "patch"

    # 2) 머지 가능한 인접 이벤트? (read는 dry에서도 OK)
    mergeable = None
    try:
        mergeable = find_mergeable_event(metrics)
    except RuntimeError as e:
        print(f"  WARN  {label} — merge search failed: {e}")
    if mergeable:
        body = merged_body(mergeable, metrics, git)
        if dry_run:
            print(f"  MERGE {label} → into '{mergeable.get('summary','')}' (dry)")
        else:
            patch_event(mergeable["id"], body)
            print(f"  MERGE {label} → into {mergeable['id']}")
        return "merge"

    # 3) 신규 생성
    if not allow_new:
        if verbose:
            print(f"  SKIP  {label} — no existing event")
        return "skip"
    body = build_event_body(metrics, git)
    if dry_run:
        print(f"  NEW   {label} → '{body['summary']}' (dry)")
    else:
        res = insert_event(body)
        print(f"  NEW   {label} → {res.get('id','?')}")
    return "new"


def upsert_session_id(session_id: str, *, dry_run: bool, allow_new: bool = True) -> None:
    j = find_session_jsonl(session_id)
    if not j:
        # codex
        cj = find_codex_session_jsonl(session_id)
        if cj:
            from session_metrics import _extract_codex_metrics

            m = _extract_codex_metrics(cj, dt.date.today().isoformat())
        else:
            print(f"[ERROR] session_id {session_id} jsonl not found")
            return
    else:
        m = extract_session_metrics(j)
    if not m:
        print(f"[ERROR] session_id {session_id} metrics empty")
        return
    print(f"[1 session] dry={dry_run}")
    upsert_one(m, dry_run=dry_run, allow_new=allow_new)


def upsert_date(date_str: str, *, dry_run: bool, allow_new: bool = True) -> None:
    metrics = collect_metrics_for_date(date_str)
    print(f"[{date_str}] {len(metrics)} sessions, dry={dry_run}")
    counts = {"skip": 0, "patch": 0, "merge": 0, "new": 0}
    for m in metrics:
        action = upsert_one(m, dry_run=dry_run, allow_new=allow_new)
        counts[action] = counts.get(action, 0) + 1
    print(
        f"  → new={counts['new']} merge={counts['merge']} "
        f"patch={counts['patch']} skip={counts['skip']}"
    )


def retitle_date(date_str: str, *, dry_run: bool) -> None:
    """그날 Worklog 이벤트의 제목을 다시 생성해 갱신."""
    day_start = dt.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
    day_end = day_start + dt.timedelta(days=1)
    events = list_events_in_range(day_start, day_end, project=None)
    print(f"[retitle {date_str}] {len(events)} events, dry={dry_run}")
    for ev in events:
        ext = (ev.get("extendedProperties") or {}).get("private") or {}
        sid = ext.get("claude_session_id")
        project = ext.get("claude_project", "?")
        if not sid:
            continue
        # primary session_id 기반 metrics
        j = find_session_jsonl(sid)
        if not j:
            cj = find_codex_session_jsonl(sid)
            if not cj:
                print(f"  WARN  {ev['id']} sid={sid[:8]} jsonl not found")
                continue
            from session_metrics import _extract_codex_metrics

            m = _extract_codex_metrics(cj, date_str)
        else:
            m = extract_session_metrics(j)
        if not m:
            continue
        title = _gemini_title(m)
        suffix = " (+세션)" if ext.get("claude_merged_session_ids") else ""
        new_summary = f"[{project}] {title}{suffix}"
        old = ev.get("summary", "")
        if new_summary == old:
            print(f"  SAME  {ev['id']} {old[:60]}")
            continue
        if dry_run:
            print(f"  PATCH {ev['id']}")
            print(f"    old: {old[:80]}")
            print(f"    new: {new_summary}")
        else:
            patch_event(ev["id"], {"summary": new_summary})
            print(f"  PATCH {ev['id']}")
            print(f"    {old[:80]}")
            print(f"  → {new_summary}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--session-id")
    p.add_argument("--date", default=dt.date.today().isoformat())
    p.add_argument("--backfill", type=int)
    p.add_argument("--retitle", action="store_true",
                   help="그날 이벤트 제목을 다시 생성")
    p.add_argument("--existing-only", action="store_true",
                   help="기존 이벤트만 갱신하고 새 이벤트는 만들지 않음")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.retitle:
        if args.backfill:
            today = dt.date.today()
            for i in range(args.backfill - 1, -1, -1):
                d = (today - dt.timedelta(days=i)).isoformat()
                retitle_date(d, dry_run=args.dry_run)
        else:
            retitle_date(args.date, dry_run=args.dry_run)
        return

    if args.session_id:
        upsert_session_id(
            args.session_id,
            dry_run=args.dry_run,
            allow_new=not args.existing_only,
        )
        return

    if args.backfill:
        today = dt.date.today()
        for i in range(args.backfill - 1, -1, -1):
            d = (today - dt.timedelta(days=i)).isoformat()
            upsert_date(d, dry_run=args.dry_run, allow_new=not args.existing_only)
        return

    upsert_date(args.date, dry_run=args.dry_run, allow_new=not args.existing_only)


if __name__ == "__main__":
    main()
