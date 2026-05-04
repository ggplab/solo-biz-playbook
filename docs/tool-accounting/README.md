# Tool Accounting

> Claude Max 같은 정액제 AI 도구를 어디에 썼는지 월간 단위로 집계·복기하는 모듈입니다.

시간 회계가 워크로그라면, 도구 사용 회계는 AI 도구에 쓴 토큰, 비용, 세션, 시간, 프로젝트 분포를 보는 월간 리뷰입니다. 청구서가 아니라 실제 사용 패턴을 기준으로 다음 달의 도구 사용 방식을 조정합니다.

```mermaid
flowchart TD
  A[AI 도구 사용] --> B[세션 로그]
  A --> C[빌트인 insights]
  B --> D[토큰·비용·시간 집계]
  C --> E[정성 패턴]
  D --> F[월간 도구 사용 보고서]
  E --> F
  F --> G[다음 달 효율화 액션]
```

## 핵심 파일

| 항목 | 위치 | 쓰임 |
|---|---|---|
| 월간 리뷰 예시 | [`../../examples/monthly-claude-review/`](../../examples/monthly-claude-review/) | Claude Max 사용량을 익명화해서 공개한 보고서와 워크플로 |
| 2026-04 보고서 | [`../../examples/monthly-claude-review/2026-04-anonymized.md`](../../examples/monthly-claude-review/2026-04-anonymized.md) | 첫 달 실제 보고서의 공개 가능 버전 |
| 운영 계측 | [`../operations-telemetry/`](../operations-telemetry/) | 시간 회계와 도구 사용 회계를 연결하는 기반 |

## 읽는 순서

1. 이 문서에서 도구 사용 회계의 위치를 봅니다.
2. [`../../examples/monthly-claude-review/`](../../examples/monthly-claude-review/)에서 보고서 구조와 자동화 흐름을 확인합니다.
3. 자기 결제일 기준으로 월간 집계 기간을 정합니다.
4. 다음 달에 줄일 마찰과 유지할 고효율 사용 패턴을 액션으로 남깁니다.
