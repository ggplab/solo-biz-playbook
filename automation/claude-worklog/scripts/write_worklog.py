"""
업무일지 자동 생성기 (v2)

session_metrics 모듈 기반으로 그날 모든 세션을 정량/시간순으로 정리하고,
Gemini로 narrative 요약을 만들어 Obsidian `업무일지/{date}.md`에 저장한다.

마커(<!-- AUTO:START --> / <!-- AUTO:END -->) 사이만 갱신하므로
사용자가 추가한 수동 메모는 보존된다.

사용법:
  python3 write_worklog.py [project_dir] [--date YYYY-MM-DD] [--backfill N]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_metrics import (
    KST,
    aggregate_day,
    collect_metrics_for_date,
    fmt_duration,
    git_changes_in_window,
    kst_hhmm,
)
from worklog_markers import upsert_auto_section


def _vault_root() -> Path:
    override = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    candidates = [
        Path.home()
        / "Library"
        / "Mobile Documents"
        / "iCloud~md~obsidian"
        / "Documents"
        / "Obsidian Vault",
        Path.home() / "Documents" / "Obsidian Vault",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


VAULT_ROOT = _vault_root()
WORKLOG_DIR = VAULT_ROOT / "업무일지"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


def _format_quant_box(agg: dict, git_totals: dict) -> str:
    lines = ["## 📊 오늘의 숫자\n"]
    if agg["session_count"] == 0:
        lines.append("- 기록된 세션 없음")
        return "\n".join(lines)

    proj_parts = [
        f"{p} {fmt_duration(s)}"
        for p, s in sorted(agg["by_project_seconds"].items(), key=lambda x: -x[1])
    ]
    total_active = sum(agg["by_project_seconds"].values())
    lines.append(
        f"- **활성 시간:** {fmt_duration(total_active)} "
        f"({', '.join(proj_parts)})"
    )
    if agg.get("first_ts") and agg.get("last_ts"):
        lines.append(
            f"- **워크데이:** {kst_hhmm(agg['first_ts'])} → "
            f"{kst_hhmm(agg['last_ts'])}"
        )
    lines.append(
        f"- **세션:** {agg['session_count']}개 / "
        f"**메시지:** {agg['user_msg_count']}개"
    )
    if agg["tool_counts"]:
        top = sorted(agg["tool_counts"].items(), key=lambda x: -x[1])[:5]
        lines.append("- **Tool 호출:** " + ", ".join(f"{k} ×{v}" for k, v in top))
    if git_totals["commits"] or git_totals["files"]:
        lines.append(
            f"- **Git:** {git_totals['commits']} commit / "
            f"{git_totals['files']} files / "
            f"+{git_totals['insertions']} -{git_totals['deletions']}"
        )
    if agg["total_tokens"]:
        lines.append(
            f"- **토큰:** {agg['total_tokens']:,} "
            f"(추정 ${agg['total_cost']:.2f} — Max plan 정액제와 무관)"
        )
    return "\n".join(lines)


def _format_timeline(metrics: list[dict]) -> str:
    if not metrics:
        return "## ⏱ 시간 흐름\n\n- 기록 없음"
    lines = ["## ⏱ 시간 흐름\n"]
    for m in metrics:
        first_msg = m["user_messages"][0]["text"] if m["user_messages"] else "—"
        lines.append(
            f"- **{kst_hhmm(m['first_ts'])}–{kst_hhmm(m['last_ts'])}** "
            f"`[{m['project']}]` {fmt_duration(m['duration_sec'])} · "
            f"{first_msg[:80]}"
        )
    return "\n".join(lines)


def _format_by_project(metrics: list[dict]) -> str:
    if not metrics:
        return ""
    by_proj: dict[str, list[dict]] = {}
    for m in metrics:
        by_proj.setdefault(m["project"], []).append(m)

    lines = ["## 🗂 프로젝트별 작업\n"]
    proj_order = sorted(
        by_proj.items(),
        key=lambda kv: -sum(m["duration_sec"] for m in kv[1]),
    )
    for proj, ms in proj_order:
        total = sum(m["duration_sec"] for m in ms)
        msg_count = sum(m["user_msg_count"] for m in ms)
        lines.append(f"### {proj} — {fmt_duration(total)} · 메시지 {msg_count}개")
        for m in ms:
            lines.append(
                f"- {kst_hhmm(m['first_ts'])}–{kst_hhmm(m['last_ts'])} "
                f"({fmt_duration(m['duration_sec'])}, {m['tool']})"
            )
            for um in m["user_messages"][:3]:
                lines.append(f"    - [{kst_hhmm(um['ts'])}] {um['text'][:160]}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _gemini_narrative(metrics: list[dict], date_str: str) -> dict:
    if not GEMINI_API_KEY or not metrics:
        return {"summary": "", "wins": [], "blockers": [], "next": [], "seeds": []}

    sessions_view = []
    for m in metrics:
        sessions_view.append(
            {
                "time": f"{kst_hhmm(m['first_ts'])}-{kst_hhmm(m['last_ts'])}",
                "project": m["project"],
                "tool": m["tool"],
                "duration": fmt_duration(m["duration_sec"]),
                "messages": [um["text"][:200] for um in m["user_messages"][:5]],
                "tools": dict(
                    sorted(m["tool_counts"].items(), key=lambda x: -x[1])[:5]
                ),
            }
        )

    prompt = f"""
