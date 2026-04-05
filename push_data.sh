#!/bin/bash
# push_data.sh — Копирует свежие CSV/JSON из рабочих папок и пушит в GitHub
# Запускается после fetch_data.py через cron

DASHBOARD_DIR="/data/.openclaw/workspace-coder/analytics-dashboard"
SCOUT_DIR="/data/.openclaw/workspace-coder/scout_dashboard"
SNOVIO_DIR="/data/.openclaw/workspace-coder/snovio_dashboard"
EMAIL_DIR="/data/.openclaw/workspace-coder/email_analytics"
SALES_DIR="/data/.openclaw/workspace-coder/sales_statistics"
WEEKLY_SCOUT_DIR="/data/.openclaw/workspace-coder/weekly_scout_dashboard"

# Копируем данные
cp "$SCOUT_DIR/data/raw.csv"             "$DASHBOARD_DIR/data/scout_raw.csv"
cp "$SNOVIO_DIR/data/parsed.csv"         "$DASHBOARD_DIR/data/snovio_parsed.csv"
cp "$EMAIL_DIR/data/emails_monthly.csv"  "$DASHBOARD_DIR/data/emails_monthly.csv"
cp "$EMAIL_DIR/data/emails_weekly.csv"   "$DASHBOARD_DIR/data/emails_weekly.csv"
cp "$EMAIL_DIR/data/daily_sent_30d.csv"  "$DASHBOARD_DIR/data/daily_sent_30d.csv"
cp "$EMAIL_DIR/data/email_status.json"   "$DASHBOARD_DIR/data/email_status.json"
cp "$EMAIL_DIR/data/outgoing_types_monthly.csv" "$DASHBOARD_DIR/data/outgoing_types_monthly.csv"
cp "$SALES_DIR/data/sales_report.csv"    "$DASHBOARD_DIR/data/sales_report.csv"
cp "$WEEKLY_SCOUT_DIR/data/weekly_report.csv" "$DASHBOARD_DIR/data/weekly_report.csv"

# Пушим если есть изменения
cd "$DASHBOARD_DIR"
git add data/ pages/ Home.py
if ! git diff --cached --quiet; then
    git commit -m "data: $(date +%Y-%m-%d)"
    git push
    echo "✅ Data pushed"
else
    echo "ℹ️ No changes"
fi
