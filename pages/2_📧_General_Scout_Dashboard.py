"""
app.py — Snovio Dashboard

Запуск: streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os
from datetime import datetime, timezone, timedelta

try:
    st.set_page_config(
        page_title="General Scout Dashboard",
        page_icon="📧",
        layout="wide"
    )
except Exception:
    pass

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "snovio_parsed.csv")

# Порядок месяцев
MONTH_ORDER = [
    "Сентябрь 2025", "Октябрь 2025", "Ноябрь 2025",
    "Декабрь 2025", "Январь 2026", "Февраль 2026"
]


@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(DATA_FILE)
    # Числовые колонки
    num_cols = [
        "sn_contacts", "emails_sent", "emails_open", "sn_replies",
        "wa_contacts", "wa_replies", "tt_contacts", "ig_contacts",
        "tt_replies", "ig_replies_tt", "ig_replies_ig",
        "total_contacts", "replies_with_dup", "replies_no_dup",
        "agreed", "sn_reply_pct", "agreed_pct"
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Сортировка по порядку месяцев
    df["month_order"] = df["month"].apply(
        lambda m: MONTH_ORDER.index(m) if m in MONTH_ORDER else 99
    )
    df = df.sort_values("month_order")
    return df


df = load_data()

# --- Шапка ---
st.title("📧 General Scout Dashboard (работает на тестовых данных)")

TZ_MSK = timezone(timedelta(hours=3))
csv_mtime = os.path.getmtime(DATA_FILE)
csv_updated = datetime.fromtimestamp(csv_mtime, tz=TZ_MSK).strftime("%d.%m.%Y %H:%M")
st.caption(f"🕐 Данные обновлены: **{csv_updated}**")

st.divider()

# --- График: Добавлено контактов SN по скаутам по месяцам ---
st.subheader("📬 Добавлено контактов в Snovio")

# Фильтр по скаутам
all_scouts = sorted(df["scout"].unique().tolist())
selected_scouts = st.multiselect(
    "Фильтр по скаутам:",
    options=all_scouts,
    default=all_scouts,
    key="scouts_sn"
)

if selected_scouts:
    df_filtered = df[df["scout"].isin(selected_scouts)]

    # Доступные месяцы в данных (в правильном порядке)
    available_months = [m for m in MONTH_ORDER if m in df_filtered["month"].values]

    fig = go.Figure()

    for scout in selected_scouts:
        scout_data = df_filtered[df_filtered["scout"] == scout].set_index("month")["sn_contacts"]
        values = [scout_data.get(m, 0) for m in available_months]

        # Пропускаем скаутов у кого везде 0
        if sum(values) == 0:
            continue

        fig.add_trace(go.Bar(
            name=scout,
            x=available_months,
            y=values,
            text=[int(v) if v > 0 else "" for v in values],
            textposition="inside",
            insidetextanchor="middle",
        ))

    fig.update_layout(
        barmode="stack",
        height=560,
        xaxis_tickangle=-30,
        yaxis_title="Добавлено контактов SN",
        legend=dict(
            orientation="v",
            x=1.01,
            y=1,
            font=dict(size=11),
        ),
        margin=dict(r=160, b=80, t=40),
    )

    st.plotly_chart(fig, width="stretch")

    # Таблица итогов
    with st.expander("📋 Итоги по скаутам (таблица)"):
        pivot = df_filtered[df_filtered["scout"].isin(selected_scouts)].pivot_table(
            index="scout",
            columns="month",
            values="sn_contacts",
            aggfunc="sum",
            fill_value=0
        )
        # Упорядочиваем колонки
        pivot = pivot.reindex(columns=[m for m in MONTH_ORDER if m in pivot.columns])
        pivot["Итого"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("Итого", ascending=False)
        pivot.columns.name = None
        st.dataframe(pivot, width="stretch")
else:
    st.info("Выбери хотя бы одного скаута")

st.divider()

# --- График: Писем отправлено по скаутам по месяцам ---
st.subheader("✉️ Писем отправлено через Snovio")

selected_scouts_emails = st.multiselect(
    "Фильтр по скаутам:",
    options=all_scouts,
    default=all_scouts,
    key="scouts_emails"
)

if selected_scouts_emails:
    df_emails = df[df["scout"].isin(selected_scouts_emails)]
    available_months = [m for m in MONTH_ORDER if m in df_emails["month"].values]

    fig2 = go.Figure()

    for scout in selected_scouts_emails:
        scout_data = df_emails[df_emails["scout"] == scout].set_index("month")["emails_sent"]
        values = [scout_data.get(m, 0) for m in available_months]

        if sum(values) == 0:
            continue

        fig2.add_trace(go.Bar(
            name=scout,
            x=available_months,
            y=values,
            text=[int(v) if v > 0 else "" for v in values],
            textposition="inside",
            insidetextanchor="middle",
        ))

    fig2.update_layout(
        barmode="stack",
        height=560,
        xaxis_tickangle=-30,
        yaxis_title="Писем отправлено",
        legend=dict(
            orientation="v",
            x=1.01,
            y=1,
            font=dict(size=11),
        ),
        margin=dict(r=160, b=80, t=40),
    )

    st.plotly_chart(fig2, width="stretch")

    with st.expander("📋 Итоги по скаутам (таблица)"):
        pivot2 = df_emails.pivot_table(
            index="scout",
            columns="month",
            values="emails_sent",
            aggfunc="sum",
            fill_value=0
        )
        pivot2 = pivot2.reindex(columns=[m for m in MONTH_ORDER if m in pivot2.columns])
        pivot2["Итого"] = pivot2.sum(axis=1)
        pivot2 = pivot2.sort_values("Итого", ascending=False)
        pivot2.columns.name = None
        st.dataframe(pivot2, width="stretch")
else:
    st.info("Выбери хотя бы одного скаута")

st.divider()

# --- График: Добавлено контактов в общем по скаутам по месяцам ---
st.subheader("👥 Добавлено контактов в общем")

selected_scouts_total = st.multiselect(
    "Фильтр по скаутам:",
    options=all_scouts,
    default=all_scouts,
    key="scouts_total"
)

if selected_scouts_total:
    df_total = df[df["scout"].isin(selected_scouts_total)]
    available_months_total = [m for m in MONTH_ORDER if m in df_total["month"].values]

    fig4 = go.Figure()

    for scout in selected_scouts_total:
        scout_data = df_total[df_total["scout"] == scout].set_index("month")["total_contacts"]
        values = [scout_data.get(m, 0) for m in available_months_total]

        if sum(values) == 0:
            continue

        fig4.add_trace(go.Bar(
            name=scout,
            x=available_months_total,
            y=values,
            text=[int(v) if v > 0 else "" for v in values],
            textposition="inside",
            insidetextanchor="middle",
        ))

    fig4.update_layout(
        barmode="stack",
        height=560,
        xaxis_tickangle=-30,
        yaxis_title="Контактов в общем",
        legend=dict(orientation="v", x=1.01, y=1, font=dict(size=11)),
        margin=dict(r=160, b=80, t=40),
    )

    st.plotly_chart(fig4, width="stretch")

    with st.expander("📋 Итоги по скаутам (таблица)"):
        pivot4 = df_total.pivot_table(
            index="scout",
            columns="month",
            values="total_contacts",
            aggfunc="sum",
            fill_value=0
        )
        pivot4 = pivot4.reindex(columns=[m for m in MONTH_ORDER if m in pivot4.columns])
        pivot4["Итого"] = pivot4.sum(axis=1)
        pivot4 = pivot4.sort_values("Итого", ascending=False)
        pivot4.columns.name = None
        st.dataframe(pivot4, width="stretch")
else:
    st.info("Выбери хотя бы одного скаута")

st.divider()

# --- График: Отправлено vs Ответы + CR% по месяцам (без разбивки по скаутам) ---
st.subheader("📈 Отправлено/отвечено писем через Snovio")
st.caption("Агрегировано по всем скаутам. CR = Ответы / Отправлено × 100%")

available_months_all = [m for m in MONTH_ORDER if m in df["month"].values]

monthly_agg = (
    df.groupby("month")[["emails_sent", "sn_replies"]]
    .sum()
    .reindex(available_months_all)
    .reset_index()
)
monthly_agg["cr_pct"] = (
    monthly_agg["sn_replies"] / monthly_agg["emails_sent"].replace(0, float("nan")) * 100
).round(2)

fig3 = go.Figure()

fig3.add_trace(go.Bar(
    name="Отправлено",
    x=monthly_agg["month"],
    y=monthly_agg["emails_sent"],
    marker_color="#4A90D9",
    text=monthly_agg["emails_sent"].astype(int),
    textposition="outside",
    yaxis="y1",
))

fig3.add_trace(go.Bar(
    name="Ответы",
    x=monthly_agg["month"],
    y=monthly_agg["sn_replies"],
    marker_color="#50C878",
    text=monthly_agg["sn_replies"].astype(int),
    textposition="outside",
    yaxis="y1",
))

fig3.add_trace(go.Scatter(
    name="CR%",
    x=monthly_agg["month"],
    y=monthly_agg["cr_pct"],
    mode="lines+markers+text",
    line=dict(color="#FF4B4B", width=2),
    marker=dict(size=8),
    text=[f"{v:.2f}%" if v == v else "" for v in monthly_agg["cr_pct"]],
    textposition="top center",
    textfont=dict(color="#FF4B4B", size=12),
    yaxis="y2",
))

fig3.update_layout(
    barmode="group",
    height=520,
    xaxis_tickangle=-30,
    yaxis=dict(title="Количество писем", side="left"),
    yaxis2=dict(
        title="CR%",
        side="right",
        overlaying="y",
        tickformat=".2f",
        showgrid=False,
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(b=80, t=60),
)

st.plotly_chart(fig3, width="stretch")

with st.expander("📋 Данные по месяцам (таблица)"):
    tbl = monthly_agg.copy()
    tbl["emails_sent"] = tbl["emails_sent"].astype(int)
    tbl["sn_replies"] = tbl["sn_replies"].astype(int)
    tbl["cr_pct"] = tbl["cr_pct"].map(lambda x: f"{x:.2f}%" if x == x else "—")
    tbl.columns = ["Месяц", "Отправлено", "Ответы", "CR%"]
    st.dataframe(tbl, hide_index=True, width="stretch")

st.divider()

# --- График: Контактов в общем / Блогеров на листе + CR% по месяцам ---
st.subheader("📋 Контактов в общем → Блогеров на листе и CR%")
st.caption("Агрегировано по всем скаутам. CR = Блогеров на листе / Контактов в общем × 100%")

monthly_agg2 = (
    df.groupby("month")[["total_contacts", "replies_no_dup"]]
    .sum()
    .reindex(available_months_all)
    .reset_index()
)
monthly_agg2["cr_pct"] = (
    monthly_agg2["replies_no_dup"] / monthly_agg2["total_contacts"].replace(0, float("nan")) * 100
).round(2)

fig5 = go.Figure()

fig5.add_trace(go.Bar(
    name="Контактов в общем",
    x=monthly_agg2["month"],
    y=monthly_agg2["total_contacts"],
    marker_color="#4A90D9",
    text=monthly_agg2["total_contacts"].astype(int),
    textposition="outside",
    yaxis="y1",
))

fig5.add_trace(go.Bar(
    name="Блогеров на листе",
    x=monthly_agg2["month"],
    y=monthly_agg2["replies_no_dup"],
    marker_color="#50C878",
    text=monthly_agg2["replies_no_dup"].astype(int),
    textposition="outside",
    yaxis="y1",
))

fig5.add_trace(go.Scatter(
    name="CR%",
    x=monthly_agg2["month"],
    y=monthly_agg2["cr_pct"],
    mode="lines+markers+text",
    line=dict(color="#FF4B4B", width=2),
    marker=dict(size=8),
    text=[f"{v:.2f}%" if v == v else "" for v in monthly_agg2["cr_pct"]],
    textposition="top center",
    textfont=dict(color="#FF4B4B", size=12),
    yaxis="y2",
))

fig5.update_layout(
    barmode="group",
    height=520,
    xaxis_tickangle=-30,
    yaxis=dict(title="Количество контактов", side="left"),
    yaxis2=dict(
        title="CR%",
        side="right",
        overlaying="y",
        tickformat=".2f",
        showgrid=False,
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(b=80, t=60),
)

st.plotly_chart(fig5, width="stretch")

with st.expander("📋 Данные по месяцам (таблица)"):
    tbl2 = monthly_agg2.copy()
    tbl2["total_contacts"] = tbl2["total_contacts"].astype(int)
    tbl2["replies_no_dup"] = tbl2["replies_no_dup"].astype(int)
    tbl2["cr_pct"] = tbl2["cr_pct"].map(lambda x: f"{x:.2f}%" if x == x else "—")
    tbl2.columns = ["Месяц", "Контактов в общем", "Блогеров на листе", "CR%"]
    st.dataframe(tbl2, hide_index=True, width="stretch")
