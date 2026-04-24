"""
Claude Code / Codex 세션 jsonl을 읽어 정량 지표를 추출한다.

기본 단위는 '세션 1개'. 업무일지·캘린더 양쪽이 동일한 데이터를 본다.

활성 시간 계산은 단순화: first_msg_ts → last_msg_ts.
(advisor 권고: idle 5분+ 제외는 데이터가 sparse해서 오작동.
 화면에서 diff 읽는 시간은 idle이 아니라 작업이다.)
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

KST = dt.timezone(dt.timedelta(hours=9))
PROJECTS_BASE = Path.home() / ".claude" / "projects"
SESSIONS_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~md~obsidian"
    / "Documents"
    / "Obsidian Vault"
    / "sessions"
)

PRICING = {
    "opus": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "sonnet": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "haiku": {"input": 0.80, "output": 4.0, "cache_read": 0.08, "cache_write": 1.00},
}


_META_PREFIXES = (
    "<tool_result",
    "<environment_context>",
    "<bash-input>",
    "<bash-stdout>",
    "<command-name>",
    "<local-command-stdout>",
    "<command-message>",
    "<command-args>",
    "<system-reminder>",
    "<local-command-caveat>",
    "<local-command-stderr>",
    "<ide_selection>",
    "[Request interrupted",
    "Caveat: The messages",
)


def _is_meta_message(text: str) -> bool:
    """시스템이 wrapping해서 user 이벤트로 들어가는 메타 메시지 판별."""
    s = text.lstrip()
    return any(s.startswith(p) for p in _META_PREFIXES)


def _model_tier(model_name: str) -> str:
    m = (model_name or "").lower()
    if "opus" in m:
        return "opus"
    if "haiku" in m:
        return "haiku"
    return "sonnet"


def _parse_ts(ts_str: str) -> dt.datetime | None:
    if not ts_str:
        return None
    try:
        # ISO 8601 with Z suffix
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return dt.datetime.fromisoformat(ts_str)
    except Exception:
        return None


def kst_iso(ts: dt.datetime) -> str:
    """캘린더에 넣을 KST RFC3339 문자열."""
    return ts.astimezone(KST).strftime("%Y-%m-%dT%H:%M:%S")


def kst_hhmm(ts: dt.datetime) -> str:
    return ts.astimezone(KST).strftime("%H:%M")


# ── 세션 jsonl 찾기 ─────────────────────────────────────────
def find_session_jsonl(session_id: str) -> Path | None:
    """전체 ~/.claude/projects/ 트리에서 session_id.jsonl 검색."""
    if not session_id or not PROJECTS_BASE.exists():
        return None
    matches = list(PROJECTS_BASE.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def find_codex_session_jsonl(session_id: str) -> Path | None:
    """Codex 세션 (~/.codex/sessions/...) 검색."""
    base = Path.home() / ".codex" / "sessions"
    if not base.exists():
        return None
    matches = list(base.rglob(f"rollout-*-{session_id}.jsonl"))
    return matches[0] if matches else None


# ── 세션 메트릭 추출 ────────────────────────────────────────
def extract_session_metrics(jsonl_path: Path) -> dict | None:
    """
    Claude Code session jsonl을 읽어 정량 지표를 반환.

    반환:
      {
        session_id, tool, project_dir, project,
        first_ts, last_ts, duration_sec,
        user_msg_count, assistant_msg_count,
        tool_counts: {Edit, Write, Bash, Read, Grep, ...},
        user_messages: [{ts, text}, ...],   # 최근 N개
        token_usage: {total_tokens, total_cost, primary_model, details} | None,
        git_branch,
      }
    """
    if not jsonl_path or not jsonl_path.exists():
        return None

    first_ts = None
    last_ts = None
    user_count = 0
    asst_count = 0
    tool_counts: dict[str, int] = {}
    cwd = None
    git_branch = None
    session_id = None
    user_msgs: list[dict] = []
    token_totals: dict[str, dict[str, int]] = {}

    with jsonl_path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = o.get("type")
            ts = _parse_ts(o.get("timestamp", ""))
            if ts:
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts

            if not session_id and o.get("sessionId"):
                session_id = o["sessionId"]
            if not cwd and o.get("cwd"):
                cwd = o["cwd"]
            if not git_branch and o.get("gitBranch"):
                git_branch = o["gitBranch"]

            if t == "user" and not o.get("isSidechain", False):
                msg = o.get("message", {}) or {}
                content = msg.get("content")
                text = ""
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    parts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    text = " ".join(p for p in parts if p)
                text = (text or "").strip().replace("\n", " ")
                # tool_result / 시스템 wrapping / 슬래시 호출 메타는 제외
                if text and not _is_meta_message(text):
                    user_count += 1
                    if ts:
                        user_msgs.append(
                            {"ts": ts, "text": text[:400]}
                        )

            elif t == "assistant":
                asst_count += 1
                msg = o.get("message", {}) or {}
                # tool 사용 카운트
                content = msg.get("content")
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_use":
                            name = c.get("name", "?")
                            tool_counts[name] = tool_counts.get(name, 0) + 1
                # 토큰 사용량
                usage = msg.get("usage")
                model = msg.get("model", "")
                if usage and model and model != "<synthetic>":
                    bucket = token_totals.setdefault(
                        model,
                        {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
                    )
                    bucket["input"] += usage.get("input_tokens", 0) or 0
                    bucket["output"] += usage.get("output_tokens", 0) or 0
                    bucket["cache_read"] += usage.get("cache_read_input_tokens", 0) or 0
                    bucket["cache_write"] += (
                        usage.get("cache_creation_input_tokens", 0) or 0
                    )

    if first_ts is None:
        return None

    duration = int((last_ts - first_ts).total_seconds()) if last_ts else 0

    project_dir = cwd or ""
    project = Path(project_dir).name if project_dir else "unknown"

    token_usage = _summarize_tokens(token_totals) if token_totals else None

    return {
        "session_id": session_id or jsonl_path.stem,
        "tool": "claude-code",
        "project_dir": project_dir,
        "project": project,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "duration_sec": duration,
        "user_msg_count": user_count,
        "assistant_msg_count": asst_count,
        "tool_counts": tool_counts,
        "user_messages": user_msgs[-10:],
        "token_usage": token_usage,
        "git_branch": git_branch,
    }


def _summarize_tokens(totals: dict[str, dict[str, int]]) -> dict:
    total_cost = 0.0
    total_tokens = 0
    details = []
    for model, t in totals.items():
        tier = _model_tier(model)
        p = PRICING.get(tier, PRICING["sonnet"])
        cost = (
            t["input"] * p["input"]
            + t["output"] * p["output"]
            + t["cache_read"] * p["cache_read"]
            + t["cache_write"] * p["cache_write"]
        ) / 1_000_000
        tokens = t["input"] + t["output"] + t["cache_read"] + t["cache_write"]
        total_cost += cost
        total_tokens += tokens
        details.append(
            {
                "model": model,
                "input": t["input"],
                "output": t["output"],
                "cache_read": t["cache_read"],
                "cache_write": t["cache_write"],
                "cost": cost,
                "tokens": tokens,
            }
        )
    primary_model = (
        max(details, key=lambda d: d["output"])["model"] if details else "unknown"
    )
    return {
        "details": details,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "primary_model": primary_model,
    }


def _summarize_codex_tokens(info: dict | None, model: str = "codex/openai") -> dict | None:
    """Codex token_count 이벤트를 Claude 스타일 token_usage 형태로 맞춘다."""
    if not info:
        return None
    usage = info.get("total_token_usage") or {}
    if not usage:
        return None
    input_tokens = int(usage.get("input_tokens") or 0)
    cached = int(usage.get("cached_input_tokens") or 0)
    output = int(usage.get("output_tokens") or 0)
    reasoning = int(usage.get("reasoning_output_tokens") or 0)
    total = int(usage.get("total_tokens") or (input_tokens + output))
    uncached_input = max(0, input_tokens - cached)
    detail = {
        "model": model,
        "input": uncached_input,
        "output": output,
        "cache_read": cached,
        "cache_write": 0,
        "cache_write_note": "Codex token_count는 cache write를 별도 제공하지 않음",
        "reasoning": reasoning,
        "cost": 0.0,
        "tokens": total,
        "cost_note": "Codex Pro plan usage; API 비용 산정 제외",
    }
    return {
        "details": [detail],
        "total_cost": 0.0,
        "total_tokens": total,
        "primary_model": model,
        "cost_note": detail["cost_note"],
    }


# ── git 변경량 (세션 시간 윈도) ─────────────────────────────
def git_changes_in_window(
    repo_dir: str, start: dt.datetime, end: dt.datetime
) -> dict:
    """해당 repo에서 시간 윈도 내 commits/insertions/deletions/files."""
    out = {"commits": 0, "insertions": 0, "deletions": 0, "files": 0}
    if not repo_dir or not Path(repo_dir).exists():
        return out
    since = start.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S +0000")
    until = end.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S +0000")
    try:
        r = subprocess.run(
            ["git", "log", "--shortstat", "--pretty=format:---", f"--since={since}", f"--until={until}"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return out
        text = r.stdout
        out["commits"] = text.count("---")
        for m in re.finditer(r"(\d+) insertion", text):
            out["insertions"] += int(m.group(1))
        for m in re.finditer(r"(\d+) deletion", text):
            out["deletions"] += int(m.group(1))
        for m in re.finditer(r"(\d+) files? changed", text):
            out["files"] += int(m.group(1))
    except Exception:
        pass
    return out


# ── 하루치 세션 모으기 ─────────────────────────────────────
SESSION_FILE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<project>.+?)-(?P<sid>[0-9a-f]{8}|unknown)\.md$"
)


def list_session_ids_for_date(date_str: str) -> list[str]:
    """그날 Obsidian sessions/ 폴더에서 8자리 session_id 추출."""
    if not SESSIONS_DIR.exists():
        return []
    ids = []
    for f in sorted(SESSIONS_DIR.glob(f"{date_str}-*.md")):
        m = SESSION_FILE_RE.match(f.name)
        if not m:
            continue
        sid_short = m.group("sid")
        if sid_short == "unknown":
            continue
        ids.append(sid_short)
    return ids


def collect_metrics_for_date(date_str: str) -> list[dict]:
    """
    그날 세션 노트들을 기반으로 jsonl을 찾아 metrics 리스트를 반환.
    시간순 정렬. jsonl 못 찾은 세션은 sessions/ 노트만으로 최소 메트릭 fallback.
    """
    short_ids = list_session_ids_for_date(date_str)
    if not short_ids:
        return []

    metrics: list[dict] = []
    seen = set()
    for short in short_ids:
        # short id (8자) → 전체 jsonl 검색
        if not PROJECTS_BASE.exists():
            continue
        candidates = list(PROJECTS_BASE.glob(f"*/{short}*.jsonl"))
        if not candidates:
            # codex 세션도 시도
            cand_codex = (
                list((Path.home() / ".codex" / "sessions").rglob(f"*{short}*.jsonl"))
                if (Path.home() / ".codex" / "sessions").exists()
                else []
            )
            if cand_codex:
                m = _extract_codex_metrics(cand_codex[0], date_str)
                if m and m["session_id"] not in seen:
                    seen.add(m["session_id"])
                    metrics.append(m)
            continue
        m = extract_session_metrics(candidates[0])
        if m and m["session_id"] not in seen:
            seen.add(m["session_id"])
            metrics.append(m)

    metrics.sort(key=lambda x: x["first_ts"])
    return metrics


def _extract_codex_metrics(jsonl_path: Path, date_str: str) -> dict | None:
    """Codex rollout jsonl에서 세션 메트릭을 추출한다."""
    first_ts = None
    last_ts = None
    user_count = 0
    user_msgs = []
    cwd = None
    session_id = jsonl_path.stem.split("rollout-", 1)[-1].split("-", 2)[-1]
    token_info = None
    model = "codex/openai"
    try:
        with jsonl_path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _parse_ts(o.get("timestamp", "") or o.get("ts", ""))
                if ts:
                    if first_ts is None or ts < first_ts:
                        first_ts = ts
                    if last_ts is None or ts > last_ts:
                        last_ts = ts
                payload = o.get("payload") or {}
                if not cwd:
                    cwd = o.get("cwd") or payload.get("cwd")
                if payload.get("id"):
                    session_id = payload["id"]
                if payload.get("model"):
                    model = payload["model"]
                if payload.get("type") == "token_count" and payload.get("info"):
                    token_info = payload["info"]
                role = (payload.get("role") or o.get("role") or "").lower()
                if role == "user":
                    user_count += 1
                    text = ""
                    content = payload.get("content")
                    if isinstance(content, list):
                        text = " ".join(
                            c.get("text", "")
                            for c in content
                            if isinstance(c, dict) and c.get("type") == "input_text"
                        )
                    elif isinstance(content, str):
                        text = content
                    text = text.strip().replace("\n", " ")
                    if text and ts and not _is_meta_message(text):
                        user_msgs.append({"ts": ts, "text": text[:400]})
    except Exception:
        return None
    if first_ts is None:
        return None
    project = Path(cwd).name if cwd else "codex"
    return {
        "session_id": session_id,
        "tool": "codex",
        "project_dir": cwd or "",
        "project": project,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "duration_sec": int((last_ts - first_ts).total_seconds()) if last_ts else 0,
        "user_msg_count": user_count,
        "assistant_msg_count": 0,
        "tool_counts": {},
        "user_messages": user_msgs[-10:],
        "token_usage": _summarize_codex_tokens(token_info, model),
        "git_branch": None,
    }


# ── 일자 단위 롤업 ──────────────────────────────────────────
def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    h, m = divmod(seconds // 60, 60)
    if h == 0:
        return f"{m}m"
    return f"{h}h {m:02d}m"


def aggregate_day(metrics: list[dict]) -> dict:
    """그날 전체 정량 합계 + 프로젝트별 시간."""
    by_project: dict[str, int] = {}
    msgs = 0
    tools: dict[str, int] = {}
    cost = 0.0
    tokens = 0
    first = None
    last = None
    for m in metrics:
        proj = m["project"] or "unknown"
        by_project[proj] = by_project.get(proj, 0) + m["duration_sec"]
        msgs += m["user_msg_count"]
        for k, v in m["tool_counts"].items():
            tools[k] = tools.get(k, 0) + v
        if m.get("token_usage"):
            cost += m["token_usage"]["total_cost"]
            tokens += m["token_usage"]["total_tokens"]
        if first is None or m["first_ts"] < first:
            first = m["first_ts"]
        if last is None or m["last_ts"] > last:
            last = m["last_ts"]
    return {
        "session_count": len(metrics),
        "by_project_seconds": by_project,
        "user_msg_count": msgs,
        "tool_counts": tools,
        "total_cost": cost,
        "total_tokens": tokens,
        "first_ts": first,
        "last_ts": last,
    }


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    ms = collect_metrics_for_date(target)
    print(f"[{target}] {len(ms)} sessions")
    for m in ms:
        print(
            f"  {kst_hhmm(m['first_ts'])}-{kst_hhmm(m['last_ts'])} "
            f"[{m['project']}] {m['tool']} "
            f"dur={fmt_duration(m['duration_sec'])} "
            f"msgs={m['user_msg_count']} "
            f"tools={sum(m['tool_counts'].values())} "
            f"cost=${(m['token_usage'] or {}).get('total_cost', 0):.2f}"
        )
    agg = aggregate_day(ms)
    print(
        f"\nTOTAL sessions={agg['session_count']} "
        f"msgs={agg['user_msg_count']} "
        f"cost=${agg['total_cost']:.2f}"
    )
    for p, s in sorted(agg["by_project_seconds"].items(), key=lambda x: -x[1]):
        print(f"  {p}: {fmt_duration(s)}")
