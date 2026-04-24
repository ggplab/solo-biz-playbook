"""
업무일지의 자동 영역과 사용자 수동 메모 영역을 분리하는 헬퍼.

자동 갱신은 마커 사이만 갱신해 사용자 수동 메모를 보존한다.
- AUTO:START / AUTO:END  : write_worklog.py가 매번 덮어쓰는 영역
- 마커 밖의 모든 텍스트  : 사용자 수동 편집 영역, 절대 건드리지 않음

새 파일은 자동 영역만 채우고 그 아래에 빈 수동 메모 섹션을 둔다.
"""

from __future__ import annotations

import re
from pathlib import Path

AUTO_START = "<!-- AUTO:START -->"
AUTO_END = "<!-- AUTO:END -->"

_AUTO_BLOCK_RE = re.compile(
    rf"{re.escape(AUTO_START)}.*?{re.escape(AUTO_END)}",
    flags=re.DOTALL,
)

MANUAL_HEADER = "## 메모 (수동 편집 영역)"
MANUAL_PLACEHOLDER = "_여기에 작성한 내용은 일지 자동 갱신 시 보존됩니다._\n"


def wrap_auto(content: str) -> str:
    """auto 콘텐츠를 마커로 감싼다."""
    return f"{AUTO_START}\n{content.rstrip()}\n{AUTO_END}"


def upsert_auto_section(file_path: Path, auto_content: str) -> str:
    """
    파일이 있으면 마커 사이만 교체, 없으면 새로 만든다.
    교체 결과 텍스트를 반환한다 (테스트/디버그 용).
    """
    new_block = wrap_auto(auto_content)

    if not file_path.exists():
        text = (
            f"{new_block}\n\n---\n\n"
            f"{MANUAL_HEADER}\n\n{MANUAL_PLACEHOLDER}"
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")
        return text

    original = file_path.read_text(encoding="utf-8")

    if AUTO_START in original and AUTO_END in original:
        updated = _AUTO_BLOCK_RE.sub(lambda _m: new_block, original, count=1)
    else:
        # 마커 없는 기존 파일: 자동 영역을 맨 위에 prepend, 기존 내용은 수동 영역으로 보존
        updated = (
            f"{new_block}\n\n---\n\n"
            f"{MANUAL_HEADER}\n\n"
            f"{original.lstrip()}"
        )

    file_path.write_text(updated, encoding="utf-8")
    return updated


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "test.md"

        # 1) 신규 파일
        upsert_auto_section(f, "# auto v1\n자동 v1\n")
        t1 = f.read_text(encoding="utf-8")
        assert AUTO_START in t1 and AUTO_END in t1
        assert MANUAL_HEADER in t1

        # 2) 사용자가 수동 메모 추가
        with f.open("a", encoding="utf-8") as h:
            h.write("\n오늘 주의: 무기가되는스토리 프레임 적용\n")

        # 3) 자동 영역 재생성
        upsert_auto_section(f, "# auto v2\n자동 v2 — 다른 내용\n")
        t3 = f.read_text(encoding="utf-8")

        # 자동 영역은 새 콘텐츠로 교체됐어야
        assert "자동 v2" in t3
        assert "자동 v1" not in t3
        # 수동 메모는 살아있어야
        assert "무기가되는스토리 프레임 적용" in t3

        # 4) 마커 없는 기존 파일 마이그레이션
        f2 = Path(td) / "legacy.md"
        f2.write_text("# 옛날 일지\n옛날 내용\n", encoding="utf-8")
        upsert_auto_section(f2, "# auto v1\n새 자동\n")
        t4 = f2.read_text(encoding="utf-8")
        assert "새 자동" in t4 and "옛날 내용" in t4 and AUTO_START in t4

    print("OK")


if __name__ == "__main__":
    _selftest()
