# 원칙 04 — 보안 사고 대응 (Supply Chain & Credential)

> "공격은 1년에 한 번이라도, 대응 체계는 매일 작동한다. **검증되지 않은 '점검 도구' 실행이 가장 흔한 두 번째 침해 벡터다.**"

---

## 한 줄 정의

**1인 사업자에게 보안 사고는 매출 손실보다 ID 손실이 더 치명적이다** — 한 번 유출된 GitHub OIDC 토큰, npm publish 토큰, OAuth refresh 토큰은 IP·고객 데이터·결제 자격증명까지 연쇄적으로 노출시킨다. 따라서 보안은:

1. **자동 감시(매일)** + **명시적 대응(사고 발생 시)** 두 트랙으로 분리한다.
2. 사고 시 모든 행동은 **1차 소스로 검증**한 IoC 위에서만 이뤄진다.
3. 행동의 blast radius 순서를 지킨다 — **점검 → 격리 → 정화 → 복구 → 학습**. 역순으로 가지 않는다(예: 증거 없이 토큰부터 전면 회전은 운영을 마비시킨다).

---

## 왜 중요한가

**1인 사업자 위협 모델의 특이점**:

| 위협 | 다인 기업 | 1인 사업자 |
|---|---|---|
| OAuth 토큰 유출 | SRE팀이 자동 회전 | 본인이 모든 서비스 수동 재로그인 → 24h+ 다운타임 |
| npm publish 토큰 | 보안팀 격리 + 강제 회전 | 자기 IP(강의자료·콘텐츠) 재배포 차단 |
| Claude Code/Cursor 후킹 | EDR 탐지 | 모든 AI 워크플로 오염 가능 — 본인 인지 후 7+ 일 |
| 소셜 엔지니어링 (가짜 점검 도구) | 보안 인식 교육 + 승인 절차 | **즉시 실행 충동 + 단독 의사결정** → 가장 큰 리스크 |

**역사적 패턴**: Shai-Hulud (2025-09 → 2025-12 v2 → 2026-05 Mini), TeamPCP 캠페인, PyPI typosquat — npm/PyPI 공급망 공격은 **분기당 1회 이상** 대형 캠페인이 발견된다. "내 시스템엔 안 올 것"은 가정이 아니라 도박.

---

## 5가지 원칙

### P1. 1차 소스 검증 (Primary Source First)

뉴스 헤드라인·전달받은 메시지·SNS 캡처는 **시작점이지 결론이 아니다.** 행동 전에 다음 중 **최소 2곳 독립 1차 소스**로 교차 확인:

- 벤더 보안 블로그: Microsoft Security, Wiz, Snyk, Sophos, Datadog Security Labs, Aikido, StepSecurity, Onapsis, Upwind
- 공식 advisory: GHSA, CVE, vendor security advisory
- 1차 IoC 리포: DataDog `indicators-of-compromise` GitHub repo

**적용 시점**: 사고 첫 5분.

### P2. 검증되지 않은 "점검 도구" 거부 (Refuse Unverified Remedies)

공격 캠페인 자체가 **"감염 점검 도구"를 가장하여** 추가 페이로드를 배포하는 경우가 잦다. 다음은 1차 소스 확인 없이 **절대 실행하지 않는다**:

- `npx <들어본 적 없는-패키지>` ("supply-chain-attack-checker" 류)
- `curl <URL> | sh`, `wget <URL> | bash`
- 사용자가 처음 보는 `pip install <pkg>` 한 줄
- "긴급" 이모지 + "지금 바로" 동시 사용된 행동 지시

**판별 기준**: 1차 소스에서 동일한 명령을 권장하는가? 패키지 maintainer가 누구인가? 출시일은? 그 셋 다 확인 못 하면 실행 거부.

### P3. IoC 기반 점검 (Concrete Indicators Only)

"의심스러우면 다 지운다"는 작전이 아니다. 점검은 항상 다음 5종 IoC를 명시적으로 명단화하고 진행:

| IoC 유형 | 점검 방법 |
|---|---|
| 패키지명 + 버전 | `package.json` 의존성, `node_modules/*/package.json` |
| 파일명 | `find ~ -name "<ioc-filename>"` (예: `router_init.js`, `setup_bun.js`) |
| 고유 문자열 | `grep -r "<campaign-salt>"` (예: `svksjrhjkcejg`) — 단, 본인 검색 로그(`.claude/projects/*.jsonl`)에 해당 문자열이 남으므로 명시적 exclude |
| 네트워크 (도메인/IP) | `pf` log, 방화벽, 네트워크 모니터 |
| 외부 흔적 | GitHub 본인 계정에 알 수 없는 repo (exfil 패턴: "Sha1-Hulud: The Second Coming") |

