# Solo Biz Playbook

> 1인 사업자·크리에이터·인디 교육자를 위한 **운영 스타터킷**.

전략을 정리하는 린캔버스, 시간을 실측하는 워크로그, AI 에이전트를 모델 비종속으로 운영하는 가이드를 한 저장소에 묶었습니다. 이론 튜토리얼이 아니라, 실제 1인 사업 운영에서 쓰는 문서·자동화·원칙을 공개 가능한 형태로 정리한 키트입니다.

---

## 왜 만들었나

1인 사업자는 전략, 시간, 도구 운영을 혼자 관리해야 합니다. 문제는 대부분의 자료가 “아이디어를 어떻게 검증할까”에만 머물고, 실제 운영에 필요한 계측과 자동화, AI 도구 사용 규칙까지 연결하지 않는다는 점입니다.

이 레포는 그 공백을 메우기 위한 스타터킷입니다. “무엇을 팔 것인가”를 정리하는 캔버스, “어디에 시간을 썼는가”를 남기는 워크로그, “AI 에이전트가 바뀌어도 같은 업무를 하게 만드는” 운영 가이드를 같은 계층으로 제공합니다.

---

## 구성

| 모듈 | 위치 | 쓰임 |
|---|---|---|
| **전략 설계** | [`examples/my-canvas.md`](examples/my-canvas.md), [`template/lean-canvas.md`](template/lean-canvas.md) | 실제 사례와 빈 템플릿으로 자기 사업의 고객, 문제, 수익 구조를 정리 |
| **의사결정 원칙** | [`docs/principles/`](docs/principles/) | 시급 방어선, 플랫폼 집중도, 부의 사다리처럼 반복 판단에 쓰는 규율 |
| **운영 계측** | [`automation/claude-worklog/`](automation/claude-worklog/) | AI 에이전트 세션을 캘린더·업무일지로 남겨 프로젝트별 투입 시간을 실측 |
| **에이전트 운영** | [`docs/agent-systems/`](docs/agent-systems/) | Claude, Codex 등 특정 모델에 종속되지 않는 공용 문서·스크립트·어댑터 구조 |

---

## 전략 설계

![지지플랩 린캔버스 — 공개판 (절대 금액 영역 모자이크)](examples/my-canvas.png)

> 비용 구조·Profit First 분배·자산 로드맵 절대값 영역은 모자이크 처리됐습니다. 비중·전략·원칙·슬로건은 그대로입니다. 텍스트 상세: [`examples/my-canvas.md`](examples/my-canvas.md)

린캔버스는 스타터킷의 한 모듈입니다. 실제 사례로 감을 잡고, 빈 템플릿에 자기 사업을 투영한 뒤, 결과를 한 장 이미지로 시각화해 전략 드리프트를 점검합니다.

핵심 파일:

- [`examples/my-canvas.md`](examples/my-canvas.md) — 실제로 채운 린캔버스
- [`template/lean-canvas.md`](template/lean-canvas.md) — 독자가 복사해 쓰는 빈 템플릿
- [`docs/principles/`](docs/principles/) — 캔버스에서 추출한 반복 의사결정 원칙

---

## 운영 계측

원칙은 실측 데이터가 있어야 방어됩니다. "시급 N원 밑으로 안 받는다"를 선언이 아니라 숫자로 말하려면, 프로젝트별 누적 시간을 자동으로 찍어주는 계측이 필요합니다.

- [`automation/claude-worklog/`](automation/claude-worklog/) — Claude Code / Codex 세션이 끝날 때마다 Google 캘린더·Obsidian 업무일지에 자동 기록되는 Stop hook 시스템
- 분기 회고 때 프로젝트별 누적 시간을 필터링해서 [원칙 01(시급 방어선)](docs/principles/01-pricing-floor.md)의 실측 근거로 씁니다.

---

## 에이전트 운영

AI 도구는 계속 바뀝니다. 업무 시스템을 특정 모델의 프롬프트 파일에만 넣으면, 모델이나 CLI를 바꿀 때마다 같은 자동화를 다시 만들어야 합니다.

