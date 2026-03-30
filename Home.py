import streamlit as st

st.set_page_config(
    page_title="Analytics Hub",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Analytics Hub")
st.markdown("Выбери раздел в меню слева:")
st.page_link("pages/1_📊_TT_IG_Scout_Dashboard.py", label="📊 TT/IG Scout Dashboard", icon="📊")
st.page_link("pages/2_📧_General_Scout_Dashboard.py", label="📧 General Scout Dashboard", icon="📧")
st.page_link("pages/3_📩_Email_Analytics.py", label="📩 Email Analytics", icon="📩")