당신은 사용자의 하루 작업 흐름을 narrative로 정리해주는 어시스턴트입니다.

날짜: {date_str}

아래는 그날 진행한 모든 Claude/Codex 세션입니다(시간순). 각 세션의 사용자 메시지를 보고
"무엇을 시도했고, 어떤 흐름으로 진행됐는지"를 사실 기반으로 정리하세요.

세션 데이터:
{json.dumps(sessions_view, ensure_ascii=False, indent=2)}

요구사항:
- 한 줄 요약: 그날의 핵심 활동을 한 문장으로 (사실만, 추측 금지)
- 이긴 것: 실제로 진척된/완료된 일 (불릿 3~5개, 없으면 빈 리스트)
- 막힌 것: 문제·재시도·블로커 (불릿, 없으면 빈 리스트)
- 다음 할 일: 자연스럽게 이어질 후속 작업 (불릿 2~3개)
- 콘텐츠 씨앗: 사용자가 한 질문/막힌 지점 중 강의·블로그·SNS 소재가 될 만한 인사이트 1~2개

**JSON으로만 답하세요. 다른 텍스트 금지.**
{{
  "summary": "...",
  "wins": ["..."],
  "blockers": ["..."],
  "next": ["..."],
  "seeds": ["..."]
}}
"""

    try:
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }
        ).encode()
        req = urllib.request.Request(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(text)
    except Exception as e:
        print(f"[Gemini 오류] {e}", file=sys.stderr)
        return {
            "summary": f"{date_str}에 {len(metrics)}개 세션을 진행했습니다.",
            "wins": [],
            "blockers": [],
            "next": [],
            "seeds": [],
        }


def _format_narrative(narr: dict) -> str:
    def _bullets(items: list[str], placeholder: str = "—") -> str:
        if not items:
            return f"- {placeholder}"
        return "\n".join(f"- {x}" for x in items)

    lines = []
    lines.append("## 🧭 한 줄 요약\n")
    lines.append(f"> {narr.get('summary', '—')}")
    lines.append("\n## ✅ 이긴 것\n")
    lines.append(_bullets(narr.get("wins", [])))
    lines.append("\n## ⚠️ 막힌 것\n")
    lines.append(_bullets(narr.get("blockers", []), placeholder="없음"))
    lines.append("\n## 🎯 다음 할 일\n")
    lines.append(
        "\n".join(f"- [ ] {x}" for x in narr.get("next", [])) or "- [ ] —"
    )
    lines.append("\n## 🌱 콘텐츠 씨앗\n")
    lines.append(_bullets(narr.get("seeds", [])))
    return "\n".join(lines)


def _aggregate_git(metrics: list[dict], date_str: str) -> dict:
    """세션별 cwd 단위로 git 변경량 합산. 같은 repo 중복 카운트 방지."""
    seen_repos = set()
    totals = {"commits": 0, "insertions": 0, "deletions": 0, "files": 0}
    if not metrics:
        return totals
    day_start = dt.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
    day_end = day_start + dt.timedelta(days=1)
    for m in metrics:
        repo = m.get("project_dir")
        if not repo or repo in seen_repos:
            continue
        seen_repos.add(repo)
        ch = git_changes_in_window(repo, day_start, day_end)
        for k, v in ch.items():
            totals[k] += v
    return totals


def build_auto_section(date_str: str, metrics: list[dict]) -> str:
    agg = aggregate_day(metrics)
    git_totals = _aggregate_git(metrics, date_str)
    narr = _gemini_narrative(metrics, date_str)

    parts = [
        f"# {date_str} 업무일지\n",
        "_자동 생성 영역. 수동 편집은 아래 메모 섹션에 작성하세요._\n",
        _format_quant_box(agg, git_totals),
        "",
        _format_narrative(narr),
        "",
        _format_timeline(metrics),
        "",
        _format_by_project(metrics),
    ]
    return "\n".join(p for p in parts if p)


def write_for_date(date_str: str) -> Path:
    metrics = collect_metrics_for_date(date_str)
    auto = build_auto_section(date_str, metrics)
    target = WORKLOG_DIR / f"{date_str}.md"
    upsert_auto_section(target, auto)
    print(f"[업무일지] {target} ({len(metrics)} sessions)")
    return target


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("project_dir", nargs="?", default=os.getcwd())
    p.add_argument("--date", default=None)
    p.add_argument("--backfill", type=int)
    p.add_argument("--force", action="store_true")
    args, _ = p.parse_known_args()

    if not sys.stdin.isatty():
        try:
            sys.stdin.read()
        except Exception:
            pass

    if args.backfill:
        today = dt.date.today()
        for i in range(args.backfill - 1, -1, -1):
            d = (today - dt.timedelta(days=i)).isoformat()
            write_for_date(d)
        return

    target_date = args.date or dt.date.today().isoformat()
    write_for_date(target_date)


if __name__ == "__main__":
    main()
