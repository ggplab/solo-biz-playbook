# Publishing Structure

> GitHub 저장소 메인 대신 Threads, 블로그, 뉴스레터에서 바로 공유하기 좋은 링크 구조입니다.

## 권장 구조

```text
solo-biz-playbook/
├── README.md                         # 전체 지도: 처음 온 사람용
├── docs/
│   ├── README.md                     # 원칙·해설 문서 지도
│   ├── strategy-design/
│   │   └── README.md                 # 전략 설계 모듈 랜딩
│   ├── principles/
│   │   └── README.md                 # 반복 의사결정 원칙 랜딩
│   ├── operations-telemetry/
│   │   └── README.md                 # 운영 계측 모듈 랜딩
│   ├── claude-monthly-review/
│   │   └── README.md                 # Claude Monthly Review 랜딩
│   ├── agent-systems/
│   │   └── README.md                 # 에이전트 운영 랜딩
│   └── diagrams/
├── examples/
│   ├── README.md                     # 실제 사례 모음
│   ├── my-canvas.md
│   └── monthly-claude-review/
│       └── README.md                 # Claude Monthly Review 사례 랜딩
├── template/
│   └── README.md                     # 복사해서 쓰는 양식 모음
└── automation/
    ├── README.md                     # 실행 자동화 지도
    └── claude-worklog/
        └── README.md                 # 자동화 구현 예시 랜딩
```

## 디렉토리 역할

| 디렉토리 | 역할 | 넣는 것 | 넣지 않는 것 |
|---|---|---|---|
| `docs/` | 설명과 원칙 | 운영 원칙, 에이전트 시스템 가이드, 구조도 | 실제 사용 사례 원문, 실행 스크립트 |
| `examples/` | 공개 사례 | 익명화된 완성본, 샘플 보고서, 이미지 예시 | 빈 양식, 비공개 원본 |
| `template/` | 복사용 양식 | 빈 캔버스, 체크리스트, 보고서 틀 | 특정 개인의 실제 수치 |
| `automation/` | 실행 예시 | 스크립트, hook 설정 예시, 설치 방법 | 원칙 설명만 있는 문서 |

## 링크 전략

| 글의 주제 | 공유할 링크 | 이유 |
|---|---|---|
| 전체 저장소 소개 | [`README.md`](../README.md) | 처음 온 사람이 전체 지도를 봐야 할 때 |
| 문서 묶음 전체 | [`docs/README.md`](README.md) | 원칙과 해설 문서의 상위 지도가 필요할 때 |
| "내 사업을 한 장으로 정리하는 법" | [`docs/strategy-design/README.md`](strategy-design/) | 사례, 이미지, 템플릿을 같은 흐름으로 보여줄 때 |
| "바로 따라 쓸 양식" | [`template/README.md`](../template/) | 복사 가능한 템플릿만 전달하고 싶을 때 |
| "일을 받을지 말지 판단하는 기준" | [`docs/principles/README.md`](principles/) | 원칙별 링크를 한 화면에 모아야 할 때 |
| "프로젝트별 시간을 자동으로 재는 법" | [`docs/operations-telemetry/README.md`](operations-telemetry/) | 시간 계측 구조와 구현 예시를 함께 보여줄 때 |
| "AI 에이전트 운영 체계" | [`docs/agent-systems/README.md`](agent-systems/) | 모델 비종속 운영 가이드를 보여줄 때 |
| "Claude Max 월간 사용 복기" | [`docs/claude-monthly-review/README.md`](claude-monthly-review/) | 정량 리뷰 구조와 예시 보고서를 함께 보여줄 때 |
| 자동화 묶음 전체 | [`automation/README.md`](../automation/) | 실행 가능한 자동화 목록을 먼저 보여줄 때 |
| "워크로그 자동화" | [`automation/claude-worklog/README.md`](../automation/claude-worklog/) | 구현 방법과 스크립트를 보여줄 때 |

## README 작성 패턴

각 디렉토리의 README는 같은 틀을 유지합니다.

1. 한 줄 목적: 이 폴더가 해결하는 문제를 먼저 씁니다.
2. 다이어그램: Mermaid 또는 PNG로 자료 간 관계를 보여줍니다.
3. 링크 표: 핵심 파일, 용도, 읽는 순서를 표로 정리합니다.
4. 공개 원칙: 익명화, 비밀값 제거, 모델 비종속성 기준을 짧게 반복합니다.
5. 다음 행동: 복사, 읽기, 실행 중 하나로 끝냅니다.

GitHub에서는 `README.md`가 디렉토리 첫 화면에 자동 렌더링됩니다. 파일명은 `readmd.md`가 아니라 `README.md`로 통일해야 합니다.
