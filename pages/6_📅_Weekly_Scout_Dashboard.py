"""
Weekly Scout Dashboard - Еженедельная аналитика скаутинга

Данные из Google Sheets "Weekly Report"
Графики:
1. Добавлено в Snovio / Snovio ответы / CR в ответ
2. Контакты не через Snovio / Ответы не через Snovio / CR в ответ
3. Получено ответов без повторов / Согласовано / CR в согласование
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import streamlit as st
import os
from datetime import datetime, timedelta

# --- Настройки страницы (только при прямом запуске) ---
if __name__ == "__main__" or not hasattr(st, "_page_config_set"):
    try:
        st.set_page_config(
            page_title="Weekly Scout Dashboard",
            page_icon="📅",
            layout="wide"
        )
    except Exception:
        pass

# --- Константы ---
# Путь к файлу данных (в prod репозитории данные в папке data/)
SNOVIO_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "weekly_report.csv")

@st.cache_data
def load_snovio_data():
    """Загружает CSV с данными Weekly Report для Snovio."""
    if not os.path.exists(SNOVIO_DATA_FILE):
        # Если файла нет, пытаемся загрузить данные
        st.warning(f"Файл {SNOVIO_DATA_FILE} не найден. Запустите fetch_weekly_report.py")
        return pd.DataFrame()
    
    df = pd.read_csv(SNOVIO_DATA_FILE, parse_dates=["date"])
    
    # Преобразуем скаутов: если содержит "Не работа" → "Other"
    # Регистронезависимая проверка
    def normalize_scout(name):
        if isinstance(name, str):
            # Проверяем различные варианты написания
            lower_name = name.lower()
            if 'не работ' in lower_name:
                return "Other"
        return name
    
    df["scout_original"] = df["scout"]  # Сохраняем оригинальное значение
    df["scout"] = df["scout"].apply(normalize_scout)
    
    # Сортируем по дате
    df = df.sort_values(["date", "scout"])
    
    # Преобразуем дату в строку для отображения (неделя)
    df["week"] = df["date"].dt.strftime("%d.%m.%Y")
    # date - это понедельник, но данные относятся к ПРЕДЫДУЩЕЙ неделе
    # week_start = понедельник предыдущей недели
    df["week_start"] = df["date"] - pd.to_timedelta(7, unit='D')
    # Формат: "24.03 – 30.03.2026" (понедельник – воскресенье с годом)
    df["week_label"] = df["week_start"].dt.strftime("%d.%m") + " – " + (df["week_start"] + pd.Timedelta(days=6)).dt.strftime("%d.%m.%Y")
    
    # Для удобства группировки
    df["year_week"] = df["date"].dt.strftime("%Y-%W")
    
    return df


# --- Загрузка данных ---
df_snovio = load_snovio_data()

# --- Заголовок ---
st.title("📅 Weekly Scout Dashboard")
st.markdown("**Еженедельная аналитика скаутинга**")
st.markdown("Данные из листа 'Weekly Report' Google Sheets")

# --- Информация об актуальности данных ---
if not df_snovio.empty:
    try:
        snovio_mtime = os.path.getmtime(SNOVIO_DATA_FILE)
        snovio_updated = datetime.fromtimestamp(snovio_mtime).strftime("%d.%m.%Y %H:%M")
        st.caption(f"🕐 Данные обновлены: **{snovio_updated}**")
    except:
        st.caption("🕐 Время обновления данных неизвестно")
    
    # Статистика
    total_weeks = df_snovio["date"].nunique()
    total_scouts = df_snovio["scout"].nunique()
    total_snovio_added = df_snovio["snovio_added"].sum()
    total_snovio_replies = df_snovio["snovio_replies"].sum()
    
    # Вычисляем метрики для других контактов
    total_added_other = df_snovio["wa_contacts"].sum() + df_snovio["direct_tt"].sum() + df_snovio["direct_tt_ig"].sum() + df_snovio["direct_ig"].sum()
    total_replies_other = df_snovio["direct_replies_tt"].sum() + df_snovio["direct_replies_tt_ig"].sum() + df_snovio["direct_replies_ig"].sum() + df_snovio["direct_replies_sc"].sum()
    
    # Вычисляем метрики для нового графика
    total_replies_without_repeats = df_snovio["replies_without_repeats"].sum()
    total_agreed = df_snovio["agreed"].sum()
    total_agreement_cr = round(total_agreed / total_replies_without_repeats * 100, 2) if total_replies_without_repeats > 0 else 0
    
    # CR для других контактов
    total_cr_other = round(total_replies_other / total_added_other * 100, 2) if total_added_other > 0 else 0
    
    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)
    col1.metric("Недель данных", total_weeks)
    col2.metric("Скаутов", total_scouts)
    col3.metric("Добавлено в Snovio", f"{total_snovio_added:,}")
    col4.metric("Ответов Snovio", f"{total_snovio_replies:,}")
    col5.metric("Контактов (не Snovio)", f"{total_added_other:,}")
    col6.metric("Ответов (не Snovio)", f"{total_replies_other:,}")
    col7.metric("Ответов без повторов", f"{total_replies_without_repeats:,}")
    col8.metric("Согласовано", f"{total_agreed:,}")
    col9.metric("CR в согласование", f"{total_agreement_cr:,}%")
    
    st.divider()

# --- График: Добавлено в Snovio / Snovio ответы / CR в ответ ---
st.subheader("📊 Добавлено в Snovio / Snovio ответы / CR в ответ")

if df_snovio.empty:
    st.info("📭 Нет данных Snovio. Запустите fetch_weekly_report.py для загрузки данных из Google Sheets.")
    st.stop()

# Фильтры для Snovio
col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    # Выбор скаутов
    all_snovio_scouts = sorted(df_snovio["scout"].unique().tolist())
    # Добавляем "Other" если ещё нет (для будущих данных "Не работают")
    if "Other" not in all_snovio_scouts:
        all_snovio_scouts.append("Other")
        all_snovio_scouts.sort()
    
    selected_snovio_scouts = st.multiselect(
        "Скауты:",
        options=all_snovio_scouts,
        default=all_snovio_scouts,
        help="Выбери скаутов для анализа"
    )

with col_s2:
    # Выбор недель
    # Создаем словарь для отображения: дата (понедельник) -> диапазон ПРЕДЫДУЩЕЙ недели
    week_display_map = {}
    for date_val in df_snovio["date"].unique():
        week_start = date_val - pd.to_timedelta(7, unit='D')
        week_label = week_start.strftime("%d.%m") + " – " + (week_start + pd.Timedelta(days=6)).strftime("%d.%m.%Y")
        week_display_map[date_val] = week_label
    
    snovio_weeks = sorted(df_snovio["date"].unique())
    if snovio_weeks:
        default_snovio_weeks = snovio_weeks[-4:] if len(snovio_weeks) >= 4 else snovio_weeks
        selected_snovio_weeks = st.multiselect(
            "Недели:",
            options=snovio_weeks,
            default=default_snovio_weeks,
            format_func=lambda d: week_display_map[d],
            help="Выбери недели для анализа"
        )
    else:
        selected_snovio_weeks = []
        st.info("Нет данных о неделях")

with col_s3:
    # Группировка данных
    snovio_group_by = st.selectbox(
        "Группировать:",
        options=["По неделям", "По скаутам", "По неделям и скаутам"],
        index=0,
        help="Как сгруппировать данные на графике"
    )

# Применение фильтров Snovio
df_snovio_filtered = df_snovio.copy()

if selected_snovio_scouts:
    df_snovio_filtered = df_snovio_filtered[df_snovio_filtered["scout"].isin(selected_snovio_scouts)]

if selected_snovio_weeks:
    df_snovio_filtered = df_snovio_filtered[df_snovio_filtered["date"].isin(selected_snovio_weeks)]

if df_snovio_filtered.empty:
    st.warning("⚠️ Нет данных по выбранным фильтрам")
    st.stop()

# Подготовка данных в зависимости от группировки
if snovio_group_by == "По неделям":
    # Группируем по неделям
    grouped_snovio = df_snovio_filtered.groupby(["week_start", "week_label", "year_week"]).agg({
        "snovio_added": "sum",
        "snovio_replies": "sum",
        "scout": "nunique"
    }).reset_index()
    
    grouped_snovio = grouped_snovio.sort_values("week_start")
    
    # Вычисляем CR (ограничиваем максимум 100%)
    grouped_snovio["snovio_cr"] = grouped_snovio.apply(
        lambda x: min(round(x["snovio_replies"] / x["snovio_added"] * 100, 2), 100) if x["snovio_added"] > 0 else 0,
        axis=1
    )
    
    x_data = grouped_snovio["week_label"].tolist()
    x_title = "Неделя"
    
elif snovio_group_by == "По скаутам":
    # Группируем по скаутам
    grouped_snovio = df_snovio_filtered.groupby("scout").agg({
        "snovio_added": "sum",
        "snovio_replies": "sum",
        "date": "nunique"
    }).reset_index()
    
    grouped_snovio = grouped_snovio.sort_values("snovio_added", ascending=False)
    
    # Вычисляем CR
    grouped_snovio["snovio_cr"] = grouped_snovio.apply(
        lambda x: round(x["snovio_replies"] / x["snovio_added"] * 100, 2) if x["snovio_added"] > 0 else 0,
        axis=1
    )
    
    x_data = grouped_snovio["scout"].tolist()
    x_title = "Скаут"
    
else:  # "По неделям и скаутам"
    # Группируем по неделям и скаутам
    grouped_snovio = df_snovio_filtered.copy()
    grouped_snovio = grouped_snovio.sort_values(["week_start", "scout"])
    
    # Создаем комбинированные метки
    grouped_snovio["x_label"] = grouped_snovio["week_label"] + " | " + grouped_snovio["scout"]
    
    x_data = grouped_snovio["x_label"].tolist()
    x_title = "Неделя | Скаут"

# Создаем график с двумя осями Y
fig_snovio = sp.make_subplots(
    specs=[[{"secondary_y": True}]],
    subplot_titles=(f"Аналитика Snovio ({snovio_group_by.lower()})",)
)

if snovio_group_by == "По неделям и скаутам":
    # Для детализированного отображения
    fig_snovio.add_trace(
        go.Bar(
            name="Добавлено в Snovio",
            x=x_data,
            y=grouped_snovio["snovio_added"].tolist(),
            marker_color="#4A90D9",
            text=grouped_snovio["snovio_added"].tolist(),
            textposition="outside",
            textfont=dict(size=10),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Добавлено: %{y}<br>"
                "Ответов: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_snovio["snovio_replies"].tolist(),
                grouped_snovio["snovio_cr"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_snovio.add_trace(
        go.Bar(
            name="Ответы Snovio",
            x=x_data,
            y=grouped_snovio["snovio_replies"].tolist(),
            marker_color="#E8A838",
            text=grouped_snovio["snovio_replies"].tolist(),
            textposition="inside",
            textfont=dict(size=10, color="white"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Ответов: %{y}<br>"
                "Добавлено: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_snovio["snovio_added"].tolist(),
                grouped_snovio["snovio_cr"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_snovio.add_trace(
        go.Scatter(
            name="CR в ответ (%)",
            x=x_data,
            y=grouped_snovio["snovio_cr"].tolist(),
            mode="lines+markers+text",
            line=dict(color="#FF4B4B", width=2),
            marker=dict(size=8, color="#FF4B4B"),
            text=[f"{cr:.1f}%" for cr in grouped_snovio["snovio_cr"].tolist()],
            textposition="top center",
            textfont=dict(size=10, color="#FF4B4B"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CR: %{y:.1f}%<br>"
                "Добавлено: %{customdata[0]}<br>"
                "Ответов: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_snovio["snovio_added"].tolist(),
                grouped_snovio["snovio_replies"].tolist()
            ))
        ),
        secondary_y=True
    )
    
    fig_snovio.update_layout(
        barmode="overlay",
        bargap=0.3,
        bargroupgap=0.1,
        xaxis_tickangle=-45,
        height=600,
    )
    
else:
    # Для агрегированного отображения
    fig_snovio.add_trace(
        go.Bar(
            name="Добавлено в Snovio",
            x=x_data,
            y=grouped_snovio["snovio_added"].tolist(),
            marker_color="#4A90D9",
            text=grouped_snovio["snovio_added"].tolist(),
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Добавлено: %{y}<br>"
                "Ответов: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<br>"
                "Скаутов: %{customdata[2]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_snovio["snovio_replies"].tolist(),
                grouped_snovio["snovio_cr"].tolist(),
                grouped_snovio.get("scout", [0] * len(grouped_snovio)) if snovio_group_by == "По неделям" else grouped_snovio.get("date", [0] * len(grouped_snovio))
            ))
        ),
        secondary_y=False
    )
    
    fig_snovio.add_trace(
        go.Bar(
            name="Ответы Snovio",
            x=x_data,
            y=grouped_snovio["snovio_replies"].tolist(),
            marker_color="#E8A838",
            text=grouped_snovio["snovio_replies"].tolist(),
            textposition="inside",
            textfont=dict(color="white"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Ответов: %{y}<br>"
                "Добавлено: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_snovio["snovio_added"].tolist(),
                grouped_snovio["snovio_cr"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_snovio.add_trace(
        go.Scatter(
            name="CR в ответ (%)",
            x=x_data,
            y=grouped_snovio["snovio_cr"].tolist(),
            mode="lines+markers+text",
            line=dict(color="#FF4B4B", width=3),
            marker=dict(size=10, color="#FF4B4B"),
            text=[f"{cr:.1f}%" for cr in grouped_snovio["snovio_cr"].tolist()],
            textposition="top center",
            textfont=dict(size=12, color="#FF4B4B"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CR: %{y:.1f}%<br>"
                "Добавлено: %{customdata[0]}<br>"
                "Ответов: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_snovio["snovio_added"].tolist(),
                grouped_snovio["snovio_replies"].tolist()
            ))
        ),
        secondary_y=True
    )
    
    fig_snovio.update_layout(
        barmode="overlay",
        bargap=0.2,
        height=550,
    )

# Общие настройки графика
fig_snovio.update_layout(
    title=f"Добавлено в Snovio / Snovio ответы / CR в ответ ({snovio_group_by.lower()})",
    xaxis_title=x_title,
    yaxis_title="Количество (шт)",
    yaxis2_title="CR в ответ (%)",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode="x unified"
)

# Настройка осей
fig_snovio.update_yaxes(title_text="Количество (шт)", secondary_y=False)
fig_snovio.update_yaxes(title_text="CR в ответ (%)", secondary_y=True, range=[0, 120])

st.plotly_chart(fig_snovio, use_container_width=True)

st.divider()

# --- График: Контакты не через Snovio / Ответы не через Snovio / CR в ответ ---
st.subheader("📊 Контакты не через Snovio / Ответы не через Snovio / CR в ответ")

# Вычисляем метрики для других контактов (J+M+N+O / P+Q+R+S)
df_other_filtered = df_snovio_filtered.copy()

# Добавлено контактов (другое) = wa_contacts + direct_tt + direct_tt_ig + direct_ig
df_other_filtered["added_other"] = df_other_filtered["wa_contacts"] + df_other_filtered["direct_tt"] + df_other_filtered["direct_tt_ig"] + df_other_filtered["direct_ig"]

# Ответов (другое) = direct_replies_tt + direct_replies_tt_ig + direct_replies_ig + direct_replies_sc
df_other_filtered["replies_other"] = df_other_filtered["direct_replies_tt"] + df_other_filtered["direct_replies_tt_ig"] + df_other_filtered["direct_replies_ig"] + df_other_filtered["direct_replies_sc"]

# CR в ответ
if df_other_filtered["added_other"].sum() > 0:
    df_other_filtered["cr_other"] = df_other_filtered.apply(
        lambda x: round(x["replies_other"] / x["added_other"] * 100, 2) if x["added_other"] > 0 else 0,
        axis=1
    )
else:
    df_other_filtered["cr_other"] = 0

# Подготовка данных в зависимости от группировки (та же логика что и для Snovio)
if snovio_group_by == "По неделям":
    # Группируем по неделям
    grouped_other = df_other_filtered.groupby(["week_start", "week_label", "year_week"]).agg({
        "added_other": "sum",
        "replies_other": "sum",
        "scout": "nunique"
    }).reset_index()
    
    grouped_other = grouped_other.sort_values("week_start")
    
    # Вычисляем CR
    grouped_other["cr_other"] = grouped_other.apply(
        lambda x: round(x["replies_other"] / x["added_other"] * 100, 2) if x["added_other"] > 0 else 0,
        axis=1
    )
    
    x_data_other = grouped_other["week_label"].tolist()
    x_title_other = "Неделя"
    
elif snovio_group_by == "По скаутам":
    # Группируем по скаутам
    grouped_other = df_other_filtered.groupby("scout").agg({
        "added_other": "sum",
        "replies_other": "sum",
        "date": "nunique"
    }).reset_index()
    
    grouped_other = grouped_other.sort_values("added_other", ascending=False)
    
    # Вычисляем CR
    grouped_other["cr_other"] = grouped_other.apply(
        lambda x: round(x["replies_other"] / x["added_other"] * 100, 2) if x["added_other"] > 0 else 0,
        axis=1
    )
    
    x_data_other = grouped_other["scout"].tolist()
    x_title_other = "Скаут"
    
else:  # "По неделям и скаутам"
    # Группируем по неделям и скаутам
    grouped_other = df_other_filtered.copy()
    grouped_other = grouped_other.sort_values(["week_start", "scout"])
    
    # Создаем комбинированные метки
    grouped_other["x_label_other"] = grouped_other["week_label"] + " | " + grouped_other["scout"]
    
    x_data_other = grouped_other["x_label_other"].tolist()
    x_title_other = "Неделя | Скаут"

# Создаем график с двумя осями Y
fig_other = sp.make_subplots(
    specs=[[{"secondary_y": True}]],
    subplot_titles=(f"Контакты не через Snovio ({snovio_group_by.lower()})",)
)

if snovio_group_by == "По неделям и скаутам":
    # Для детализированного отображения
    fig_other.add_trace(
        go.Bar(
            name="Добавлено контактов (не Snovio)",
            x=x_data_other,
            y=grouped_other["added_other"].tolist(),
            marker_color="#2E86AB",
            text=grouped_other["added_other"].tolist(),
            textposition="outside",
            textfont=dict(size=10),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Добавлено: %{y}<br>"
                "Ответов: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_other["replies_other"].tolist(),
                grouped_other["cr_other"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_other.add_trace(
        go.Bar(
            name="Ответов (не Snovio)",
            x=x_data_other,
            y=grouped_other["replies_other"].tolist(),
            marker_color="#A23B72",
            text=grouped_other["replies_other"].tolist(),
            textposition="inside",
            textfont=dict(size=10, color="white"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Ответов: %{y}<br>"
                "Добавлено: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_other["added_other"].tolist(),
                grouped_other["cr_other"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_other.add_trace(
        go.Scatter(
            name="CR в ответ (%)",
            x=x_data_other,
            y=grouped_other["cr_other"].tolist(),
            mode="lines+markers+text",
            line=dict(color="#F18F01", width=2),
            marker=dict(size=8, color="#F18F01"),
            text=[f"{cr:.1f}%" for cr in grouped_other["cr_other"].tolist()],
            textposition="top center",
            textfont=dict(size=10, color="#F18F01"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CR: %{y:.1f}%<br>"
                "Добавлено: %{customdata[0]}<br>"
                "Ответов: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_other["added_other"].tolist(),
                grouped_other["replies_other"].tolist()
            ))
        ),
        secondary_y=True
    )
    
    fig_other.update_layout(
        barmode="overlay",
        bargap=0.3,
        bargroupgap=0.1,
        xaxis_tickangle=-45,
        height=600,
    )
    
else:
    # Для агрегированного отображения
    fig_other.add_trace(
        go.Bar(
            name="Добавлено контактов (не Snovio)",
            x=x_data_other,
            y=grouped_other["added_other"].tolist(),
            marker_color="#2E86AB",
            text=grouped_other["added_other"].tolist(),
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Добавлено: %{y}<br>"
                "Ответов: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<br>"
                "Скаутов: %{customdata[2]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_other["replies_other"].tolist(),
                grouped_other["cr_other"].tolist(),
                grouped_other.get("scout", [0] * len(grouped_other)) if snovio_group_by == "По неделям" else grouped_other.get("date", [0] * len(grouped_other))
            ))
        ),
        secondary_y=False
    )
    
    fig_other.add_trace(
        go.Bar(
            name="Ответов (не Snovio)",
            x=x_data_other,
            y=grouped_other["replies_other"].tolist(),
            marker_color="#A23B72",
            text=grouped_other["replies_other"].tolist(),
            textposition="inside",
            textfont=dict(color="white"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Ответов: %{y}<br>"
                "Добавлено: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_other["added_other"].tolist(),
                grouped_other["cr_other"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_other.add_trace(
        go.Scatter(
            name="CR в ответ (%)",
            x=x_data_other,
            y=grouped_other["cr_other"].tolist(),
            mode="lines+markers+text",
            line=dict(color="#F18F01", width=3),
            marker=dict(size=10, color="#F18F01"),
            text=[f"{cr:.1f}%" for cr in grouped_other["cr_other"].tolist()],
            textposition="top center",
            textfont=dict(size=12, color="#F18F01"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CR: %{y:.1f}%<br>"
                "Добавлено: %{customdata[0]}<br>"
                "Ответов: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_other["added_other"].tolist(),
                grouped_other["replies_other"].tolist()
            ))
        ),
        secondary_y=True
    )
    
    fig_other.update_layout(
        barmode="overlay",
        bargap=0.2,
        height=550,
    )

# Общие настройки графика
fig_other.update_layout(
    title=f"Контакты не через Snovio / Ответы не через Snovio / CR в ответ ({snovio_group_by.lower()})",
    xaxis_title=x_title_other,
    yaxis_title="Количество (шт)",
    yaxis2_title="CR в ответ (%)",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode="x unified"
)

# Настройка осей
fig_other.update_yaxes(title_text="Количество (шт)", secondary_y=False)
fig_other.update_yaxes(title_text="CR в ответ (%)", secondary_y=True, range=[0, 120])

st.plotly_chart(fig_other, use_container_width=True)

st.divider()

# --- График: Получено ответов без повторов / Согласовано / CR в согласование ---
st.subheader("📈 Получено ответов без повторов / Согласовано / CR в согласование")

# Используем те же отфильтрованные данные
df_agreement_filtered = df_snovio_filtered.copy()

# Подготовка данных в зависимости от группировки (та же логика что и для предыдущих графиков)
if snovio_group_by == "По неделям":
    # Группируем по неделям
    grouped_agreement = df_agreement_filtered.groupby(["week_start", "week_label", "year_week"]).agg({
        "replies_without_repeats": "sum",
        "agreed": "sum",
        "scout": "nunique"
    }).reset_index()
    
    grouped_agreement = grouped_agreement.sort_values("week_start")
    
    # Вычисляем CR в согласование
    grouped_agreement["agreement_cr"] = grouped_agreement.apply(
        lambda x: round(x["agreed"] / x["replies_without_repeats"] * 100, 2) if x["replies_without_repeats"] > 0 else 0,
        axis=1
    )
    
    x_data_agreement = grouped_agreement["week_label"].tolist()
    x_title_agreement = "Неделя"
    
elif snovio_group_by == "По скаутам":
    # Группируем по скаутам
    grouped_agreement = df_agreement_filtered.groupby("scout").agg({
        "replies_without_repeats": "sum",
        "agreed": "sum",
        "date": "nunique"
    }).reset_index()
    
    grouped_agreement = grouped_agreement.sort_values("replies_without_repeats", ascending=False)
    
    # Вычисляем CR в согласование
    grouped_agreement["agreement_cr"] = grouped_agreement.apply(
        lambda x: round(x["agreed"] / x["replies_without_repeats"] * 100, 2) if x["replies_without_repeats"] > 0 else 0,
        axis=1
    )
    
    x_data_agreement = grouped_agreement["scout"].tolist()
    x_title_agreement = "Скаут"
    
else:  # "По неделям и скаутам"
    # Группируем по неделям и скаутам
    grouped_agreement = df_agreement_filtered.copy()
    grouped_agreement = grouped_agreement.sort_values(["week_start", "scout"])
    
    # Создаем комбинированные метки
    grouped_agreement["x_label_agreement"] = grouped_agreement["week_label"] + " | " + grouped_agreement["scout"]
    
    x_data_agreement = grouped_agreement["x_label_agreement"].tolist()
    x_title_agreement = "Неделя | Скаут"

# Создаем график с двумя осями Y
fig_agreement = sp.make_subplots(
    specs=[[{"secondary_y": True}]],
    subplot_titles=(f"Ответы без повторов / Согласовано ({snovio_group_by.lower()})",)
)

if snovio_group_by == "По неделям и скаутам":
    # Для детализированного отображения
    fig_agreement.add_trace(
        go.Bar(
            name="Ответов без повторов",
            x=x_data_agreement,
            y=grouped_agreement["replies_without_repeats"].tolist(),
            marker_color="#34A853",  # Зелёный
            text=grouped_agreement["replies_without_repeats"].tolist(),
            textposition="outside",
            textfont=dict(size=10),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Ответов без повторов: %{y}<br>"
                "Согласовано: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_agreement["agreed"].tolist(),
                grouped_agreement["agreement_cr"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_agreement.add_trace(
        go.Bar(
            name="Согласовано",
            x=x_data_agreement,
            y=grouped_agreement["agreed"].tolist(),
            marker_color="#9334E6",  # Фиолетовый
            text=grouped_agreement["agreed"].tolist(),
            textposition="inside",
            textfont=dict(size=10, color="white"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Согласовано: %{y}<br>"
                "Ответов без повторов: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_agreement["replies_without_repeats"].tolist(),
                grouped_agreement["agreement_cr"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_agreement.add_trace(
        go.Scatter(
            name="CR в согласование (%)",
            x=x_data_agreement,
            y=grouped_agreement["agreement_cr"].tolist(),
            mode="lines+markers+text",
            line=dict(color="#FBBC05", width=2),  # Жёлтый
            marker=dict(size=8, color="#FBBC05"),
            text=[f"{cr:.1f}%" for cr in grouped_agreement["agreement_cr"].tolist()],
            textposition="top center",
            textfont=dict(size=10, color="#FBBC05"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CR: %{y:.1f}%<br>"
                "Ответов без повторов: %{customdata[0]}<br>"
                "Согласовано: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_agreement["replies_without_repeats"].tolist(),
                grouped_agreement["agreed"].tolist()
            ))
        ),
        secondary_y=True
    )
    
    fig_agreement.update_layout(
        barmode="overlay",
        bargap=0.3,
        bargroupgap=0.1,
        xaxis_tickangle=-45,
        height=600,
    )
    
else:
    # Для агрегированного отображения
    fig_agreement.add_trace(
        go.Bar(
            name="Ответов без повторов",
            x=x_data_agreement,
            y=grouped_agreement["replies_without_repeats"].tolist(),
            marker_color="#34A853",
            text=grouped_agreement["replies_without_repeats"].tolist(),
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Ответов без повторов: %{y}<br>"
                "Согласовано: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<br>"
                "Скаутов: %{customdata[2]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_agreement["agreed"].tolist(),
                grouped_agreement["agreement_cr"].tolist(),
                grouped_agreement.get("scout", [0] * len(grouped_agreement)) if snovio_group_by == "По неделям" else grouped_agreement.get("date", [0] * len(grouped_agreement))
            ))
        ),
        secondary_y=False
    )
    
    fig_agreement.add_trace(
        go.Bar(
            name="Согласовано",
            x=x_data_agreement,
            y=grouped_agreement["agreed"].tolist(),
            marker_color="#9334E6",
            text=grouped_agreement["agreed"].tolist(),
            textposition="inside",
            textfont=dict(color="white"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Согласовано: %{y}<br>"
                "Ответов без повторов: %{customdata[0]}<br>"
                "CR: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                grouped_agreement["replies_without_repeats"].tolist(),
                grouped_agreement["agreement_cr"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    fig_agreement.add_trace(
        go.Scatter(
            name="CR в согласование (%)",
            x=x_data_agreement,
            y=grouped_agreement["agreement_cr"].tolist(),
            mode="lines+markers+text",
            line=dict(color="#FBBC05", width=3),
            marker=dict(size=10, color="#FBBC05"),
            text=[f"{cr:.1f}%" for cr in grouped_agreement["agreement_cr"].tolist()],
            textposition="top center",
            textfont=dict(size=12, color="#FBBC05"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CR: %{y:.1f}%<br>"
                "Ответов без повторов: %{customdata[0]}<br>"
                "Согласовано: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(
                grouped_agreement["replies_without_repeats"].tolist(),
                grouped_agreement["agreed"].tolist()
            ))
        ),
        secondary_y=True
    )
    
    fig_agreement.update_layout(
        barmode="overlay",
        bargap=0.2,
        height=550,
    )

# Общие настройки графика
fig_agreement.update_layout(
    title=f"Получено ответов без повторов / Согласовано / CR в согласование ({snovio_group_by.lower()})",
    xaxis_title=x_title_agreement,
    yaxis_title="Количество (шт)",
    yaxis2_title="CR в согласование (%)",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode="x unified"
)

# Настройка осей
fig_agreement.update_yaxes(title_text="Количество (шт)", secondary_y=False)
fig_agreement.update_yaxes(title_text="CR в согласование (%)", secondary_y=True, range=[0, 120])

st.plotly_chart(fig_agreement, use_container_width=True)

st.divider()

# --- Дополнительная информация ---
st.subheader("📈 Статистика по выбранным данным")

if snovio_group_by == "По неделям":
    # Показываем таблицу с данными по неделям
    display_df = grouped_snovio[["week_label", "snovio_added", "snovio_replies", "snovio_cr", "scout"]].copy()
    display_df.columns = ["Неделя", "Добавлено в Snovio", "Ответов Snovio", "CR (%)", "Кол-во скаутов"]
    display_df["CR (%)"] = display_df["CR (%)"].map(lambda x: f"{x:.1f}%")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with col2:
        # Сводная статистика
        avg_cr = grouped_snovio["snovio_cr"].mean()
        max_cr = grouped_snovio["snovio_cr"].max()
        min_cr = grouped_snovio["snovio_cr"].min()
        
        st.metric("Средний CR", f"{avg_cr:.1f}%")
        st.metric("Максимальный CR", f"{max_cr:.1f}%")
        st.metric("Минимальный CR", f"{min_cr:.1f}%")

elif snovio_group_by == "По скаутам":
    # Показываем таблицу с данными по скаутам
    display_df = grouped_snovio[["scout", "snovio_added", "snovio_replies", "snovio_cr", "date"]].copy()
    display_df.columns = ["Скаут", "Добавлено в Snovio", "Ответов Snovio", "CR (%)", "Недель работы"]
    display_df["CR (%)"] = display_df["CR (%)"].map(lambda x: f"{x:.1f}%")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Топ-5 скаутов по CR
    top_cr = display_df.nlargest(5, "CR (%)")
    st.caption("🏆 Топ-5 скаутов по CR:")
    for i, row in top_cr.iterrows():
        st.markdown(f"- **{row['Скаут']}**: {row['CR (%)']} (добавлено: {row['Добавлено в Snovio']}, ответов: {row['Ответов Snovio']})")

else:  # "По неделям и скаутам"
    # Показываем детальную таблицу
    display_df = grouped_snovio[["week_label", "scout", "snovio_added", "snovio_replies", "snovio_cr"]].copy()
    display_df.columns = ["Неделя", "Скаут", "Добавлено в Snovio", "Ответов Snovio", "CR (%)"]
    display_df["CR (%)"] = display_df["CR (%)"].map(lambda x: f"{x:.1f}%")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# --- Итоговая оценка скаутов за выбранный период ---
st.divider()
st.subheader("🏆 Итоговая оценка скаутов за выбранный период")
st.markdown("**Агрегированные данные по всем выбранным неделям без разделения по времени**")

# Группируем данные по скаутам для итоговой оценки
if not df_snovio_filtered.empty:
    # Суммируем данные по скаутам за все выбранные недели
    scout_summary = df_snovio_filtered.groupby("scout").agg({
        "replies_without_repeats": "sum",
        "agreed": "sum",
        "date": "nunique",  # количество недель работы
        "snovio_added": "sum",
        "snovio_replies": "sum",
        "wa_contacts": "sum",
        "direct_tt": "sum",
        "direct_tt_ig": "sum",
        "direct_ig": "sum",
        "direct_replies_tt": "sum",
        "direct_replies_tt_ig": "sum",
        "direct_replies_ig": "sum",
        "direct_replies_sc": "sum"
    }).reset_index()
    
    # Вычисляем добавленные контакты не через Snovio
    scout_summary["added_other"] = scout_summary["wa_contacts"] + scout_summary["direct_tt"] + scout_summary["direct_tt_ig"] + scout_summary["direct_ig"]
    
    # Вычисляем ответы не через Snovio
    scout_summary["replies_other"] = scout_summary["direct_replies_tt"] + scout_summary["direct_replies_tt_ig"] + scout_summary["direct_replies_ig"] + scout_summary["direct_replies_sc"]
    
    # Вычисляем CR согласования
    scout_summary["agreement_cr"] = scout_summary.apply(
        lambda x: round(x["agreed"] / x["replies_without_repeats"] * 100, 2) if x["replies_without_repeats"] > 0 else 0,
        axis=1
    )
    
    # Вычисляем CR Snovio
    scout_summary["snovio_cr"] = scout_summary.apply(
        lambda x: round(x["snovio_replies"] / x["snovio_added"] * 100, 2) if x["snovio_added"] > 0 else 0,
        axis=1
    )
    
    # Вычисляем CR других контактов
    scout_summary["other_cr"] = scout_summary.apply(
        lambda x: round(x["replies_other"] / x["added_other"] * 100, 2) if x["added_other"] > 0 else 0,
        axis=1
    )
    
    # Сортируем по количеству согласованных (главный критерий)
    scout_summary = scout_summary.sort_values("agreed", ascending=False)
    
    # --- График: Согласовано и CR согласования по скаутам ---
    st.markdown("#### 📊 Согласованные блогеры и CR согласования")
    
    fig_scout_summary = sp.make_subplots(
        specs=[[{"secondary_y": True}]],
        subplot_titles=("Итоговые результаты по скаутам",)
    )
    
    # Столбцы: количество согласованных
    fig_scout_summary.add_trace(
        go.Bar(
            name="Согласовано",
            x=scout_summary["scout"].tolist(),
            y=scout_summary["agreed"].tolist(),
            marker_color="#34A853",  # Зелёный
            text=scout_summary["agreed"].tolist(),
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Согласовано: %{y}<br>"
                "Ответов без повторов: %{customdata[0]}<br>"
                "CR согласования: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=list(zip(
                scout_summary["replies_without_repeats"].tolist(),
                scout_summary["agreement_cr"].tolist()
            ))
        ),
        secondary_y=False
    )
    
    # Линия: CR согласования
    fig_scout_summary.add_trace(
        go.Scatter(
            name="CR согласования (%)",
            x=scout_summary["scout"].tolist(),
            y=scout_summary["agreement_cr"].tolist(),
            mode="lines+markers+text",
            line=dict(color="#FBBC05", width=3),  # Жёлтый
            marker=dict(size=10, color="#FBBC05"),
            text=[f"{cr:.1f}%" for cr in scout_summary["agreement_cr"].tolist()],
            textposition="top center",
            textfont=dict(size=11, color="#FBBC05"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "CR согласования: %{y:.1f}%<br>"
                "Согласовано: %{customdata[0]}<br>"
                "Ответов без повторов: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(
                scout_summary["agreed"].tolist(),
                scout_summary["replies_without_repeats"].tolist()
            ))
        ),
        secondary_y=True
    )
    
    # Настройки графика
    fig_scout_summary.update_layout(
        title="Согласованные блогеры и CR согласования по скаутам",
        xaxis_title="Скаут",
        yaxis_title="Количество согласованных (шт)",
        yaxis2_title="CR согласования (%)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        height=500
    )
    
    fig_scout_summary.update_yaxes(title_text="Количество согласованных (шт)", secondary_y=False)
    fig_scout_summary.update_yaxes(title_text="CR согласования (%)", secondary_y=True, range=[0, 120])
    
    st.plotly_chart(fig_scout_summary, use_container_width=True)
    
    # --- Детальная таблица по скаутам ---
    st.markdown("#### 📋 Детальная статистика по скаутам")
    
    # Создаём таблицу для отображения
    scout_display_df = scout_summary[["scout", "agreed", "replies_without_repeats", "agreement_cr", 
                                     "snovio_added", "snovio_replies", "snovio_cr",
                                     "added_other", "replies_other", "other_cr", "date"]].copy()
    
    scout_display_df.columns = ["Скаут", "Согласовано", "Ответов без повторов", "CR согласования (%)",
                               "Добавлено в Snovio", "Ответов Snovio", "CR Snovio (%)",
                               "Контактов (не Snovio)", "Ответов (не Snovio)", "CR других (%)", "Недель работы"]
    
    # Форматируем проценты
    scout_display_df["CR согласования (%)"] = scout_display_df["CR согласования (%)"].map(lambda x: f"{x:.1f}%")
    scout_display_df["CR Snovio (%)"] = scout_display_df["CR Snovio (%)"].map(lambda x: f"{x:.1f}%")
    scout_display_df["CR других (%)"] = scout_display_df["CR других (%)"].map(lambda x: f"{x:.1f}%")
    
    # Показываем таблицу
    st.dataframe(scout_display_df, use_container_width=True, hide_index=True)
    
    # --- Ключевые инсайты ---
    st.markdown("#### 💡 Ключевые инсайты")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        top_scout = scout_summary.iloc[0]["scout"] if not scout_summary.empty else "-"
        top_agreed = scout_summary.iloc[0]["agreed"] if not scout_summary.empty else 0
        st.metric("🏆 Лучший по согласованным", f"{top_scout}", f"{top_agreed} согласованных")
    
    with col2:
        if not scout_summary.empty and scout_summary["agreement_cr"].max() > 0:
            top_cr_scout = scout_summary.loc[scout_summary["agreement_cr"].idxmax(), "scout"]
            top_cr_value = scout_summary["agreement_cr"].max()
            st.metric("🎯 Лучший CR согласования", f"{top_cr_scout}", f"{top_cr_value:.1f}%")
        else:
            st.metric("🎯 Лучший CR согласования", "-", "нет данных")
    
    with col3:
        if not scout_summary.empty:
            avg_cr = scout_summary["agreement_cr"].mean()
            st.metric("📊 Средний CR согласования", f"{avg_cr:.1f}%")
        else:
            st.metric("📊 Средний CR согласования", "-", "нет данных")
    
    # Общая статистика
    st.markdown(f"**Всего за выбранный период:** {scout_summary['agreed'].sum():,} согласованных из {scout_summary['replies_without_repeats'].sum():,} ответов без повторов "
                f"(CR: {round(scout_summary['agreed'].sum() / scout_summary['replies_without_repeats'].sum() * 100, 2) if scout_summary['replies_without_repeats'].sum() > 0 else 0:.1f}%)")
else:
    st.info("📭 Нет данных для итоговой оценки. Проверь фильтры скаутов и недель.")


# --- Подвал ---
st.divider()
st.caption("Weekly Scout Dashboard • Данные из Google Sheets 'Weekly Report' • Обновление вручную")
