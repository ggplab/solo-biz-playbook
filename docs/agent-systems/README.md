# Model-Neutral Agent Systems

특정 AI 모델이나 CLI에 종속되지 않는 업무 시스템을 만들기 위한 문서 묶음입니다.

| Document | Purpose |
|---|---|
| [`agent-guide.md`](agent-guide.md) | 워크스페이스 운영 규칙, 비식별화 기준, 에이전트별 얇은 어댑터 구조 |
| [`utilities-registry.md`](utilities-registry.md) | 재사용 스크립트·템플릿·스킬을 한 곳에서 관리하는 레지스트리 템플릿 |

핵심 원칙은 단순합니다. 업무 로직은 특정 모델의 프롬프트 파일에 넣지 말고, 공용 문서와 실행 가능한 스크립트에 둡니다. Claude, Codex, Gemini CLI 같은 도구별 파일은 그 공용 자산을 가리키는 포인터로만 유지합니다.
