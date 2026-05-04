#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
hook_path="$repo_root/.git/hooks/pre-push"

cat > "$hook_path" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

echo "Running public safety check before push..."
python3 scripts/public_safety_check.py --all
HOOK

chmod +x "$hook_path"
echo "Installed public safety pre-push hook: $hook_path"
