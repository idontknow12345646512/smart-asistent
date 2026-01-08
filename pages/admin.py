import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="S.M.A.R.T. Admin PRO", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOGIN ---
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

with st.sidebar:
    pwd = st.text_input("Admin Heslo", type="password")
    if st.button("Přihlásit"):
        if pwd == st.secrets.get("ADMIN_PASSWORD"):
            st.session_state.admin_auth = True
            st.rerun()

if not st.session_state.admin_auth:
    st.warning("Přístup odepřen. Zadejte heslo.")
    st.stop()

# --- ADMIN OBSAH ---
st.title("🔒 S.M.A.R.T. OS - Centrála")

users_df = conn.read(worksheet="Users", ttl=0)
stats_df = conn.read(worksheet="Stats", ttl=0)

# STATISTIKY KLÍČŮ
st.subheader("🔑 Stav API klíčů")
total_msgs = stats_df['used'].astype(int).sum() if not stats_df.empty else 0
limit_max = 200 # 10 klíčů x 20

# Ukazatel celkové kapacity
st.write(f"Celkové využití High-Speed modelu: {total_msgs} / {limit_max}")
st.progress(min(total_msgs / limit_max, 1.0))

cols = st.columns(5)
for i, row in stats_df.iterrows():
    with cols[i % 5]:
        val = int(row['used'])
        color = "green" if val < 20 else "red"
        st.markdown(f"""
            <div style="border: 1px solid #333; padding: 10px; border-radius: 10px; text-align: center;">
                <small>Klíč {row['key_id']}</small><br>
                <b style="color: {color}; font-size: 1.2rem;">{val}</b> / 20
            </div>
        """, unsafe_allow_html=True)

st.divider()

# PROHLÍŽEČ ZPRÁV
st.subheader("📂 Historie zpráv")
if not users_df.empty:
    # Filtry
    u_list = users_df['user_id'].unique()
    target_user = st.selectbox("Vyberte zařízení (Device ID):", u_list)
    
    filtered = users_df[users_df['user_id'] == target_user]
    
    for chat_id in filtered['chat_id'].unique():
        c_data = filtered[filtered['chat_id'] == chat_id]
        with st.expander(f"📄 Chat: {c_data['title'].iloc[0]} ({len(c_data)} zpráv)"):
            for _, msg in c_data.iterrows():
                icon = "👤" if msg['role'] == "user" else "🤖"
                st.markdown(f"**{icon} {msg['role'].upper()}** <small style='color:gray'>{msg['timestamp']}</small>", unsafe_allow_html=True)
                st.write(msg['content'])
                st.divider()
else:
    st.info("Žádná data k zobrazení.")
