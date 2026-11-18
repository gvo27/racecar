#!/bin/sh
# PreToolUse launcher for hw_guard.py: runs it with the project uv .venv python (make dev-setup),
# never the system python3. No .venv => "ask" (fail closed: a hook that cannot start would
# otherwise be a non-blocking error, and the guard would be off).
py="$CLAUDE_PROJECT_DIR/.venv/bin/python"
if [ -x "$py" ]; then
  exec "$py" "$CLAUDE_PROJECT_DIR/.claude/hooks/hw_guard.py"
fi
cat <<'EOF'
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "hw_guard cannot run: .venv/bin/python is missing. Run `make dev-setup` in the repo, then restart Claude Code."}}
EOF
