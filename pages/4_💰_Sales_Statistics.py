"""
Sales Statistics Dashboard
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
from datetime import datetime

st.set_page_config(
    page_title="Sales Statistics",
    page_icon="💰",
    layout="wide"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sales_report.csv")

st.title("💰 Sales Statistics")

# Загрузка данных
if not os.path.exists(DATA_FILE):
    st.warning("📭 Данные ещё не загружены. Запустите fetch_data.py для сбора данных.")
    st.stop()

df = pd.read_csv(DATA_FILE)

# Время обновления данных
mtime = os.path.getmtime(DATA_FILE)
updated_at = datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")
st.caption(f"🕐 Данные обновлены: **{updated_at}**")

# Общий список сейлзов
all_sales = sorted([s for s in df["sales"].unique() if s != "All"])


# === HELPER: подготовка данных с фильтром по сейлзам ===
def prepare_data(selected, agg_cols):
    if set(selected) == set(all_sales):
        return df[df["sales"] == "All"].copy().sort_values("date")
    else:
        filtered = df[df["sales"].isin(selected)]
        return filtered.groupby("date", as_index=False).agg(agg_cols).sort_values("date")


# ============================================================
# График 1: 🔬 Масштаб vs Результат (бывший график 5)
# ============================================================
st.subheader("🔬 Масштаб vs Результат: почему рост лидов не даёт рост тестов")

selected_sales1 = st.multiselect(
    "Сейлзы", options=all_sales, default=all_sales, key="chart1_sales",
)

df_c1 = prepare_data(selected_sales1, {
    "warm_leads": "sum", "negotiations": "sum",
    "anketa_total": "sum", "ignore": "sum", "test": "sum",
})
df_c1["cr_lead_test"] = df_c1.apply(
    lambda r: round(r["test"] / r["warm_leads"] * 100, 1) if r["warm_leads"] > 0 else 0, axis=1
)
df_c1["ignore_pct"] = df_c1.apply(
    lambda r: round(r["ignore"] / r["negotiations"] * 100, 1) if r["negotiations"] > 0 else 0, axis=1
)

if df_c1.empty:
    st.info("Выберите хотя бы одного сейлза.")
else:
    fig1 = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[0.6, 0.4],
        subplot_titles=("Объём: Лиды → Переговоры → Анкеты → Тест",
                        "Потери: % игнора от переговоров | CR лиды → тест"),
    )

    fig1.add_trace(go.Bar(
        x=df_c1["date"], y=df_c1["warm_leads"],
        name="Тёплые лиды", marker_color="#636EFA", opacity=0.4,
    ), row=1, col=1)
    fig1.add_trace(go.Bar(
        x=df_c1["date"], y=df_c1["negotiations"],
        name="В переговорах", marker_color="#636EFA", opacity=0.6,
    ), row=1, col=1)
    fig1.add_trace(go.Bar(
        x=df_c1["date"], y=df_c1["anketa_total"],
        name="Заявки на анкеты", marker_color="#00CC96", opacity=0.7,
    ), row=1, col=1)
    fig1.add_trace(go.Bar(
        x=df_c1["date"], y=df_c1["test"],
        name="✅ Тест", marker_color="#EF553B",
        text=df_c1["test"], textposition="outside",
        textfont=dict(size=11, color="#EF553B"),
    ), row=1, col=1)

    fig1.add_trace(go.Scatter(
        x=df_c1["date"], y=df_c1["ignore_pct"],
        name="% Игнор от переговоров",
        mode="lines+markers", line=dict(color="#FFA15A", width=2, dash="dot"),
        marker=dict(size=6),
    ), row=2, col=1)
    fig1.add_trace(go.Scatter(
        x=df_c1["date"], y=df_c1["cr_lead_test"],
        name="CR Лиды → Тест", mode="lines+markers+text",
        text=[f"{v:.1f}%" for v in df_c1["cr_lead_test"]],
        textposition="top center", textfont=dict(size=9),
        line=dict(color="#EF553B", width=3), marker=dict(size=8),
    ), row=2, col=1)

    fig1.update_layout(
        template="plotly_dark", height=700, barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="center", x=0.5),
        margin=dict(t=60, b=60),
    )
    fig1.update_yaxes(title_text="Количество", row=1, col=1)
    fig1.update_yaxes(title_text="%", row=2, col=1)
    fig1.update_xaxes(tickangle=-45, row=2, col=1)

    st.plotly_chart(fig1, use_container_width=True)

    # Инсайты
    half = len(df_c1) // 2
    first_half = df_c1.iloc[:half]
    second_half = df_c1.iloc[half:]

    st.markdown("### 💡 Инсайты")
    c1, c2, c3 = st.columns(3)
    leads_growth = (second_half["warm_leads"].mean() / first_half["warm_leads"].mean() - 1) * 100 if first_half["warm_leads"].mean() > 0 else 0
    test_growth = (second_half["test"].mean() / first_half["test"].mean() - 1) * 100 if first_half["test"].mean() > 0 else 0
    ignore_first = (first_half["ignore"].sum() / first_half["negotiations"].sum() * 100) if first_half["negotiations"].sum() > 0 else 0
    ignore_second = (second_half["ignore"].sum() / second_half["negotiations"].sum() * 100) if second_half["negotiations"].sum() > 0 else 0

    c1.metric("Рост лидов (2я vs 1я пол.)", f"+{leads_growth:.0f}%")
    c2.metric("Рост тестов", f"{test_growth:+.0f}%", delta_color="inverse" if test_growth < 0 else "normal")
    c3.metric("Игнор (2я половина)", f"{ignore_second:.0f}%", delta=f"{ignore_second - ignore_first:+.1f}% vs 1я пол.")

# ============================================================
# График 2: Тёплые лиды → Согласованные блогеры (CR)
# ============================================================
st.divider()
st.subheader("📈 Тёплые лиды → Согласованные блогеры (CR)")

selected_sales2 = st.multiselect(
    "Сейлзы", options=all_sales, default=all_sales, key="chart2_sales",
)

df_c2 = prepare_data(selected_sales2, {"warm_leads": "sum", "negotiations": "sum"})
df_c2["cr_pct"] = df_c2.apply(
    lambda r: round(r["negotiations"] / r["warm_leads"] * 100, 1) if r["warm_leads"] > 0 else 0, axis=1
)

if df_c2.empty:
    st.info("Выберите хотя бы одного сейлза.")
else:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df_c2["date"], y=df_c2["warm_leads"], name="Тёплые лиды", marker_color="#636EFA", opacity=0.7))
    fig2.add_trace(go.Bar(x=df_c2["date"], y=df_c2["negotiations"], name="В переговорах (согласованные)", marker_color="#00CC96", opacity=0.7))
    fig2.add_trace(go.Scatter(
        x=df_c2["date"], y=df_c2["cr_pct"], name="CR %",
        mode="lines+markers+text", text=[f"{v:.0f}%" for v in df_c2["cr_pct"]],
        textposition="top center", textfont=dict(size=10),
        line=dict(color="#EF553B", width=3), marker=dict(size=8), yaxis="y2",
    ))
    fig2.update_layout(
        barmode="group", template="plotly_dark", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Количество"),
        yaxis2=dict(title="CR %", overlaying="y", side="right", range=[0, 100], showgrid=False),
        xaxis=dict(title="Неделя", tickangle=-45), margin=dict(t=40, b=80),
    )
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Ср. тёплых лидов / нед.", f"{df_c2['warm_leads'].mean():.0f}")
    col2.metric("Ср. согласованных / нед.", f"{df_c2['negotiations'].mean():.0f}")
    col3.metric("Ср. CR", f"{df_c2['cr_pct'].mean():.1f}%")

# ============================================================
# График 3: Согласованные блогеры → Заявки на анкеты (CR)
# ============================================================
st.divider()
st.subheader("📈 Согласованные блогеры → Заявки на анкеты (CR)")

selected_sales3 = st.multiselect(
    "Сейлзы", options=all_sales, default=all_sales, key="chart3_sales",
)

df_c3 = prepare_data(selected_sales3, {"negotiations": "sum", "anketa_total": "sum"})
df_c3["cr_pct"] = df_c3.apply(
    lambda r: round(r["anketa_total"] / r["negotiations"] * 100, 1) if r["negotiations"] > 0 else 0, axis=1
)

if df_c3.empty:
    st.info("Выберите хотя бы одного сейлза.")
else:
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=df_c3["date"], y=df_c3["negotiations"], name="Согласованные блогеры", marker_color="#636EFA", opacity=0.7))
    fig3.add_trace(go.Bar(x=df_c3["date"], y=df_c3["anketa_total"], name="Заявки на анкеты", marker_color="#00CC96", opacity=0.7))
    fig3.add_trace(go.Scatter(
        x=df_c3["date"], y=df_c3["cr_pct"], name="CR %",
        mode="lines+markers+text", text=[f"{v:.0f}%" for v in df_c3["cr_pct"]],
        textposition="top center", textfont=dict(size=10),
        line=dict(color="#EF553B", width=3), marker=dict(size=8), yaxis="y2",
    ))
    fig3.update_layout(
        barmode="group", template="plotly_dark", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Количество"),
        yaxis2=dict(title="CR %", overlaying="y", side="right", range=[0, 100], showgrid=False),
        xaxis=dict(title="Неделя", tickangle=-45), margin=dict(t=40, b=80),
    )
    st.plotly_chart(fig3, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Ср. согласованных / нед.", f"{df_c3['negotiations'].mean():.0f}")
    col2.metric("Ср. заявок на анкеты / нед.", f"{df_c3['anketa_total'].mean():.0f}")
    col3.metric("Ср. CR", f"{df_c3['cr_pct'].mean():.1f}%")

# ============================================================
# График 4: Согласованные блогеры → Игнор (CR)
# ============================================================
st.divider()
st.subheader("📈 Согласованные блогеры → Игнор (CR)")

selected_sales4 = st.multiselect(
    "Сейлзы", options=all_sales, default=all_sales, key="chart4_sales",
)

df_c4 = prepare_data(selected_sales4, {"negotiations": "sum", "ignore": "sum"})
df_c4["cr_pct"] = df_c4.apply(
    lambda r: round(r["ignore"] / r["negotiations"] * 100, 1) if r["negotiations"] > 0 else 0, axis=1
)
df_c4["diff"] = df_c4["negotiations"] - df_c4["ignore"]

if df_c4.empty:
    st.info("Выберите хотя бы одного сейлза.")
else:
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=df_c4["date"], y=df_c4["negotiations"], name="Согласованные блогеры", marker_color="#636EFA", opacity=0.7))
    fig4.add_trace(go.Bar(
        x=df_c4["date"], y=df_c4["ignore"], name="Игнор", marker_color="#FFA15A", opacity=0.7,
        text=[f"Δ {d}" for d in df_c4["diff"]], textposition="outside",
        textfont=dict(size=9, color="#AB63FA"),
    ))
    fig4.add_trace(go.Scatter(
        x=df_c4["date"], y=df_c4["cr_pct"], name="CR %",
        mode="lines+markers+text", text=[f"{v:.0f}%" for v in df_c4["cr_pct"]],
        textposition="top center", textfont=dict(size=10),
        line=dict(color="#EF553B", width=3), marker=dict(size=8), yaxis="y2",
    ))
    fig4.update_layout(
        barmode="group", template="plotly_dark", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Количество"),
        yaxis2=dict(title="CR %", overlaying="y", side="right", range=[0, 100], showgrid=False),
        xaxis=dict(title="Неделя", tickangle=-45), margin=dict(t=40, b=80),
    )
    st.plotly_chart(fig4, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Ср. согласованных / нед.", f"{df_c4['negotiations'].mean():.0f}")
    col2.metric("Ср. игноров / нед.", f"{df_c4['ignore'].mean():.0f}")
    col3.metric("Ср. CR", f"{df_c4['cr_pct'].mean():.1f}%")

# ============================================================
# График 5: CR в Тест (из согласованных vs из заявок на анкеты)
# ============================================================
st.divider()
st.subheader("📈 CR в Тест: из согласованных vs из заявок на анкеты")

selected_sales5 = st.multiselect(
    "Сейлзы", options=all_sales, default=all_sales, key="chart5_sales",
)

df_c5 = prepare_data(selected_sales5, {"negotiations": "sum", "anketa_total": "sum", "test": "sum"})
df_c5["cr_nego_test"] = df_c5.apply(
    lambda r: round(r["test"] / r["negotiations"] * 100, 1) if r["negotiations"] > 0 else 0, axis=1
)
df_c5["cr_anketa_test"] = df_c5.apply(
    lambda r: round(r["test"] / r["anketa_total"] * 100, 1) if r["anketa_total"] > 0 else 0, axis=1
)

if df_c5.empty:
    st.info("Выберите хотя бы одного сейлза.")
else:
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=df_c5["date"], y=df_c5["cr_nego_test"],
        name="CR Согласованные → Тест", mode="lines+markers+text",
        text=[f"{v:.0f}%" for v in df_c5["cr_nego_test"]],
        textposition="top center", textfont=dict(size=10),
        line=dict(color="#636EFA", width=3), marker=dict(size=8),
    ))
    fig5.add_trace(go.Scatter(
        x=df_c5["date"], y=df_c5["cr_anketa_test"],
        name="CR Заявки на анкеты → Тест", mode="lines+markers+text",
        text=[f"{v:.0f}%" for v in df_c5["cr_anketa_test"]],
        textposition="bottom center", textfont=dict(size=10),
        line=dict(color="#00CC96", width=3), marker=dict(size=8),
    ))
    fig5.update_layout(
        template="plotly_dark", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="CR %", range=[0, max(df_c5["cr_anketa_test"].max(), df_c5["cr_nego_test"].max()) * 1.3]),
        xaxis=dict(title="Неделя", tickangle=-45), margin=dict(t=40, b=80),
    )
    st.plotly_chart(fig5, use_container_width=True)

    col1, col2 = st.columns(2)
    col1.metric("Ср. CR Согласованные → Тест", f"{df_c5['cr_nego_test'].mean():.1f}%")
    col2.metric("Ср. CR Заявки → Тест", f"{df_c5['cr_anketa_test'].mean():.1f}%")
