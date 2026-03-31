"""
status_app.py — Sales Email Status Dashboard
Отображает структуру email-аккаунтов сэйлзов и их статус доступности.
"""
import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="Sales Email Status",
    page_icon="🔍",
    layout="wide"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "email_status.json")

# Структура аккаунтов (зеркалит fetch_data.py)
WORKSPACE_ACCOUNTS = {
    "Джеля": [
        "emily@fansy.cz",
        "katrin@fansy.cz",
        "emily@inperson.agency",
        "sophia@inperson-group.com",
    ],
    "Настя": [
        "annie@inperson.agency",
        "annie@inperson-group.com",
    ],
    "Ксения": [
        "amelia@inperson-group.com",
    ],
}

GMAIL_ACCOUNTS = {
    "Джеля": [
        "milukovasofia457@gmail.com",
        "aalexantoos@gmail.com",
        "gachakeril@gmail.com",           # snovio
        "mijaresenely523@gmail.com",       # snovio
        "klavarossi@gmail.com",
    ],
    "Настя": [
        "annwalkmanmgmt@gmail.com",
        "walkman.annie@gmail.com",         # snovio
        "annie.applin@gmail.com",          # snovio
        "ann.gruv@gmail.com",
        "tammy.melloww@gmail.com",
        "oliviamerrickson@gmail.com",
    ],
    "Ксения": [
        "roksiblackfansy@gmail.com",
        "roxanawinterhold@gmail.com",
        "roxanabarnum@gmail.com",
        "blueskyroxana@gmail.com",         # snovio
        "woodenwarekristian@gmail.com",    # snovio
    ],
}

SNOVIO_EMAILS = {
    "gachakeril@gmail.com",
    "mijaresenely523@gmail.com",
    "walkman.annie@gmail.com",
    "annie.applin@gmail.com",
    "blueskyroxana@gmail.com",
    "woodenwarekristian@gmail.com",
}


def load_status():
    if not os.path.exists(STATUS_FILE):
        return {}
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def status_icon(status):
    if status == "ok":
        return "✅"
    elif status == "error":
        return "❌"
    elif status == "no_token":
        return "⚠️"
    return "⬜"


def format_time(time_str):
    """Форматирует время в читаемый вид с указанием давности."""
    if not time_str:
        return "—"
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            ago = f"{diff.days}д назад"
        elif diff.seconds >= 3600:
            ago = f"{diff.seconds // 3600}ч назад"
        elif diff.seconds >= 60:
            ago = f"{diff.seconds // 60}м назад"
        else:
            ago = "только что"
        
        return f"{dt.strftime('%d.%m.%Y %H:%M')} ({ago})"
    except Exception:
        return time_str


st.title("🔍 Sales Email Status")

status_data = load_status()

if not status_data:
    st.warning("📭 Статусы пока не собраны. Они появятся после следующего запуска сбора данных (крон: ежедневно 07:00 Berlin).")

# Общая статистика
total = 0
ok_count = 0
error_count = 0
no_token_count = 0

all_accounts = {}
for sales, emails in WORKSPACE_ACCOUNTS.items():
    for email in emails:
        all_accounts[email] = {"sales": sales, "type": "workspace"}
for sales, emails in GMAIL_ACCOUNTS.items():
    for email in emails:
        all_accounts[email] = {"sales": sales, "type": "gmail"}

for email in all_accounts:
    total += 1
    s = status_data.get(email, {}).get("status", "unknown")
    if s == "ok":
        ok_count += 1
    elif s == "error":
        error_count += 1
    elif s == "no_token":
        no_token_count += 1

# Метрики
col1, col2, col3, col4 = st.columns(4)
col1.metric("Всего аккаунтов", total)
col2.metric("Доступно", ok_count, delta=None)
col3.metric("Ошибки", error_count, delta=None)
col4.metric("Нет токена", no_token_count, delta=None)

# Время последнего обновления
last_checks = [status_data[e].get("last_check") for e in status_data if status_data[e].get("last_check")]
if last_checks:
    latest = max(last_checks)
    st.caption(f"🕐 Последнее обновление статусов: **{format_time(latest)}**")

st.divider()

# По каждому сэйлзу
for sales_name in sorted(set(list(WORKSPACE_ACCOUNTS.keys()) + list(GMAIL_ACCOUNTS.keys()))):
    st.subheader(f"👤 {sales_name}")
    
    workspace_emails = WORKSPACE_ACCOUNTS.get(sales_name, [])
    gmail_emails = GMAIL_ACCOUNTS.get(sales_name, [])
    
    rows = []
    
    for email in workspace_emails:
        info = status_data.get(email, {})
        rows.append({
            "Статус": status_icon(info.get("status", "unknown")),
            "Email": email,
            "Тип": "🏢 Workspace",
            "Сообщений": info.get("messages_total", "—"),
            "Последняя проверка": format_time(info.get("last_check")),
            "Ошибка": info.get("error") or "—",
        })
    
    for email in gmail_emails:
        info = status_data.get(email, {})
        email_type = "📨 Snovio" if email in SNOVIO_EMAILS else "📩 Gmail"
        rows.append({
            "Статус": status_icon(info.get("status", "unknown")),
            "Email": email,
            "Тип": email_type,
            "Сообщений": info.get("messages_total", "—"),
            "Последняя проверка": format_time(info.get("last_check")),
            "Ошибка": info.get("error") or "—",
        })
    
    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Статус": st.column_config.TextColumn(width="small"),
                "Email": st.column_config.TextColumn(width="medium"),
                "Тип": st.column_config.TextColumn(width="small"),
                "Сообщений": st.column_config.NumberColumn(width="small"),
                "Последняя проверка": st.column_config.TextColumn(width="medium"),
                "Ошибка": st.column_config.TextColumn(width="medium"),
            }
        )
    else:
        st.info("Нет аккаунтов")
    
    st.text("")  # отступ
