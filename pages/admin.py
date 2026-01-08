import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="S.M.A.R.T. Admin", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Tlačítko zpět
if st.sidebar.button("⬅️ Zpět do chatu"):
    st.switch_page("app.py")

st.title("🔒 Administrace systému")

try:
    users_df = conn.read(worksheet="Users", ttl=0)
    stats_df = conn.read(worksheet="Stats", ttl=0)
    
    total_used = stats_df['used'].astype(int).sum()
    limit_max = 200

    col1, col2, col3 = st.columns(3)
    col1.metric("Celkem zpráv", total_used)
    col2.metric("Zařízení", users_df['user_id'].nunique() if not users_df.empty else 0)
    col3.metric("Limit Flash", f"{total_used}/200")

    st.write("**Vytížení High-Speed režimu:**")
    st.progress(min(total_used / limit_max, 1.0))

    st.divider()
    st.subheader("🔑 Statistiky API klíčů")
    
    cols = st.columns(5)
    for i in range(1, 11):
        with cols[(i-1)%5]:
            row = stats_df[stats_df['key_id'].astype(str) == str(i)]
            val = int(row['used'].iloc[0]) if not row.empty else 0
            color = "green" if val < 20 else "red"
            st.markdown(f"<div style='border:1px solid #444; padding:10px; border-radius:10px; text-align:center;'>Klíč {i}<br><b style='color:{color};'>{val}/20</b></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🕵️ Live Spy Prohlížeč")
    if not users_df.empty:
        selected_user = st.selectbox("Vyberte ID zařízení:", users_df['user_id'].unique())
        user_data = users_df[users_df['user_id'] == selected_user]
        st.dataframe(user_data, use_container_width=True)
    else:
        st.info("Žádná data k zobrazení.")

except Exception as e:
    st.error(f"Chyba při načítání databáze: {e}")