- [`docs/agent-systems/`](docs/agent-systems/) — 모델 비종속 에이전트 운영 문서 묶음
- [`docs/agent-systems/agent-guide.md`](docs/agent-systems/agent-guide.md) — 공용 SSOT 문서와 얇은 에이전트별 어댑터 구조
- [`docs/agent-systems/utilities-registry.md`](docs/agent-systems/utilities-registry.md) — 재사용 스크립트·템플릿·스킬 레지스트리 템플릿

---

## 시작하기

1. [`template/lean-canvas.md`](template/lean-canvas.md)를 복사해 자기 사업의 현재 버전을 작성합니다.
2. [`docs/principles/`](docs/principles/)에서 자기 상황에 맞는 의사결정 기준을 고릅니다.
3. [`automation/claude-worklog/`](automation/claude-worklog/)를 참고해 프로젝트별 투입 시간 계측을 붙입니다.
4. [`docs/agent-systems/`](docs/agent-systems/)를 참고해 AI 에이전트 운영 지식을 특정 모델 밖으로 꺼냅니다.

---

## 린캔버스 시각화

텍스트 린캔버스는 정보 밀도는 높지만 **한눈에 안 들어옵니다**. 완성한 캔버스를 **한 장 이미지**로 만들어 두면:

- 매주 훑어보며 전략 드리프트를 감지하기 쉽다
- 미팅/피칭 때 첨부 자료로 바로 쓸 수 있다
- 동료·멘토에게 피드백 요청할 때 응답률이 높다

### 추천: Claude Code `diagram-design` 스킬

Claude Code에서:

```
/diagram-design
```

후 "내 린캔버스를 9블록 그리드 레이아웃으로 시각화해줘. 색상은 내 브랜드 톤에 맞춰서"라고 요청하면 **인라인 SVG HTML 파일** 한 장이 나옵니다. 편집도 텍스트로 가능합니다.

### 다른 옵션

| 도구 | 장점 | 단점 |
|---|---|---|
| **Notion 데이터베이스 보드** | 블록 편집·링크 연결 쉬움 | 이미지로 내보낼 때 레이아웃 깨짐 |
| **Excalidraw** | 손그림 톤, 자유로움 | Notion 미지원, 공유 시 별도 파일 |
| **Figma / Figjam** | 협업 피드백에 최적 | 1인 사업자에겐 과투자 |
| **공식 Lean Canvas** (leanstack.com) | 원저 양식 | 브랜딩 커스텀 어려움 |

> 개인 경험: Notion에 텍스트 SSOT + 분기마다 한 장짜리 PNG 내보내기 조합이 가장 유지비 낮았습니다.

---

## 누가 만들었나

**임정 / 지지플랩(GGPLab)** — AI × 데이터 × 교육 교차점에서 1인 사업 운영 중. 기업 강의 30회+, 멘토링 400명+ 누적.

- Threads: [@belle_epoque7](https://threads.net/@belle_epoque7)
- LinkedIn: [jayjunglim](https://linkedin.com/in/jayjunglim)
- Homepage: [ggplab.xyz](https://ggplab.xyz)
- 저서: 『n8n이 다해줌』(한빛미디어)

---

## 로드맵

스타터킷 사용 반응을 보고 단계적으로 확장합니다. 계획: [ROADMAP.md](ROADMAP.md)

다음 예정:
- **v1.1** — 원칙 실전 양식 (스크리닝 워크시트·계약 조항·이메일 템플릿·분기 회고 아젠다)
- **v1.2** — 실제 의사결정 로그(ADR) + 변경 이력
- **v1.3** — Profit First·KPI 추적 Google Sheets 연결

## 라이선스 / 기여

- 라이선스: [CC BY-SA 4.0](LICENSE) — 포크·리믹스 환영, 출처 명시·동일 조건 공유
- 기여: [CONTRIBUTING.md](CONTRIBUTING.md) — 자기 린캔버스 익명화 사례 PR 환영합니다. 한국 1인 사업자 캔버스 컬렉션으로 키우고 싶어요.