### P4. Blast Radius 작은 행동 우선 (Smallest Action First)

증거가 명확해질 때까지 **되돌리기 쉬운** 행동만 한다. 행동 위계:

```
[1] 읽기 전용 점검  →  [2] 격리(uninstall, network off)  →  [3] 캐시/패키지 정화
                                                              →  [4] 토큰 회전
                                                                  →  [5] 리포 force-push, 데이터 삭제
```

증거 없이 4·5단계로 점프 = 운영 마비. "확실하지 않으면 1·2단계만". 5단계는 사용자 명시적 승인 + 백업 확인 후에만.

### P5. 자동 감시 ↔ 명시 대응 분리 (Two-Track System)

- **자동 트랙** (`supply-chain-watchdog.py` + launchd): IoC 리스트를 매일 fetch하고 본인 시스템과 대조. AI 개입 없음, 토큰 0. 발견 시 Discord 알림.
- **명시 트랙** (`security-incident-responder` 서브에이전트): 사용자가 뉴스를 봤거나 watchdog 알림을 받았을 때 호출. Web fetch + 시스템 스캔 + 권장 조치. 메인 컨텍스트 보호.

두 트랙을 섞지 않는다. 자동 트랙에 AI를 끼우면 토큰 비용·환각 위험, 명시 트랙을 cron화하면 사고 인지 지연.

---

## 대응 프로세스 (6단계)

NIST SP 800-61 사이클을 1인 사업자 규모로 압축. 다이어그램: [`security-incident-response.html`](../diagrams/security-incident-response.html)

| 단계 | 목적 | 도구 | 결과물 |
|---|---|---|---|
| **D1. Detect** | 발견 | `supply-chain-watchdog.py` (자동), 뉴스/SNS (수동) | Discord 알림 or 사용자 인지 |
| **D2. Triage** | 진위·범위 판단 | `security-incident-responder` 서브에이전트, 1차 소스 fetch | "Confirmed / At-risk / False positive" 분류 |
| **D3. Contain** | 추가 피해 차단 | `npm uninstall`, dev 서버 종료, GitHub Actions 워크플로 비활성, 의심 리포 archive | 침해 확산 정지 |
| **D4. Eradicate** | 흔적 제거 | `rm -rf node_modules`, lockfile 재생성, 알려진 안전 버전 핀, IoC 파일 삭제 | 깨끗한 빌드 환경 |
| **D5. Recover** | 신뢰 자격증명 복구 | GitHub PAT 회전, npm token 회전, Supabase·Notion·Gemini 토큰 회전(필요 시), 사고 기간 commit 재검토 | 정상 운영 재개 |
| **D6. Learn** | 재발 방지 | 이 문서 업데이트, watchdog IoC 리스트 추가, 새 원칙 도출 (필요 시) | 1페이지 회고 노트 |

각 단계는 **이전 단계 완료 확인 후** 진행한다. D2 없이 D5(토큰 회전)로 점프하면 운영만 마비된다.

---

## 체크리스트 — 30분 안 / 24시간 안

### ⏱️ 30분 안 (Triage 종료까지)

- [ ] 위협 캠페인 이름 식별 + 최소 2개 1차 소스로 교차 확인
- [ ] 1차 소스에서 IoC 추출 (패키지 리스트 / 파일명 / 해시 / 문자열 / 네트워크)
- [ ] **사용자(본인)에게 전달된 "점검 도구" 명령이 1차 소스에 있는지** 확인 — 없으면 실행 거부
- [ ] 글로벌 npm 패키지 (`npm ls -g`) + `~/Projects/**/package.json` IoC 매칭
- [ ] IoC 파일 탐색 (`find ~ -name "..."`), 고유 문자열 grep
- [ ] GitHub 본인 계정 exfil repo 검색
- [ ] **Verdict 1줄**: Confirmed / At-risk / Clean

### 🗓️ 24시간 안 (Confirmed인 경우)

- [ ] 침해 패키지 모든 인스턴스 `npm uninstall`
- [ ] 사고 기간(공격 publish 시각 ± 24h) 동안 실행된 CI/CD 워크플로 로그 확인
- [ ] GitHub Actions 토큰 / npm publish 토큰 회전
- [ ] **회전 필요 토큰만** 회전 — 캠페인 IoC와 무관한 토큰(Notion/Supabase/Gemini)은 보류
- [ ] `pull_request_target` 워크플로 점검 (Mini Shai-Hulud 진입 벡터)
- [ ] 사고 기간 git log에서 비정상 commit 확인
- [ ] `~/Projects/solo-biz-playbook/` 1페이지 회고 — 무엇을 다르게 했어야 했나
- [ ] `supply-chain-watchdog.py`에 새 IoC 추가 (아직 자동 fetch 안 되는 항목)

