import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="S.M.A.R.T. Admin PRO", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- PŘIHLÁŠENÍ ---
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

with st.sidebar:
    st.title("🔐 Admin Vstup")
    pwd = st.text_input("Heslo", type="password")
    if st.button("Přihlásit"):
        if pwd == st.secrets.get("ADMIN_PASSWORD"):
            st.session_state.admin_auth = True
            st.rerun()

if not st.session_state.admin_auth:
    st.warning("Pro přístup k administraci se musíte přihlásit.")
    st.stop()

# --- HLAVNÍ ADMIN PANEL ---
st.title("🔒 S.M.A.R.T. OS - Centrální dohled")

users_df = conn.read(worksheet="Users", ttl=0)
stats_df = conn.read(worksheet="Stats", ttl=0)

# --- 1. STATISTIKY KLÍČŮ ---
st.header("📊 Využití systému")
total_msgs = stats_df['used'].astype(int).sum() if not stats_df.empty else 0
limit_max = 200

col1, col2, col3 = st.columns(3)
col1.metric("Celkem zpráv (Flash)", f"{total_msgs} / {limit_max}")
col2.metric("Aktivních zařízení", users_df['user_id'].nunique() if not users_df.empty else 0)
col3.metric("Režim", "LITE" if total_msgs >= limit_max else "HIGH-SPEED")

st.write("**Celková vytíženost Flash modelu:**")
st.progress(min(total_msgs / limit_max, 1.0))

# Mřížka klíčů
st.subheader("🔑 Jednotlivé klíče")
cols = st.columns(5)
for i in range(1, 11):
    with cols[(i-1) % 5]:
        # Najdeme hodnotu pro klíč i
        row = stats_df[stats_df['key_id'].astype(str) == str(i)]
        val = int(row['used'].iloc[0]) if not row.empty else 0
        
        color = "#28a745" if val < 20 else "#dc3545"
        st.markdown(f"""
            <div style="border: 1px solid #444; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
                <small>Klíč {i}</small><br>
                <b style="color: {color}; font-size: 1.1rem;">{val} / 20</b>
            </div>
        """, unsafe_allow_html=True)

st.divider()

# --- 2. LIVE SPY PROHLÍŽEČ ---
st.header("🕵️ Prohlížeč historie")
if not users_df.empty:
    u_list = users_df['user_id'].unique()
    selected_device = st.selectbox("Vyberte zařízení (Device ID):", u_list)
    
    filtered_data = users_df[users_df['user_id'] == selected_device]
    
    for chat_id in filtered_data['chat_id'].unique():
        chat_msgs = filtered_data[filtered_data['chat_id'] == chat_id]
        with st.expander(f"📄 Chat: {chat_msgs['title'].iloc[0]} ({len(chat_msgs)} zpráv)"):
            for _, msg in chat_msgs.iterrows():
                role_icon = "👤" if msg['role'] == "user" else "🤖"
                st.markdown(f"**{role_icon} {msg['role'].upper()}** <small style='color:gray'>{msg['timestamp']}</small>", unsafe_allow_html=True)
                st.write(msg['content'])
                st.divider()
else:
    st.info("Zatím nejsou k dispozici žádná data o chatech.")

if st.sidebar.button("Odhlásit"):
    st.session_state.admin_auth = False
    st.rerun()
