# Examples

> 실제 운영에서 사용한 자료를 공개 가능한 형태로 익명화한 예시 모음입니다.

루트 README는 전체 지도이고, 이 디렉토리는 "실제로 어떻게 생겼는지"를 보여주는 공유용 진입점입니다. Threads나 블로그 글에서는 저장소 메인보다 아래 항목 중 하나를 직접 링크하는 편이 찾기 쉽습니다.

![지지플랩 린캔버스 — 공개판](my-canvas.png)

```mermaid
flowchart LR
  A[1인 사업 운영] --> B[전략 설계]
  A --> C[도구 사용 회계]
  B --> D[my-canvas.md]
  B --> E[my-canvas.png]
  C --> F[monthly-claude-review]
  F --> G[2026-04 anonymized report]
```

## 예시 목록

| 예시 | 위치 | 언제 보면 좋은가 |
|---|---|---|
| 린캔버스 공개판 | [`my-canvas.md`](my-canvas.md), [`my-canvas.png`](my-canvas.png) | 1인 사업의 고객, 문제, 수익 구조를 한 장으로 정리하고 싶을 때 |
| 월간 Claude 사용 복기 | [`monthly-claude-review/`](monthly-claude-review/) | 정액제 AI 도구를 어디에 썼는지 토큰, 비용, 시간 기준으로 회고하고 싶을 때 |

## 전략 설계

린캔버스는 스타터킷의 첫 모듈입니다. 실제 사례로 감을 잡고, 빈 템플릿에 자기 사업을 투영한 뒤, 결과를 한 장 이미지로 시각화해 전략 드리프트를 점검합니다.

핵심 파일:

- [`my-canvas.md`](my-canvas.md) — 실제로 채운 린캔버스
- [`my-canvas.png`](my-canvas.png) — 공개 가능한 이미지 버전
- [`../template/lean-canvas.md`](../template/lean-canvas.md) — 독자가 복사해 쓰는 빈 템플릿

## 도구 사용 회계

Claude Max 같은 정액제 AI 도구는 청구서만 봐서는 실제 사용 가치를 알기 어렵습니다. [`monthly-claude-review/`](monthly-claude-review/)는 토큰, 비용, 세션, 시간, 프로젝트 분포를 월간 단위로 집계해 다음 달의 도구 사용 방식을 조정하는 예시입니다.

## 공개 원칙

- 고객명, 내부 프로젝트명, 실제 계약 조건은 일반화합니다.
- 절대 금액, 식별 가능한 경로, 실제 계정 정보는 제거하거나 마스킹합니다.
- 구조적 수치와 판단 기준은 가능한 한 남겨서 독자가 자기 상황과 비교할 수 있게 합니다.