---

## 참고 사례 — Mini Shai-Hulud (2026-05-11)

**타임라인**:
- 5/11 19:20–19:26 UTC: TeamPCP가 `@tanstack/*-router` 등 42개 패키지에 84개 악성 버전 publish
- 5/11–5/12 48h: 172개 unique 패키지 / 403개 악성 버전으로 확산 (@uipath, @mistralai, @opensearch-project, @squawk 등)

**진입 벡터**: TanStack 리포의 `pull_request_target` 워크플로 → 공격자 fork PR이 trigger → GitHub Actions cache poisoning → OIDC 토큰을 `/proc/<pid>/mem`에서 추출 → npm publish.

**위협 특징**:
- 사용자 데이터 100+ 경로(클라우드 / 암호화폐 지갑 / AI 도구 / 메신저) harvest
- Claude Code, VS Code, OS 레벨 persistence hook 설치
- 캠페인 unique salt 사용 (캠페인별 고유 PBKDF2 salt)
- Exfiltration: Session/Oxen 메신저 E2E 업로드 망

**1인 작업자 관점의 핵심 학습**:
1. 전달받은 점검 지시에 가짜 `npx <unfamiliar>` 명령이 포함되는 패턴이 흔하다 — **P2가 작동하지 않으면 점검 행위 자체가 두 번째 침해 벡터**.
2. 로컬 작업 디렉토리는 **자동 백업되지 않는 게 기본**(macOS의 iCloud Drive는 Desktop/Documents만 동기화, `~/Projects/` 같은 경로는 제외). 사고 발생 시 "깨끗한 commit으로 reset 가능한 백업 채널"이 필수 — 작업 디렉토리를 private repo로 즉시 백업하는 일회성 정리 작업이 사후가 아니라 사전에 끝나 있어야 한다.
3. 단일 파일 기반 IoC 스캔(`find` + `grep`)은 home 디렉토리 전체에서 1분 이내 끝난다 → watchdog 매일 실행 비용은 매우 낮다.

---

## 도구 매핑 — 이 원칙을 실제로 작동시키는 코드 (예시 구현)

| 도구 | 역할 | 구현 방식 |
|---|---|---|
| 일일 IoC 스캐너 (`supply-chain-watchdog.py` 등) | 자동 감시 (Detect) | 공용 스크립트 디렉토리에 배치, 1차 소스 IoC CSV를 매일 fetch + 로컬 `package.json` / `node_modules` 대조 |
| 시스템 스케줄러 (launchd · cron · systemd) | 매일 정해진 시각 실행 | OS별 표준 스케줄러로 daemon 등록 |
| 보안 사고 대응 서브에이전트 | Triage·Contain 권고 (메인 AI 컨텍스트 보호) | Claude Code subagent / Cursor agent — 도구는 read-only(Read, Bash, WebFetch, Grep)만 허용, Write 제거 |
| 다이어그램 | 6단계 시각화 | [`../diagrams/security-incident-response.html`](../diagrams/security-incident-response.html) |
| 알림 채널 환경변수 | Discord/Slack webhook URL + 멘션 대상 ID | 글로벌 셸 env에 secret으로 보관, 프로젝트 `.env`에 복붙 금지 |

---

## 이 원칙이 작동하지 않는 케이스

- **0-day 공급망 공격**: 1차 소스 자체가 24–72h 늦게 나옴. P1·P3가 무력. 이 구간은 **방어 불가**로 인정하고 사후 격리에 집중.
- **본인이 직접 만든 악성 코드**: 외부 공격이 아니라 본인 실수로 비밀이 push된 경우. 이 원칙은 외부 공격용. 별도 원칙(아직 미작성) 필요.
- **계정 직접 탈취 (피싱)**: 공급망 IoC가 아닌 phishing 경로. 별도 대응 매뉴얼 영역.

---

## 관련 원칙

- [원칙 01 — 실투입 시급 방어선](01-pricing-floor.md): 사고 대응에도 동일 — "100% 가능성 없으면 큰 행동 안 한다"
- [원칙 02 — 단일 플랫폼 매출 상한](02-platform-concentration.md): GitHub/npm 단일 의존도 위험과 통하는 분산 사고
