import streamlit as st

st.set_page_config(
    page_title="Analytics Hub",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Analytics Hub")
st.markdown("Выбери раздел в меню слева:")
st.page_link("pages/1_📊_TT_IG_Scout_Dashboard.py", label="TT/IG Scout Dashboard", icon="📊")
st.page_link("pages/3_📩_Sales_Email_Analytics.py", label="Sales Email Analytics", icon="📩")
st.page_link("pages/4_💰_Sales_Statistics.py", label="Sales Statistics", icon="💰")
st.page_link("pages/5_🔍_Sales_Email_Status.py", label="Sales Email Status", icon="🔍")
st.page_link("pages/6_📅_Weekly_Scout_Dashboard.py", label="Weekly Scout Dashboard", icon="📅")
