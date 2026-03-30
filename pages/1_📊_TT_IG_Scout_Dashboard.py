"""
app.py — Дашборд Scout Analytics

Запуск: streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os
from datetime import datetime

# --- Настройки страницы (только при прямом запуске) ---
if __name__ == "__main__" or not hasattr(st, "_page_config_set"):
    try:
        st.set_page_config(
            page_title="TT/IG Scout Dashboard",
            page_icon="📊",
            layout="wide"
        )
    except Exception:
        pass

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "scout_raw.csv")

COLUMN_NAMES = [
    "TikTok", "Instagram", "Snapchat", "Статус", "Скаут",
    "Где_нашли", "Дата", "Где_написали", "Дата_ответа", "IG",
    "Где_ответ", "Камилла", "Комм_скаут", "Комм_кам", "Повторы"
]


@st.cache_data
def load_data():
    """Загружает CSV и подготавливает данные."""
    df = pd.read_csv(DATA_FILE, header=None, names=COLUMN_NAMES, low_memory=False)

    # Убираем строку-заголовок если попала в данные
    df = df[df["Дата"] != "Дата добавления"]

    # Парсим даты (формат дд.мм.гггг)
    df["Дата"] = pd.to_datetime(df["Дата"], format="%d.%m.%Y", errors="coerce")

    # Убираем строки без даты
    df = df.dropna(subset=["Дата"])

    # Метка: повтор или уникальная
    df["Тип"] = df["Повторы"].fillna("").str.contains("повтор", case=False).map(
        {True: "Повтор", False: "Уникальная"}
    )

    # Год и месяц
    df["Год"] = df["Дата"].dt.year
    df["Месяц_дата"] = df["Дата"].dt.to_period("M").dt.to_timestamp()
    df["Месяц"] = df["Дата"].dt.to_period("M").astype(str)

    return df


# --- Загрузка данных ---
df = load_data()

# --- Заголовок ---
st.title("📊 TT/IG Scout Dashboard")

# --- Информация об актуальности данных ---
from datetime import timezone, timedelta
TZ_MSK = timezone(timedelta(hours=3))
csv_mtime = os.path.getmtime(DATA_FILE)
csv_updated = datetime.fromtimestamp(csv_mtime, tz=TZ_MSK).strftime("%d.%m.%Y %H:%M")

_df_check = pd.read_csv(DATA_FILE, header=None, usecols=[6], names=["Дата"], low_memory=False)
_df_check = _df_check[_df_check["Дата"] != "Дата добавления"]
last_date = pd.to_datetime(_df_check["Дата"], format="%d.%m.%Y", errors="coerce").max()
last_date_str = last_date.strftime("%d.%m.%Y") if pd.notna(last_date) else "—"

st.caption(f"🕐 Данные обновлены: **{csv_updated}** &nbsp;|&nbsp; 📅 Последняя запись в данных: **{last_date_str}**")

# Скрываем лишние теги в мультиселекте — показываем только первые 3
st.markdown("""
<style>
div[data-baseweb="tag"]:nth-child(n+4) { display: none; }
</style>
""", unsafe_allow_html=True)

# Метрики
total = len(df)
unique = (df["Тип"] == "Уникальная").sum()
repeat = (df["Тип"] == "Повтор").sum()

col1, col2, col3 = st.columns(3)
col1.metric("Всего лидов", f"{total:,}")
col2.metric("Уникальных лидов", f"{unique:,}", f"{unique/total*100:.1f}%")
col3.metric("Повторов", f"{repeat:,}", f"{repeat/total*100:.1f}%", delta_color="inverse")

st.divider()

# --- Фильтр: диапазон месяцев ---
all_months_sorted = sorted(df["Месяц_дата"].unique().tolist())
min_date = all_months_sorted[0]
max_date = all_months_sorted[-1]

fcol1, fcol2 = st.columns(2)

with fcol1:
    from_month = st.selectbox(
        "С месяца:",
        options=all_months_sorted,
        index=0,
        format_func=lambda d: pd.Timestamp(d).strftime("%B %Y")
    )

with fcol2:
    to_month = st.selectbox(
        "По месяц:",
        options=all_months_sorted,
        index=len(all_months_sorted) - 1,
        format_func=lambda d: pd.Timestamp(d).strftime("%B %Y")
    )

# Применяем фильтр
if from_month <= to_month:
    df_filtered = df[(df["Месяц_дата"] >= from_month) & (df["Месяц_дата"] <= to_month)]
else:
    st.warning("⚠️ Начало диапазона не может быть позже конца")
    df_filtered = df

# --- Группировка по месяцам и типу ---
monthly = (
    df_filtered
    .groupby(["Месяц_дата", "Месяц", "Тип"])
    .size()
    .reset_index(name="Количество")
    .sort_values("Месяц_дата")
)

months_order = monthly["Месяц"].unique().tolist()

unique_by_month = monthly[monthly["Тип"] == "Уникальная"].set_index("Месяц")["Количество"]
repeat_by_month = monthly[monthly["Тип"] == "Повтор"].set_index("Месяц")["Количество"]
total_by_month = monthly.groupby("Месяц")["Количество"].sum()

# --- График ---
fig = go.Figure()

# Столбики: уникальные (снизу)
fig.add_trace(go.Bar(
    name="Уникальные",
    x=months_order,
    y=[unique_by_month.get(m, 0) for m in months_order],
    marker_color="#4A90D9",
    text=[unique_by_month.get(m, 0) for m in months_order],
    textposition="inside",
    insidetextanchor="middle"
))

# Столбики: повторы (сверху)
fig.add_trace(go.Bar(
    name="Повторы",
    x=months_order,
    y=[repeat_by_month.get(m, 0) for m in months_order],
    marker_color="#E8A838",
    text=[repeat_by_month.get(m, 0) for m in months_order],
    textposition="inside",
    insidetextanchor="middle"
))

# Линия: общее количество
fig.add_trace(go.Scatter(
    name="Всего",
    x=months_order,
    y=[total_by_month.get(m, 0) for m in months_order],
    mode="lines+markers",
    line=dict(color="#333333", width=2),
    marker=dict(size=6)
))

fig.update_layout(
    barmode="stack",
    title="Количество лидов по месяцам",
    xaxis_tickangle=-45,
    height=520,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis_title="Количество лидов"
)

st.plotly_chart(fig, width='stretch')

st.divider()

# --- График 3: Уникальные по источникам ---
st.subheader("🔗 Уникальные лиды по источникам")

df_unique_src = df_filtered[
    ~df_filtered["Повторы"].fillna("").str.contains("повтор", case=False)
].copy()

# Убираем строки без источника и строку-заголовок
df_unique_src = df_unique_src[
    ~df_unique_src["Где_нашли"].isin(["", "Где нашли"]) &
    df_unique_src["Где_нашли"].notna()
]

sources = sorted(df_unique_src["Где_нашли"].unique().tolist())
selected_sources = st.multiselect(
    "Фильтр по источнику:",
    options=sources,
    default=sources
)

if selected_sources:
    df_src = df_unique_src[df_unique_src["Где_нашли"].isin(selected_sources)]

    src_monthly = (
        df_src
        .groupby(["Месяц_дата", "Месяц", "Где_нашли"])
        .size()
        .reset_index(name="Количество")
        .sort_values("Месяц_дата")
    )

    months_src = src_monthly["Месяц"].unique().tolist()

    fig3 = go.Figure()

    colors = {"TT": "#69C9D0", "IG": "#E1306C", "Snap": "#FFFC00", "Twitch": "#9146FF"}

    for src in selected_sources:
        src_data = src_monthly[src_monthly["Где_нашли"] == src]
        src_by_month = src_data.set_index("Месяц")["Количество"]
        fig3.add_trace(go.Bar(
            name=src,
            x=months_src,
            y=[src_by_month.get(m, 0) for m in months_src],
            marker_color=colors.get(src, None),
            text=[src_by_month.get(m, 0) for m in months_src],
            textposition="inside",
            insidetextanchor="middle"
        ))

    fig3.update_layout(
        barmode="stack",
        title="Уникальные лиды по месяцам (разбивка по источнику)",
        xaxis_tickangle=-45,
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="Уникальных лидов"
    )

    st.plotly_chart(fig3, width='stretch')
else:
    st.info("Выбери хотя бы один источник")

st.divider()

# --- График 2: Уникальные по скаутам ---
st.subheader("👤 Уникальные лиды по скаутам")

df_unique = df_filtered[
    ~df_filtered["Повторы"].fillna("").str.contains("повтор", case=False)
].copy()

# Все скауты отсортированные по количеству уникальных
all_scouts = (
    df_unique.groupby("Скаут").size()
    .sort_values(ascending=False)
    .index.tolist()
)

# Мультиселект — по умолчанию все, теги свёрнуты
selected_scouts = st.multiselect(
    "Фильтр по скаутам (по умолчанию — все):",
    options=all_scouts,
    default=all_scouts,
    max_selections=None,
    placeholder="Выбери скаутов...",
    label_visibility="visible"
)

if selected_scouts:
    df_scouts = df_unique[df_unique["Скаут"].isin(selected_scouts)]

    scout_monthly = (
        df_scouts
        .groupby(["Месяц_дата", "Месяц", "Скаут"])
        .size()
        .reset_index(name="Количество")
        .sort_values("Месяц_дата")
    )

    months_scouts = sorted(scout_monthly["Месяц"].unique().tolist())

    fig2 = go.Figure()

    for scout in selected_scouts:
        scout_data = scout_monthly[scout_monthly["Скаут"] == scout].set_index("Месяц")["Количество"]
        fig2.add_trace(go.Bar(
            name=scout,
            x=months_scouts,
            y=[scout_data.get(m, 0) for m in months_scouts],
        ))

    fig2.update_layout(
        barmode="stack",
        title="Уникальные лиды по месяцам (разбивка по скаутам)",
        xaxis_tickangle=-45,
        height=550,
        yaxis_title="Уникальных лидов",
        legend=dict(
            orientation="v",
            x=1.01,
            y=1,
            font=dict(size=11),
            tracegroupgap=2
        ),
        margin=dict(r=150)
    )

    st.plotly_chart(fig2, width='stretch')
else:
    st.info("Выбери хотя бы одного скаута")

st.divider()

# --- График 4: Уникальные лиды по скаутам по неделям ---
st.subheader("📅 Уникальные лиды по скаутам — по неделям")

# Фильтруем: только уникальные, зависит от выбранного диапазона дат
df_5w = df_filtered[
    ~df_filtered["Повторы"].fillna("").str.contains("повтор", case=False)
].copy()

# Номер недели: "Нед. 1 (дд.мм – дд.мм)"
df_5w["Неделя_нач"] = df_5w["Дата"].apply(
    lambda d: d - pd.Timedelta(days=d.weekday())
)
df_5w["Неделя_label"] = df_5w["Неделя_нач"].apply(
    lambda d: f"{d.strftime('%d.%m')}–{(d + pd.Timedelta(days=6)).strftime('%d.%m')}"
)

weeks_order = (
    df_5w.groupby("Неделя_нач")["Неделя_label"].first()
    .sort_index()
    .tolist()
)

# Скауты для этого графика (по количеству за 2 года)
all_scouts_5w = (
    df_5w.groupby("Скаут").size()
    .sort_values(ascending=False)
    .index.tolist()
)

selected_scouts_5w = st.multiselect(
    "Фильтр по скаутам:",
    options=all_scouts_5w,
    default=all_scouts_5w,
    key="scouts_5w"
)

if selected_scouts_5w:
    df_5w_filtered = df_5w[df_5w["Скаут"].isin(selected_scouts_5w)]

    weekly = (
        df_5w_filtered
        .groupby(["Неделя_нач", "Неделя_label", "Скаут"])
        .size()
        .reset_index(name="Количество")
        .sort_values("Неделя_нач")
    )

    fig4 = go.Figure()

    for scout in selected_scouts_5w:
        scout_data = weekly[weekly["Скаут"] == scout].set_index("Неделя_label")["Количество"]
        fig4.add_trace(go.Bar(
            name=scout,
            x=weeks_order,
            y=[scout_data.get(w, 0) for w in weeks_order],
            text=[scout_data.get(w, 0) if scout_data.get(w, 0) > 0 else "" for w in weeks_order],
            textposition="inside",
            insidetextanchor="middle"
        ))

    fig4.update_layout(
        barmode="stack",
        title="Уникальные лиды по скаутам (последние 2 года по неделям)",
        height=550,
        yaxis_title="Уникальных лидов",
        xaxis_title="Неделя",
        xaxis=dict(
            tickangle=-45,
            tickmode="array",
            tickvals=weeks_order[::4],   # каждая 4-я неделя = ~раз в месяц
            ticktext=weeks_order[::4],
        ),
        legend=dict(
            orientation="v",
            x=1.01,
            y=1,
            font=dict(size=11),
        ),
        margin=dict(r=150, b=80)
    )

    st.plotly_chart(fig4, width='stretch')
else:
    st.info("Выбери хотя бы одного скаута")

st.divider()

# --- График 5: Медиана соотношения повторов к уникальным по скаутам ---
st.subheader("📊 Соотношение повторов к уникальным — по скаутам")
st.caption("Показывает долю повторов относительно уникальных лидов для каждого скаута. Красная линия — медиана по всем скаутам.")

# Считаем по всем скаутам в отфильтрованном диапазоне
scout_ratio = (
    df_filtered
    .groupby(["Скаут", "Тип"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

# Гарантируем наличие обоих столбцов
if "Уникальная" not in scout_ratio.columns:
    scout_ratio["Уникальная"] = 0
if "Повтор" not in scout_ratio.columns:
    scout_ratio["Повтор"] = 0

# Оставляем только скаутов с хотя бы 1 уникальным лидом (иначе деление на 0)
scout_ratio = scout_ratio[scout_ratio["Уникальная"] > 0].copy()
scout_ratio["Соотношение"] = scout_ratio["Повтор"] / scout_ratio["Уникальная"]

# Убираем строку-заголовок (если попала)
scout_ratio = scout_ratio[~scout_ratio["Скаут"].isin(["", "Скаут", "scout"]) & scout_ratio["Скаут"].notna()]

# Сортируем по соотношению (по убыванию)
scout_ratio = scout_ratio.sort_values("Соотношение", ascending=False)

# Медиана
median_ratio = scout_ratio["Соотношение"].median()

# Цвет столбцов: выше медианы — оранжевый, ниже — синий
colors_ratio = [
    "#E8A838" if r >= median_ratio else "#4A90D9"
    for r in scout_ratio["Соотношение"]
]

fig5 = go.Figure()

fig5.add_trace(go.Bar(
    name="Соотношение повторов к уникальным",
    x=scout_ratio["Скаут"].tolist(),
    y=scout_ratio["Соотношение"].tolist(),
    marker_color=colors_ratio,
    text=[f"{r:.2f}" for r in scout_ratio["Соотношение"]],
    textposition="outside",
    hovertemplate=(
        "<b>%{x}</b><br>"
        "Соотношение: %{y:.2f}<br>"
        "<extra></extra>"
    )
))

# Линия медианы
fig5.add_hline(
    y=median_ratio,
    line_dash="dash",
    line_color="#FF4B4B",
    line_width=2,
    annotation_text=f"Медиана: {median_ratio:.2f}",
    annotation_position="top right",
    annotation_font_color="#FF4B4B"
)

fig5.update_layout(
    title="Соотношение повторов к уникальным лидам (повторы / уникальные)",
    height=520,
    xaxis_tickangle=-45,
    yaxis_title="Повторов на 1 уникального лида",
    xaxis_title="Скаут",
    showlegend=False,
    margin=dict(t=80, b=120)
)

st.plotly_chart(fig5, width='stretch')

# Мини-таблица под графиком
with st.expander("📋 Детали по скаутам (соотношение)"):
    ratio_table = scout_ratio[["Скаут", "Уникальная", "Повтор", "Соотношение"]].copy()
    ratio_table.columns = ["Скаут", "Уникальных", "Повторов", "Соотношение (повт/уник)"]
    ratio_table["Соотношение (повт/уник)"] = ratio_table["Соотношение (повт/уник)"].map("{:.2f}".format)
    st.dataframe(ratio_table, hide_index=True, width='stretch')

# --- Таблица ---
with st.expander("📋 Данные по месяцам (таблица)"):
    table = pd.DataFrame({
        "Период": months_order,
        "Всего": [total_by_month.get(m, 0) for m in months_order],
        "Уникальных": [unique_by_month.get(m, 0) for m in months_order],
        "Повторов": [repeat_by_month.get(m, 0) for m in months_order],
        "Доля уникальных": [
            f"{unique_by_month.get(m, 0) / total_by_month.get(m, 1) * 100:.1f}%"
            for m in months_order
        ]
    })
    st.dataframe(table, width='stretch', hide_index=True)
