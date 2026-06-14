#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG="$PROJECT_DIR/scripts/update.log"

echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "$LOG"

# 1. Update all generated sport data files
"$PROJECT_DIR/.venv/bin/python" "$SCRIPT_DIR/update_all_data.py" >> "$LOG" 2>&1
SPORTS_EXIT=$?
echo "update_all_data.py exit: $SPORTS_EXIT" >> "$LOG"

# 2. Commit and push if file changed
cd "$PROJECT_DIR"
if ! git diff --quiet data.js *_data.js; then
  git add data.js *_data.js >> "$LOG" 2>&1
  git commit -m "Update sports data $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
  git push >> "$LOG" 2>&1
  PUSH_EXIT=$?
  echo "git push exit: $PUSH_EXIT" >> "$LOG"
else
  echo "No generated data changes, skipping commit." >> "$LOG"
fi

# 3. Send newsletter email (if script exists and env var set)
if [ -f "$SCRIPT_DIR/send_newsletter.py" ] && [ -n "$GMAIL_APP_PASSWORD" ]; then
  "$PROJECT_DIR/.venv/bin/python" "$SCRIPT_DIR/send_newsletter.py" >> "$LOG" 2>&1
  echo "send_newsletter.py exit: $?" >> "$LOG"
fi

# 4. Send Glory digest (lee .env por su cuenta; solo envía si hay hechos nuevos)
if [ -f "$SCRIPT_DIR/send_glory_email.py" ]; then
  "$PROJECT_DIR/.venv/bin/python" "$SCRIPT_DIR/send_glory_email.py" >> "$LOG" 2>&1
  echo "send_glory_email.py exit: $?" >> "$LOG"
fi

echo "Done." >> "$LOG"
