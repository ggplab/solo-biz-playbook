# Utilities Registry Template

> 목적: 여러 AI 에이전트가 같은 유틸리티를 재사용하도록 만드는 인덱스 템플릿입니다. “기능을 다시 만들지 않고 찾아서 쓰게 하는 문서”가 핵심입니다.

---

## 1. 구조

```text
[공용 엔진]                         [에이전트별 어댑터]
shared/scripts/*.py           <-    adapters/claude/skills/*/SKILL.md
shared/scripts/*.mjs          <-    adapters/codex/skills/*/SKILL.md
shared/templates/*            <-    adapters/other-agent/prompts/*.md
```

- `scripts/`: 실제 실행 로직입니다. 에이전트와 무관해야 합니다.
- `templates/`: 이메일, 문서, `.env`, `.gitignore` 같은 반복 자산입니다.
- `adapters/`: 특정 에이전트가 언제 어떤 스크립트를 호출해야 하는지 설명하는 얇은 문서입니다.
- `UTILITIES.md`: 위 자산을 찾기 위한 SSOT 인덱스입니다.

---

## 2. 네이밍 규칙

### 유틸리티 이름

- `domain-verb` 형식의 `kebab-case`를 사용합니다.
- 예: `email-draft`, `pdf-read`, `md-to-pdf`, `worklog-sync`

### 스크립트 파일

- Python은 `snake_case.py`를 사용합니다.
- Node는 `snake_case.mjs` 또는 팀 표준을 따릅니다.
- 스킬명과 스크립트명은 가능하면 1:1로 맞춥니다.

```text
email-draft  ->  scripts/email_draft.py
md-to-pdf    ->  scripts/md_to_pdf.py
worklog-sync ->  scripts/worklog_sync.py
```

### 도메인 접두어

| Prefix | Domain |
|---|---|
| `email-` / `gmail-` | 이메일 작성·검색·발송 |
| `md-` | Markdown 변환·정리 |
| `pdf-` | PDF 읽기·병합·변환 |
| `docx-` | Word 문서 |
| `xlsx-` | 스프레드시트 |
| `slides-` | 프레젠테이션 |
| `gdocs-` / `gcal-` / `gdrive-` | Google Workspace |
| `notion-` | Notion API 워크플로 |
| `worklog-` | 업무일지·세션 계측 |
| `n8n-` | n8n 워크플로 |
| `agent-` | 에이전트 운영 보조 |

---

## 3. 레지스트리 양식

아래 표를 복사해 도메인별로 유지합니다.

```markdown
## Email

| Name | Type | Location | Purpose | Adapter |
|---|---|---|---|---|
| `email_draft.py` | script | `shared/scripts/email_draft.py` | 이메일 초안 생성 | `email-draft` |
| `email_templates.json` | template | `shared/templates/email_templates.json` | 반복 이메일 템플릿 | 모든 에이전트 |
| `email-draft` | adapter | `adapters/claude/skills/email-draft/` | 스크립트 호출 규칙 | Claude |
```

권장 `Type` 값:

- `script`: 실행 가능한 로직
- `template`: 재사용 데이터나 문서 양식
- `adapter`: 에이전트별 포인터
- `workflow`: 여러 스크립트를 묶는 절차
- `reference`: 사용법, API 문서, 예제

---

## 4. 예시 레지스트리

### Document Production

| Name | Type | Location | Purpose | Adapter |
|---|---|---|---|---|
| `md_to_pdf.py` | script | `shared/scripts/md_to_pdf.py` | Markdown을 PDF로 변환 | `md-to-pdf` |
| `pdf_read.py` | script | `shared/scripts/pdf_read.py` | PDF 텍스트 추출·요약 입력 생성 | `pdf-read` |
| `docx_agenda.py` | script | `shared/scripts/docx_agenda.py` | 미팅 아젠다 Word 문서 생성 | `docx-agenda` |
| `document_templates/` | template | `shared/templates/document_templates/` | 문서 스타일·구조 템플릿 | 모든 에이전트 |

### Worklog

