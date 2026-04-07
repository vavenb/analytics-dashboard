"""
app.py — Sales Email Analytics Dashboard

Запуск: streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os
import json
from datetime import datetime, timezone, timedelta

try:
    st.set_page_config(
        page_title="Sales Email Analytics",
        page_icon="📩",
        layout="wide"
    )
except Exception:
    pass

BASE_DIR = os.path.dirname(__file__)
DATA_CANDIDATES = [
    os.path.join(BASE_DIR, "..", "data", "emails_monthly.csv"),
    os.path.join(BASE_DIR, "data", "emails_monthly.csv"),
    os.path.join(os.path.dirname(BASE_DIR), "data", "emails_monthly.csv"),
]
DATA_FILE = next((p for p in DATA_CANDIDATES if os.path.exists(p)), None)


def _csv_mtime():
    """Возвращает время модификации CSV для сброса кэша."""
    if not DATA_FILE:
        return None
    return os.path.getmtime(DATA_FILE)


@st.cache_data(ttl=3600)
def load_data(mtime):
    if not DATA_FILE:
        return pd.DataFrame(columns=["sales", "email", "month", "sent", "received"])
    df = pd.read_csv(DATA_FILE)
    df["sent"] = pd.to_numeric(df["sent"], errors="coerce").fillna(0).astype(int)
    df["received"] = pd.to_numeric(df["received"], errors="coerce").fillna(0).astype(int)
    return df


# Почты для рассылок Snovio — исключаются из основных графиков
SNOVIO_EMAILS = {
    "gachakeril@gmail.com",
    "mijaresenely523@gmail.com",
    "walkman.annie@gmail.com",
    "annie.applin@gmail.com",
    "blueskyroxana@gmail.com",
    "woodenwarekristian@gmail.com",
}

df_all = load_data(_csv_mtime())
df = df_all[~df_all["email"].isin(SNOVIO_EMAILS)] if not df_all.empty else df_all

# --- Шапка ---
st.title("📩 Sales Email Analytics")

TZ_MSK = timezone(timedelta(hours=3))
if DATA_FILE and os.path.exists(DATA_FILE):
    csv_mtime = os.path.getmtime(DATA_FILE)
    csv_updated = datetime.fromtimestamp(csv_mtime, tz=TZ_MSK).strftime("%d.%m.%Y %H:%M")
    st.caption(f"🕐 Данные обновлены: **{csv_updated}**")
else:
    st.error("Не найден файл данных emails_monthly.csv в продовом окружении. Проверь папку analytics-dashboard/data/ и redeploy приложения.")
    st.stop()

st.divider()

# --- Фильтр: диапазон месяцев ---
all_months = sorted(df["month"].unique())
# Убираем полностью пустые месяцы из списка выбора
agg_all = df.groupby("month")[["sent", "received"]].sum()
active_months = sorted(agg_all[(agg_all["sent"] > 0) | (agg_all["received"] > 0)].index.tolist())

if active_months:
    col1, col2 = st.columns(2)
    with col1:
        month_from = st.selectbox("📅 С месяца", active_months, index=0)
    with col2:
        month_to = st.selectbox("📅 По месяц", active_months, index=len(active_months) - 1)

    if month_from > month_to:
        month_from, month_to = month_to, month_from

    df = df[(df["month"] >= month_from) & (df["month"] <= month_to)]

st.divider()

# --- График: Отправлено/получено по месяцам (все аккаунты суммарно) ---
st.subheader("📬 Отправлено и получено писем — по месяцам")
st.caption("Суммарно по всем сэйлзам и аккаунтам")

# Агрегируем по месяцам
monthly = (
    df.groupby("month")[["sent", "received"]]
    .sum()
    .reset_index()
    .sort_values("month")
)

# Убираем месяцы где всё по нулям
monthly = monthly[(monthly["sent"] > 0) | (monthly["received"] > 0)]

fig = go.Figure()

fig.add_trace(go.Bar(
    name="Отправлено",
    x=monthly["month"],
    y=monthly["sent"],
    marker_color="#4A90D9",
    text=monthly["sent"],
    textposition="outside",
))

fig.add_trace(go.Bar(
    name="Получено",
    x=monthly["month"],
    y=monthly["received"],
    marker_color="#50C878",
    text=monthly["received"],
    textposition="outside",
))

fig.update_layout(
    barmode="group",
    height=520,
    xaxis_tickangle=-45,
    yaxis_title="Количество писем",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(b=100, t=60),
)

st.plotly_chart(fig, width="stretch")

with st.expander("📋 Данные по месяцам (таблица)"):
    tbl = monthly.copy()
    tbl.columns = ["Месяц", "Отправлено", "Получено"]
    st.dataframe(tbl, hide_index=True, width="stretch")

# --- График: Отправлено/получено по неделям ---
WEEKLY_FILE = next((p for p in [os.path.join(BASE_DIR, "..", "data", "emails_weekly.csv"), os.path.join(BASE_DIR, "data", "emails_weekly.csv"), os.path.join(os.path.dirname(BASE_DIR), "data", "emails_weekly.csv")] if os.path.exists(p)), os.path.join(BASE_DIR, "..", "data", "emails_weekly.csv"))
if os.path.exists(WEEKLY_FILE):
    st.divider()
    st.subheader("📬 Отправлено и получено писем — по неделям")
    st.caption("Суммарно по всем сэйлзам и аккаунтам")

    @st.cache_data(ttl=3600)
    def load_weekly(mtime):
        wdf = pd.read_csv(WEEKLY_FILE)
        wdf["sent"] = pd.to_numeric(wdf["sent"], errors="coerce").fillna(0).astype(int)
        wdf["received"] = pd.to_numeric(wdf["received"], errors="coerce").fillna(0).astype(int)
        return wdf

    df_weekly = load_weekly(os.path.getmtime(WEEKLY_FILE))

    # Фильтр по месяцам (переводим недели в месяцы для совместимости)
    df_weekly["_month"] = df_weekly["week"].str[:7]
    if active_months:
        df_weekly_filtered = df_weekly[
            (df_weekly["_month"] >= month_from) & (df_weekly["_month"] <= month_to)
        ]
    else:
        df_weekly_filtered = df_weekly

    weekly_agg = (
        df_weekly_filtered.groupby("week")[["sent", "received"]]
        .sum()
        .reset_index()
        .sort_values("week")
    )
    weekly_agg = weekly_agg[(weekly_agg["sent"] > 0) | (weekly_agg["received"] > 0)]

    if not weekly_agg.empty:
        # Форматируем метки: "дд.мм – дд.мм"
        week_labels = []
        for w in weekly_agg["week"]:
            d = pd.Timestamp(w)
            end = d + pd.Timedelta(days=6)
            week_labels.append(f"{d.strftime('%d.%m')}–{end.strftime('%d.%m')}")

        fig_weekly = go.Figure()

        fig_weekly.add_trace(go.Bar(
            name="Отправлено",
            x=week_labels,
            y=weekly_agg["sent"].tolist(),
            marker_color="#4A90D9",
        ))

        fig_weekly.add_trace(go.Bar(
            name="Получено",
            x=week_labels,
            y=weekly_agg["received"].tolist(),
            marker_color="#50C878",
        ))

        fig_weekly.update_layout(
            barmode="group",
            height=520,
            xaxis_tickangle=-45,
            yaxis_title="Количество писем",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                tickmode="array",
                tickvals=week_labels[::4],
                ticktext=week_labels[::4],
            ),
            margin=dict(b=100, t=60),
        )

        st.plotly_chart(fig_weekly, use_container_width=True)

        with st.expander("📋 Данные по неделям (таблица)"):
            tbl_w = pd.DataFrame({
                "Неделя": week_labels,
                "Отправлено": weekly_agg["sent"].tolist(),
                "Получено": weekly_agg["received"].tolist(),
            })
            st.dataframe(tbl_w, hide_index=True, use_container_width=True)

# --- График: Входящие по сэйлзам ---
st.divider()
st.subheader("📥 Входящие письма — по сэйлз-менеджерам")
st.caption("Сумма полученных писем со всех аккаунтов менеджера")

by_sales = (
    df.groupby(["month", "sales"])[["received"]]
    .sum()
    .reset_index()
    .sort_values("month")
)

COLORS = {"Джеля": "#4A90D9", "Настя": "#FF6B6B", "Ксения": "#50C878"}

fig2 = go.Figure()
for name in sorted(by_sales["sales"].unique()):
    subset = by_sales[by_sales["sales"] == name]
    fig2.add_trace(go.Bar(
        name=name,
        x=subset["month"],
        y=subset["received"],
        marker_color=COLORS.get(name, "#888"),
        text=subset["received"],
        textposition="outside",
    ))

fig2.update_layout(
    barmode="group",
    height=520,
    xaxis_tickangle=-45,
    yaxis_title="Получено писем",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(b=100, t=60),
)

st.plotly_chart(fig2, use_container_width=True)

with st.expander("📋 Входящие по сэйлзам (таблица)"):
    pivot = by_sales.pivot(index="month", columns="sales", values="received").fillna(0).astype(int)
    pivot.index.name = "Месяц"
    st.dataframe(pivot, use_container_width=True)

# --- График: Входящие по email-адресам ---
st.divider()
st.subheader("📥 Входящие письма — по email-адресам")
st.caption("Разбивка по отдельным почтовым ящикам")

all_sales_recv = sorted(df["sales"].unique())
selected_sales_recv = st.multiselect(
    "Фильтр по сэйлзу:",
    options=all_sales_recv,
    default=all_sales_recv,
    key="sales_recv_by_email",
)

if selected_sales_recv:
    df_recv_filtered = df[df["sales"].isin(selected_sales_recv)]
    by_email_recv = (
        df_recv_filtered.groupby(["month", "email"])[["received"]]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    by_email_recv = by_email_recv[by_email_recv["received"] > 0]

    if not by_email_recv.empty:
        fig_recv_email = go.Figure()
        for email_addr in sorted(by_email_recv["email"].unique()):
            subset = by_email_recv[by_email_recv["email"] == email_addr]
            fig_recv_email.add_trace(go.Bar(
                name=email_addr,
                x=subset["month"],
                y=subset["received"],
            ))

        fig_recv_email.update_layout(
            barmode="stack",
            height=550,
            xaxis_tickangle=-45,
            yaxis_title="Получено писем",
            legend=dict(orientation="v", x=1.01, y=1, font=dict(size=10)),
            margin=dict(r=200, b=100, t=60),
        )
        st.plotly_chart(fig_recv_email, use_container_width=True)

        with st.expander("📋 Входящие по email (таблица)"):
            pivot_recv_email = by_email_recv.pivot(index="month", columns="email", values="received").fillna(0).astype(int)
            pivot_recv_email.index.name = "Месяц"
            st.dataframe(pivot_recv_email, use_container_width=True)
    else:
        st.info("Нет данных по входящим для выбранных сэйлзов")
else:
    st.info("Выбери хотя бы одного сэйлза")

# --- График: Исходящие по сэйлзам ---
st.divider()
st.subheader("📤 Исходящие письма — по сэйлз-менеджерам")
st.caption("Сумма отправленных писем со всех аккаунтов менеджера")

by_sales_sent = (
    df.groupby(["month", "sales"])[["sent"]]
    .sum()
    .reset_index()
    .sort_values("month")
)

fig3 = go.Figure()
for name in sorted(by_sales_sent["sales"].unique()):
    subset = by_sales_sent[by_sales_sent["sales"] == name]
    fig3.add_trace(go.Bar(
        name=name,
        x=subset["month"],
        y=subset["sent"],
        marker_color=COLORS.get(name, "#888"),
        text=subset["sent"],
        textposition="outside",
    ))

fig3.update_layout(
    barmode="group",
    height=520,
    xaxis_tickangle=-45,
    yaxis_title="Отправлено писем",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(b=100, t=60),
)

st.plotly_chart(fig3, use_container_width=True)

with st.expander("📋 Исходящие по сэйлзам (таблица)"):
    pivot_sent = by_sales_sent.pivot(index="month", columns="sales", values="sent").fillna(0).astype(int)
    pivot_sent.index.name = "Месяц"
    st.dataframe(pivot_sent, use_container_width=True)

# --- График: Исходящие по email-адресам ---
st.divider()
st.subheader("📤 Исходящие письма — по email-адресам")
st.caption("Разбивка по отдельным почтовым ящикам")

all_sales_sent_email = sorted(df["sales"].unique())
selected_sales_sent_email = st.multiselect(
    "Фильтр по сэйлзу:",
    options=all_sales_sent_email,
    default=all_sales_sent_email,
    key="sales_sent_by_email",
)

if selected_sales_sent_email:
    df_sent_filtered = df[df["sales"].isin(selected_sales_sent_email)]
    by_email_sent = (
        df_sent_filtered.groupby(["month", "email"])[["sent"]]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    by_email_sent = by_email_sent[by_email_sent["sent"] > 0]

    if not by_email_sent.empty:
        fig_sent_email = go.Figure()
        for email_addr in sorted(by_email_sent["email"].unique()):
            subset = by_email_sent[by_email_sent["email"] == email_addr]
            fig_sent_email.add_trace(go.Bar(
                name=email_addr,
                x=subset["month"],
                y=subset["sent"],
            ))

        fig_sent_email.update_layout(
            barmode="stack",
            height=550,
            xaxis_tickangle=-45,
            yaxis_title="Отправлено писем",
            legend=dict(orientation="v", x=1.01, y=1, font=dict(size=10)),
            margin=dict(r=200, b=100, t=60),
        )
        st.plotly_chart(fig_sent_email, use_container_width=True)

        with st.expander("📋 Исходящие по email (таблица)"):
            pivot_sent_email = by_email_sent.pivot(index="month", columns="email", values="sent").fillna(0).astype(int)
            pivot_sent_email.index.name = "Месяц"
            st.dataframe(pivot_sent_email, use_container_width=True)
    else:
        st.info("Нет данных по исходящим для выбранных сэйлзов")
else:
    st.info("Выбери хотя бы одного сэйлза")

# --- График: Исходящие по дням (30 дней) ---
DAILY_FILE = next((p for p in [os.path.join(BASE_DIR, "..", "data", "daily_sent_30d.csv"), os.path.join(BASE_DIR, "data", "daily_sent_30d.csv"), os.path.join(os.path.dirname(BASE_DIR), "data", "daily_sent_30d.csv")] if os.path.exists(p)), os.path.join(BASE_DIR, "..", "data", "daily_sent_30d.csv"))
if os.path.exists(DAILY_FILE):
    st.divider()
    st.subheader("📅 Исходящие письма за последние 30 дней — по дням")
    st.caption("В разрезе сэйлз-менеджеров, все аккаунты суммарно")

    daily = pd.read_csv(DAILY_FILE)
    daily = daily[~daily["email"].isin(SNOVIO_EMAILS)]
    daily["sent"] = pd.to_numeric(daily["sent"], errors="coerce").fillna(0).astype(int)

    daily_by_sales = (
        daily.groupby(["date", "sales"])[["sent"]]
        .sum()
        .reset_index()
        .sort_values("date")
    )

    fig_daily = go.Figure()
    for name in sorted(daily_by_sales["sales"].unique()):
        subset = daily_by_sales[daily_by_sales["sales"] == name]
        fig_daily.add_trace(go.Scatter(
            name=name,
            x=subset["date"],
            y=subset["sent"],
            mode="lines+markers",
            marker=dict(size=5),
            line=dict(color=COLORS.get(name, "#888"), width=2),
        ))

    fig_daily.update_layout(
        height=520,
        xaxis_tickangle=-45,
        yaxis_title="Отправлено писем",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(b=100, t=60),
    )

    st.plotly_chart(fig_daily, use_container_width=True)

    with st.expander("📋 Исходящие по дням (таблица)"):
        pivot_daily = daily_by_sales.pivot(index="date", columns="sales", values="sent").fillna(0).astype(int)
        pivot_daily.index.name = "Дата"
        st.dataframe(pivot_daily, use_container_width=True)

# --- График: Исходящие Snovio — по сэйлз-менеджерам ---
df_snovio = df_all[df_all["email"].isin(SNOVIO_EMAILS)]

if not df_snovio.empty:
    st.divider()
    st.subheader("📨 Исходящие Snovio-рассылки — по сэйлз-менеджерам")
    st.caption("Только почты, используемые для рассылок через Snovio")

    by_sales_snovio = (
        df_snovio.groupby(["month", "sales"])[["sent"]]
        .sum()
        .reset_index()
        .sort_values("month")
    )

    fig_snovio = go.Figure()
    for name in sorted(by_sales_snovio["sales"].unique()):
        subset = by_sales_snovio[by_sales_snovio["sales"] == name]
        fig_snovio.add_trace(go.Bar(
            name=name,
            x=subset["month"],
            y=subset["sent"],
            marker_color=COLORS.get(name, "#888"),
            text=subset["sent"],
            textposition="outside",
        ))

    fig_snovio.update_layout(
        barmode="group",
        height=520,
        xaxis_tickangle=-45,
        yaxis_title="Отправлено писем (Snovio)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(b=100, t=60),
    )

    st.plotly_chart(fig_snovio, use_container_width=True)

    with st.expander("📋 Snovio-рассылки по сэйлзам (таблица)"):
        pivot_snovio = by_sales_snovio.pivot(index="month", columns="sales", values="sent").fillna(0).astype(int)
        pivot_snovio.index.name = "Месяц"
        st.dataframe(pivot_snovio, use_container_width=True)

# --- График: Типы исходящих писем по сэйлзам ---
TYPES_FILE = next((p for p in [os.path.join(BASE_DIR, "..", "data", "outgoing_types_monthly.csv"), os.path.join(BASE_DIR, "data", "outgoing_types_monthly.csv"), os.path.join(os.path.dirname(BASE_DIR), "data", "outgoing_types_monthly.csv")] if os.path.exists(p)), os.path.join(BASE_DIR, "..", "data", "outgoing_types_monthly.csv"))
if os.path.exists(TYPES_FILE):
    st.divider()
    st.subheader("📊 Типы исходящих писем — по сэйлз-менеджерам")
    st.caption("Классификация: первое письмо (cold outreach), ответ, follow-up, forward")

    @st.cache_data(ttl=3600)
    def load_types(mtime):
        tdf = pd.read_csv(TYPES_FILE)
        for col in ["total", "first", "reply", "followup", "forward", "other"]:
            tdf[col] = pd.to_numeric(tdf[col], errors="coerce").fillna(0).astype(int)
        return tdf

    df_types = load_types(os.path.getmtime(TYPES_FILE))

    # Исключаем Snovio-почты
    df_types = df_types[~df_types["email"].isin(SNOVIO_EMAILS)]

    # Фильтр по сэйлзам
    all_sales_types = sorted(df_types["sales"].unique())
    selected_sales_types = st.multiselect(
        "Фильтр по сэйлзу:",
        options=all_sales_types,
        default=all_sales_types,
        key="sales_outgoing_types",
    )

    if selected_sales_types:
        df_types_filtered = df_types[df_types["sales"].isin(selected_sales_types)]

        # Агрегируем по месяцам
        types_monthly = (
            df_types_filtered.groupby("month")[["first", "reply", "followup", "forward", "other"]]
            .sum()
            .reset_index()
            .sort_values("month")
        )

        TYPE_LABELS = {
            "first": "📤 Первое письмо",
            "reply": "↩️ Ответ",
            "followup": "🔁 Follow-up",
            "forward": "➡️ Forward",
            "other": "❓ Другое",
        }
        TYPE_COLORS = {
            "first": "#4A90D9",
            "reply": "#50C878",
            "followup": "#FFB347",
            "forward": "#B19CD9",
            "other": "#888888",
        }

        fig_types = go.Figure()
        for col in ["first", "reply", "followup", "forward", "other"]:
            if types_monthly[col].sum() > 0:
                fig_types.add_trace(go.Bar(
                    name=TYPE_LABELS[col],
                    x=types_monthly["month"],
                    y=types_monthly[col],
                    marker_color=TYPE_COLORS[col],
                    text=types_monthly[col],
                    textposition="inside",
                ))

        fig_types.update_layout(
            barmode="stack",
            height=520,
            xaxis_tickangle=-45,
            yaxis_title="Количество писем",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(b=100, t=60),
        )

        st.plotly_chart(fig_types, use_container_width=True)

        with st.expander("📋 Типы исходящих (таблица)"):
            types_table = (
                df_types_filtered.groupby(["month", "sales"])[["first", "reply", "followup", "forward", "other", "total"]]
                .sum()
                .reset_index()
                .sort_values(["month", "sales"])
            )
            types_table.columns = ["Месяц", "Сэйлз", "📤 Первое", "↩️ Ответ", "🔁 Follow-up", "➡️ Forward", "❓ Другое", "Всего"]
            st.dataframe(types_table, hide_index=True, use_container_width=True)
    else:
        st.info("Выбери хотя бы одного сэйлза")

# --- Новый отдельный блок: распределение входящих адресов ---
INCOMING_DIST_FILE_1D = next((p for p in [os.path.join(BASE_DIR, "..", "data", "incoming_distribution", "summary_1d.json"), os.path.join(BASE_DIR, "data", "incoming_distribution", "summary_1d.json"), os.path.join(os.path.dirname(BASE_DIR), "data", "incoming_distribution", "summary_1d.json")] if os.path.exists(p)), os.path.join(BASE_DIR, "..", "data", "incoming_distribution", "summary_1d.json"))
INCOMING_DIST_FILE_7D = next((p for p in [os.path.join(BASE_DIR, "..", "data", "incoming_distribution", "summary_7d.json"), os.path.join(BASE_DIR, "data", "incoming_distribution", "summary_7d.json"), os.path.join(os.path.dirname(BASE_DIR), "data", "incoming_distribution", "summary_7d.json")] if os.path.exists(p)), os.path.join(BASE_DIR, "..", "data", "incoming_distribution", "summary_7d.json"))
INCOMING_DIST_FILE_2026_MONTHLY = next((p for p in [os.path.join(BASE_DIR, "..", "data", "incoming_distribution", "summary_2026_monthly.json"), os.path.join(BASE_DIR, "data", "incoming_distribution", "summary_2026_monthly.json"), os.path.join(os.path.dirname(BASE_DIR), "data", "incoming_distribution", "summary_2026_monthly.json")] if os.path.exists(p)), os.path.join(BASE_DIR, "..", "data", "incoming_distribution", "summary_2026_monthly.json"))

@st.cache_data(ttl=3600)
def load_incoming_distribution(path, mtime):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

if os.path.exists(INCOMING_DIST_FILE_2026_MONTHLY):
    st.divider()
    st.subheader("📨 Анализ входящих внешниъ адресов по месяцам (2026)")
    st.caption("Отдельный экспериментальный блок. Анализируются только 17 не-Snovio аккаунтов.")

    incoming_yearly = load_incoming_distribution(
        INCOMING_DIST_FILE_2026_MONTHLY,
        os.path.getmtime(INCOMING_DIST_FILE_2026_MONTHLY),
    )
    months_data = incoming_yearly.get("months", [])

    if months_data:
        months = [m.get("month") for m in months_data]
        unique_values = [m.get("unique_external_incoming_addresses", 0) for m in months_data]
        with_reply = [m.get("reply_status", {}).get("with_reply", 0) for m in months_data]
        without_reply = [m.get("reply_status", {}).get("without_reply", 0) for m in months_data]

        latest = months_data[-1]
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Последний месяц: уникальных адресов", latest.get("unique_external_incoming_addresses", 0))
        with col_b:
            st.metric("Последний месяц: с ответом", latest.get("reply_status", {}).get("with_reply", 0))
        with col_c:
            st.metric("Последний месяц: без ответа", latest.get("reply_status", {}).get("without_reply", 0))

        fig_unique = go.Figure()
        fig_unique.add_trace(go.Bar(
            x=months,
            y=unique_values,
            marker_color="#4A90D9",
            text=unique_values,
            textposition="outside",
            name="Уникальные внешние адреса",
        ))
        fig_unique.update_layout(
            height=460,
            yaxis_title="Количество уникальных адресов",
            xaxis_title="Месяц",
            margin=dict(b=60, t=40),
            showlegend=False,
        )
        st.plotly_chart(fig_unique, use_container_width=True)

        fig_dist_monthly = go.Figure()
        bucket_meta = [
            ("1", "1 письмо", "#4A90D9"),
            ("2", "2 письма", "#50C878"),
            ("3", "3 письма", "#FFB347"),
            ("4", "4 письма", "#B57EDC"),
            ("5_plus", "5+ писем", "#FF6B6B"),
        ]
        for bucket_key, bucket_label, color in bucket_meta:
            fig_dist_monthly.add_trace(go.Bar(
                x=months,
                y=[m.get("distribution", {}).get(bucket_key, 0) for m in months_data],
                name=bucket_label,
                marker_color=color,
            ))
        fig_dist_monthly.update_layout(
            barmode="group",
            height=520,
            yaxis_title="Количество уникальных адресов",
            xaxis_title="Месяц",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(b=60, t=60),
        )
        st.plotly_chart(fig_dist_monthly, use_container_width=True)

        fig_reply_status = go.Figure()
        fig_reply_status.add_trace(go.Bar(
            x=months,
            y=with_reply,
            name="С ответом",
            marker_color="#50C878",
        ))
        fig_reply_status.add_trace(go.Bar(
            x=months,
            y=without_reply,
            name="Без ответа",
            marker_color="#FF6B6B",
        ))
        fig_reply_status.update_layout(
            barmode="group",
            height=460,
            yaxis_title="Количество уникальных адресов",
            xaxis_title="Месяц",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(b=60, t=60),
        )
        st.plotly_chart(fig_reply_status, use_container_width=True)

        with st.expander("📋 Помесячная таблица новой метрики"):
            rows = []
            for m in months_data:
                rows.append({
                    "Месяц": m.get("month"),
                    "Уникальных адресов": m.get("unique_external_incoming_addresses", 0),
                    "1 письмо": m.get("distribution", {}).get("1", 0),
                    "2 письма": m.get("distribution", {}).get("2", 0),
                    "3 письма": m.get("distribution", {}).get("3", 0),
                    "4 письма": m.get("distribution", {}).get("4", 0),
                    "5+ писем": m.get("distribution", {}).get("5_plus", 0),
                    "С ответом": m.get("reply_status", {}).get("with_reply", 0),
                    "Без ответа": m.get("reply_status", {}).get("without_reply", 0),
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
else:
    incoming_summary_path = None
    incoming_period_label = None
    if os.path.exists(INCOMING_DIST_FILE_7D):
        incoming_summary_path = INCOMING_DIST_FILE_7D
        incoming_period_label = "7 дней"
    elif os.path.exists(INCOMING_DIST_FILE_1D):
        incoming_summary_path = INCOMING_DIST_FILE_1D
        incoming_period_label = "1 день (тестовый прогон)"

    if incoming_summary_path:
        st.divider()
        st.subheader("📨 Новая метрика: входящие внешние адреса за короткий период")
        st.caption(f"Отдельный экспериментальный блок. Период: {incoming_period_label}. Анализируются только 17 не-Snovio аккаунтов.")

        incoming_summary = load_incoming_distribution(
            incoming_summary_path,
            os.path.getmtime(incoming_summary_path),
        )

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Уникальных внешних адресов", incoming_summary.get("unique_external_incoming_addresses", 0))
        with col_b:
            st.metric("С ответом", incoming_summary.get("reply_status", {}).get("with_reply", 0))
        with col_c:
            st.metric("Без ответа", incoming_summary.get("reply_status", {}).get("without_reply", 0))

        distribution = incoming_summary.get("distribution", {})
        dist_labels = ["1 письмо", "2 письма", "3 письма", "4 письма", "5+ писем"]
        dist_values = [
            distribution.get("1", 0),
            distribution.get("2", 0),
            distribution.get("3", 0),
            distribution.get("4", 0),
            distribution.get("5_plus", 0),
        ]

        fig_incoming_dist = go.Figure()
        fig_incoming_dist.add_trace(go.Bar(
            x=dist_labels,
            y=dist_values,
            marker_color=["#4A90D9", "#50C878", "#FFB347", "#B57EDC", "#FF6B6B"],
            text=dist_values,
            textposition="outside",
            name="Количество адресов",
        ))
        fig_incoming_dist.update_layout(
            height=460,
            yaxis_title="Количество уникальных адресов",
            xaxis_title="Сколько входящих писем пришло с адреса",
            margin=dict(b=60, t=40),
            showlegend=False,
        )
        st.plotly_chart(fig_incoming_dist, use_container_width=True)

        reply_status = incoming_summary.get("reply_status", {})
        fig_reply_status = go.Figure()
        fig_reply_status.add_trace(go.Bar(
            x=["С ответом", "Без ответа"],
            y=[reply_status.get("with_reply", 0), reply_status.get("without_reply", 0)],
            marker_color=["#50C878", "#FF6B6B"],
            text=[reply_status.get("with_reply", 0), reply_status.get("without_reply", 0)],
            textposition="outside",
            name="Статус ответа",
        ))
        fig_reply_status.update_layout(
            height=460,
            yaxis_title="Количество уникальных адресов",
            xaxis_title="Статус ответа со стороны sales",
            margin=dict(b=60, t=40),
            showlegend=False,
        )
        st.plotly_chart(fig_reply_status, use_container_width=True)

        with st.expander("📋 Детали новой метрики (таблица)"):
            detail_rows = []
            for row in incoming_summary.get("top_external_addresses", []):
                detail_rows.append({
                    "Email": row.get("email"),
                    "Входящих писем": row.get("incoming_messages"),
                    "Ответ sales": "Да" if row.get("replied") else "Нет",
                })
            if detail_rows:
                st.dataframe(pd.DataFrame(detail_rows), hide_index=True, use_container_width=True)
            else:
                st.info("Пока нет данных для таблицы")
