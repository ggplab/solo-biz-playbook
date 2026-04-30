# Agent-Neutral Workspace Guide

> 목적: Claude, Codex, Gemini CLI, 사내 에이전트 등 어떤 도구가 붙어도 같은 업무를 수행하도록 만드는 워크스페이스 운영 가이드입니다. 핵심은 특정 모델의 설정 파일에 지식을 묻어두지 않고, 사람이 관리하는 공용 문서를 SSOT(single source of truth)로 두는 것입니다.

---

## 1. 기본 원칙

### 모델이 아니라 워크스페이스에 지식을 둔다

에이전트별 설정 파일은 다르게 생겼습니다. 예를 들어 Claude Code는 `CLAUDE.md`, Codex는 `AGENTS.md`나 자체 설정을 읽을 수 있습니다. 하지만 업무 규칙, 경로, 인증 방식, 유틸리티 사용법을 각 파일에 복붙하면 곧바로 드리프트가 생깁니다.

권장 구조는 다음과 같습니다.

```text
workspace/
├── AGENT_GUIDE.md          # 환경·인프라 지도: 모든 에이전트가 읽는 기준 문서
├── UTILITIES.md            # 재사용 스크립트·스킬·템플릿 인덱스
├── scripts/                # 실제 로직이 들어 있는 공용 실행체
├── templates/              # 새 프로젝트·문서·환경 파일 템플릿
├── adapters/
│   ├── claude/             # Claude Code용 얇은 포인터
│   ├── codex/              # Codex용 얇은 포인터
│   └── other-agent/        # 다른 에이전트용 얇은 포인터
└── projects/
```

에이전트별 파일에는 “무엇을 언제 읽을지”만 둡니다. 실제 규칙과 로직은 `AGENT_GUIDE.md`, `UTILITIES.md`, `scripts/`에 둡니다.

### 공용 엔진과 얇은 어댑터를 분리한다

에이전트가 달라도 Bash, Python, Node, HTTP API는 대부분 동일하게 실행할 수 있습니다. 따라서 업무 로직은 공용 스크립트로 만들고, 에이전트별 스킬이나 명령은 그 스크립트를 호출하는 얇은 래퍼로 둡니다.

```text
[공용 엔진]                         [에이전트별 어댑터]
scripts/worklog_calendar.py   <-    adapters/claude/worklog.md
scripts/gmail_draft.py        <-    adapters/codex/email-draft.md
scripts/md_to_pdf.py          <-    adapters/other-agent/md-to-pdf.md
```

이 구조를 따르면 새 모델이나 새 CLI를 도입해도 전체 시스템을 다시 만들 필요가 없습니다. 포인터만 하나 더 만들면 됩니다.

---

## 2. `AGENT_GUIDE.md`에 들어갈 내용

`AGENT_GUIDE.md`는 “새 에이전트가 이 워크스페이스에 들어왔을 때 가장 먼저 읽는 지도”입니다. 개인 계정명이나 실제 토큰값은 넣지 않고, 변수명과 사용 원칙만 기록합니다.

권장 목차:

```markdown
# Agent Guide

## 1. Environment
- OS:
- Shell:
- Default workspace root:
- Runtime versions:
- Package managers:

## 2. Credential Policy
- Global secrets live in the user shell profile or a secret manager.
- Project `.env` files contain only project-specific values.
- Never paste global tokens into repositories.

| Variable | Purpose | Where it is used |
|---|---|---|
| `SERVICE_API_KEY` | External service API | scripts/service_*.py |
| `WORKLOG_CALENDAR_ID` | Calendar target | scripts/worklog_calendar.py |

## 3. Tool Map
| Tool | Purpose | Auth method | Verification command |
|---|---|---|---|
| `gh` | GitHub operations | local keyring | `gh auth status` |
| `supabase` | Supabase operations | env token | `supabase --version` |

## 4. Project Registry
| Project | Purpose | Status | Notes |
|---|---|---|---|
| `example-project` | Customer-facing app | active | public-safe note |

## 5. Workspace Layout
Describe stable directories and naming conventions.

## 6. New Project Checklist
List the repeatable setup steps.

## 7. Operational Rules
Document retry budgets, dry-run rules, path safety, and data handling rules.
```

### 비식별화 기준

- 실제 API 키, DB ID, 캘린더 ID, 이메일 주소를 기록하지 않습니다.
- 개인 이름, 고객명, 미공개 프로젝트명은 역할 기반 이름으로 바꿉니다.
- 로컬 절대경로는 `$HOME/workspace` 같은 플레이스홀더로 바꿉니다.
- 공개 가능한 저장소명도 필요 없으면 `content-hub`, `automation-tools`처럼 범주명으로 바꿉니다.
- 인증 여부는 “keyring 인증”, “환경변수 인증”처럼 방식만 적습니다.

---

## 3. 에이전트별 포인터 파일

