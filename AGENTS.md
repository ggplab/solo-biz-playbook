# AGENTS.md

This repository is a public playbook. Keep all changes public-safe, model-neutral, and free of secrets or private customer data.

## Read First

- `README.md` for repository purpose and structure
- `docs/agent-systems/agent-guide.md` for model-neutral agent workspace principles
- `docs/agent-systems/utilities-registry.md` before adding reusable automation or scripts

## Working Rules

- Do not encode workflow knowledge only in a Claude, Codex, or other model-specific file.
- Put reusable execution logic in scripts or documented templates, then add thin model-specific adapters only when necessary.
- Use placeholders for private identifiers: `user@example.com`, `$HOME/workspace`, `SERVICE_API_KEY`, `WORKLOG_CALENDAR_ID`.
- Do not commit actual API keys, calendar IDs, database IDs, private repo names, customer names, or local absolute paths.
- Prefer examples that can run without a specific AI model. If a model-specific feature is mentioned, describe it as one adapter option.

## Project Notes

- Core public materials live in `examples/`, `template/`, and `docs/principles/`.
- Agent-system materials live in `docs/agent-systems/`.
- The worklog automation in `automation/claude-worklog/` is an implementation example; keep its documentation framed so the pattern can be adapted to other agents.