| Name | Type | Location | Purpose | Adapter |
|---|---|---|---|---|
| `session_metrics.py` | script | `shared/scripts/session_metrics.py` | 에이전트 세션 로그에서 시간·툴·토큰 지표 추출 | `worklog-sync` |
| `worklog_calendar.py` | script | `shared/scripts/worklog_calendar.py` | 세션 지표를 캘린더에 upsert | `worklog-sync` |
| `write_worklog.py` | script | `shared/scripts/write_worklog.py` | 업무일지 자동 섹션 생성 | `worklog-write` |
| `worklog_markers.py` | script | `shared/scripts/worklog_markers.py` | 수동 메모 보존용 마커 처리 | 내부 의존성 |

### Agent Utility

| Name | Type | Location | Purpose | Adapter |
|---|---|---|---|---|
| `agent_project_init.py` | script | `shared/scripts/agent_project_init.py` | 새 프로젝트 기본 파일 생성 | `new-project` |
| `agent_commit.md` | adapter | `adapters/claude/skills/commit/` | 커밋 전 점검·메시지 생성 규칙 | Claude |
| `agent_review.md` | adapter | `adapters/codex/skills/review/` | 코드 리뷰 체크리스트 | Codex |

---

## 5. 새 유틸리티 추가 절차

1. `UTILITIES.md`에서 같은 기능이 이미 있는지 검색합니다.
2. 기존 유틸리티로 해결 가능하면 새로 만들지 않고 사용법만 보강합니다.
3. 실행 로직이 있으면 `scripts/`에 둡니다.
4. 에이전트별 호출 규칙은 `adapters/`에 둡니다.
5. `UTILITIES.md`에 한 줄 추가합니다.
6. 비밀값, 개인명, 고객명, 실제 ID가 들어갔는지 확인합니다.
7. 가능하면 dry-run 명령과 최소 테스트 명령을 함께 적습니다.

---

## 6. 어댑터 작성 규칙

어댑터는 짧아야 합니다. 스크립트 사용 조건과 호출 예시만 넣고, 로직은 넣지 않습니다.

좋은 예:

~~~markdown
# email-draft

Use when the user asks to draft or send an email.

Call:

```bash
python shared/scripts/email_draft.py --template proposal-reply --to "$EMAIL"
```

Do not paste API keys into prompts. The script reads credentials from the environment.
~~~

나쁜 예:

```markdown
# email-draft

여기에 이메일 생성 로직, Gmail API 호출 코드, 템플릿 본문, 고객별 예외를 전부 작성한다.
```

나쁜 예는 특정 에이전트에 업무 시스템을 종속시킵니다. 새 에이전트로 옮길 때 같은 로직을 다시 작성해야 합니다.

---

## 7. 공개 저장소용 비식별화 체크리스트

- 실제 이메일 주소를 `user@example.com`으로 바꿨는가?
- 캘린더 ID, Notion DB ID, Supabase ref 같은 실제 식별자를 제거했는가?
- 고객명과 내부 프로젝트명을 역할 기반 이름으로 바꿨는가?
- `$HOME`, `$WORKSPACE_ROOT` 같은 플레이스홀더를 사용했는가?
- `.env.example`에는 값이 아니라 변수명과 설명만 있는가?
- 로그 샘플에 토큰, 세션 ID, 파일 경로, 개인명이 없는가?
- 특정 모델을 “필수”라고 쓰지 않고 “지원 어댑터 중 하나”로 설명했는가?

---

## 8. 판단 기준

새 기능을 만들 때 아래 질문에 모두 답할 수 있어야 합니다.

- 이 로직은 Claude 없이도 실행되는가?
- 이 로직은 Codex 없이도 실행되는가?
- 새 에이전트를 붙일 때 문서 포인터만 추가하면 되는가?
- 테스트 또는 dry-run을 모델 밖에서 실행할 수 있는가?
- 공개 저장소에 올려도 개인 정보나 비밀값이 노출되지 않는가?

하나라도 “아니오”라면 아직 모델 비종속 구조가 아닙니다.