각 에이전트가 자동으로 읽는 파일은 SSOT를 가리키는 역할만 합니다.

### Claude Code 예시

```markdown
# CLAUDE.md

먼저 다음 공용 문서를 읽고 따르세요.

- `AGENT_GUIDE.md`
- `UTILITIES.md`

프로젝트별 예외만 이 파일에 기록합니다. 공용 규칙을 이 파일에 복사하지 않습니다.
```

### Codex 예시

```markdown
# AGENTS.md

Before working, read:

- `AGENT_GUIDE.md`
- `UTILITIES.md`

Keep model-specific instructions here minimal. Shared operating rules belong in the guide files above.
```

### 다른 에이전트 예시

```markdown
# Agent Adapter

1. Read `AGENT_GUIDE.md`.
2. Search `UTILITIES.md` before creating new scripts.
3. Use `scripts/` for executable logic.
4. Add only adapter-specific trigger rules here.
```

---

## 4. 운영 규칙 템플릿

### Retry budget

동일 원인으로 3회 연속 실패하면 멈추고 다음을 보고합니다.

1. 지금까지 시도한 것
2. 각 실패 원인
3. 가능한 대안 2~3개

같은 방향으로 무제한 재시도하지 않습니다.

### Dry-run first

새 자동화, 배포, 외부 API 쓰기 작업은 먼저 dry-run을 보여줍니다.

필수 포함 항목:

- 실제 입력값과 파라미터
- 샘플 입력과 기대 출력
- 실패 시 롤백 또는 재시도 전략

### Path safety

쓰기 전에 대상 디렉토리를 확인합니다. 현재 쉘의 작업 디렉토리 자체를 이동, 삭제, 이름 변경하지 않습니다. iCloud, Dropbox, 외부 마운트처럼 동기화되는 경로는 특히 보수적으로 다룹니다.

### Data handling

수집·분석 자동화에서는 추정값을 실제 데이터처럼 채우지 않습니다. 수집 실패, 누락, API 제한은 결과물에 명시합니다.

### Python environment

새 Python 프로젝트는 하나의 표준만 사용합니다. 예를 들어 팀이 `uv`를 표준으로 정했다면 다음처럼 고정합니다.

```bash
uv venv .venv
source .venv/bin/activate
uv pip install package==x.y.z
```

에이전트마다 `venv`, `conda`, 시스템 `pip`를 섞기 시작하면 재현성이 깨집니다.

---

## 5. 새 프로젝트 체크리스트

```bash
mkdir "$HOME/workspace/my-project"
cd "$HOME/workspace/my-project"
cp "$HOME/workspace/shared/templates/.env.example" .env
cp "$HOME/workspace/shared/templates/AGENTS.md" AGENTS.md
git init
```

체크리스트:

- 프로젝트 이름은 `kebab-case`로 통일합니다.
- 글로벌 토큰은 프로젝트 `.env`에 복사하지 않습니다.
- 프로젝트 고유값만 `.env`에 둡니다.
- 첫 커밋 전에 `.gitignore`가 비밀 파일을 막는지 확인합니다.
- `AGENT_GUIDE.md`와 `UTILITIES.md`에 새 프로젝트 또는 유틸리티를 등록합니다.

---

## 6. 안티패턴

| 안티패턴 | 문제 | 대안 |
|---|---|---|
| Claude 전용 스킬에 업무 로직 전체를 작성 | Codex나 다른 에이전트가 재사용 불가 | `scripts/`에 로직을 두고 Claude 스킬은 포인터만 둠 |
| Codex 전용 프롬프트에 프로젝트 규칙을 복붙 | 규칙 드리프트 발생 | 공용 `AGENT_GUIDE.md`를 참조 |
| `.env`에 글로벌 토큰을 매번 복사 | 유출·폐기 비용 증가 | 셸 프로필 또는 secret manager 사용 |
| Notion DB ID, 캘린더 ID를 공개 문서에 그대로 기록 | 비식별화 실패 | 역할명과 변수명만 기록 |
| 새 에이전트 도입 때마다 자동화를 새로 작성 | 유지보수 비용 증가 | 공용 엔진 + 얇은 어댑터 구조 유지 |

---

## 7. 목표 상태

좋은 모델 비종속 워크스페이스는 다음 조건을 만족합니다.

- 새 에이전트가 와도 첫 5분 안에 환경 지도를 읽고 작업을 시작할 수 있습니다.
- 업무 로직은 특정 모델의 프롬프트 파일이 아니라 테스트 가능한 스크립트에 있습니다.
- 에이전트별 차이는 “트리거 방식”과 “컨텍스트 주입 방식”에만 남습니다.
- 비밀값, 개인 식별 정보, 고객 정보는 공개 문서와 저장소에 들어가지 않습니다.
- 유틸리티를 만들기 전에 기존 레지스트리를 검색하는 습관이 있습니다.
