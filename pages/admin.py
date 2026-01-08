import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Admin Monitoring", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

pwd = st.sidebar.text_input("Vstupní heslo", type="password")
if pwd == st.secrets.get("ADMIN_PASSWORD"):
    st.title("🔐 S.M.A.R.T. OS - Admin")
    
    # 1. LIVE STATISTIKY KLÍČŮ
    st.subheader("📊 Využití klíčů (Live z tabulky)")
    stats_df = conn.read(worksheet="Stats", ttl=0)
    st.dataframe(stats_df, use_container_width=True)

    # 2. LIVE SPY (Všechny zprávy všech lidí)
    st.subheader("🕵️ Live Spy - Historie všech uživatelů")
    users_df = conn.read(worksheet="Users", ttl=0)
    
    selected_user = st.selectbox("Vyber uživatele:", users_df['user_id'].unique())
    user_data = users_df[users_df['user_id'] == selected_user]
    
    for chat_id in user_data['chat_id'].unique():
        c_msgs = user_data[user_data['chat_id'] == chat_id]
        with st.expander(f"Chat: {c_msgs['title'].iloc[0]} (ID: {chat_id})"):
            for _, m in c_msgs.iterrows():
                st.text(f"[{m['timestamp']}] {m['role']}: {m['content']}")
else:
    st.info("Zadejte admin heslo pro zobrazení statistik.")
