import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import uuid
import pandas as pd
from datetime import datetime

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS v5.2", page_icon="🤖", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Limity
LIMIT_PER_KEY = 20  # Počet zpráv na jeden klíč pro hlavní model

# --- IDENTIFIKACE ZAŘÍZENÍ ---
if "device_id" not in st.session_state:
    st.session_state.device_id = str(uuid.uuid4())[:12]
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())

# --- FUNKCE PRO DATABÁZI ---
def load_db():
    try:
        u_df = conn.read(worksheet="Users", ttl=0)
        s_df = conn.read(worksheet="Stats", ttl=0)
        return u_df, s_df
    except:
        return pd.DataFrame(columns=["user_id", "chat_id", "title", "role", "content", "timestamp"]), \
               pd.DataFrame(columns=["key_id", "used"])

def save_message(user_id, chat_id, title, role, content):
    u_df, _ = load_db()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    new_row = pd.DataFrame([{"user_id": user_id, "chat_id": chat_id, "title": title, "role": role, "content": content, "timestamp": now}])
    conn.update(worksheet="Users", data=pd.concat([u_df, new_row], ignore_index=True))

def update_usage(k_id):
    _, s_df = load_db()
    k_id_str = str(k_id)
    if k_id_str not in s_df['key_id'].astype(str).values:
        new_row = pd.DataFrame([{"key_id": k_id_str, "used": 1}])
        s_df = pd.concat([s_df, new_row], ignore_index=True)
    else:
        s_df.loc[s_df['key_id'].astype(str) == k_id_str, 'used'] += 1
    conn.update(worksheet="Stats", data=s_df)

# --- NAČTENÍ DAT ---
users_df, stats_df = load_db()
user_history = users_df[users_df['user_id'] == st.session_state.device_id]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.caption(f"Zařízení: {st.session_state.device_id}")
    
    # Výpočet celkového využití pro zobrazení adminovi/tobě
    total_used = stats_df['used'].astype(int).sum() if not stats_df.empty else 0
    
    # Zjistíme, jaký model se aktuálně použije (Uživatel to nemusí vědět, ale ty to uvidíš)
    current_mode = "Gemini 2.5 Flash" if total_used < (10 * LIMIT_PER_KEY) else "Gemini 2.5 Flash Lite"
    st.info(f"Režim: {current_mode}")

    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.rerun()

    st.subheader("Moje historie")
    unique_chats = user_history[['chat_id', 'title']].drop_duplicates()
    for _, row in unique_chats.iterrows():
        if st.button(row['title'][:20], key=f"btn_{row['chat_id']}", use_container_width=True):
            st.session_state.current_chat_id = row['chat_id']
            st.rerun()

# --- CHAT PLOCHA ---
current_msgs = user_history[user_history['chat_id'] == st.session_state.current_chat_id]
chat_title = current_msgs['title'].iloc[0] if not current_msgs.empty else "Nový chat"
st.header(f"💬 {chat_title}")

for _, m in current_msgs.iterrows():
    with st.chat_message(m['role']): st.write(m['content'])

# --- LOGIKA CHATU ---
if prompt := st.chat_input("Napište zprávu..."):
    with st.chat_message("user"): st.write(prompt)
    
    new_title = chat_title if chat_title != "Nový chat" else prompt[:20]
    save_message(st.session_state.device_id, st.session_state.current_chat_id, new_title, "user", prompt)

    # Načtení všech 10 klíčů
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    
    success = False
    # ROZHODOVACÍ LOGIKA:
    # 1. Nejdříve zkusíme najít klíč, který má pod 20 zpráv a použít Flash
    # 2. Pokud jsou všechny nad 20, použijeme Flash Lite
    
    selected_model_name = "gemini-2.5-flash" if total_used < (10 * LIMIT_PER_KEY) else "gemini-2.5-flash-lite"

    for i, key in enumerate(api_keys):
        if not key: continue
        k_id = i + 1
        
        # Zjistíme využití tohoto konkrétního klíče
        key_usage = stats_df[stats_df['key_id'].astype(str) == str(k_id)]['used'].iloc[0] if str(k_id) in stats_df['key_id'].astype(str).values else 0
        
        # Pokud už jsme v Lite režimu, bereme první funkční klíč. 
        # Pokud jsme ve Flash režimu, bereme ten, co má pod 20.
        if selected_model_name == "gemini-2.5-flash" and key_usage >= LIMIT_PER_KEY:
            continue 

        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name=selected_model_name)
            
            history_data = []
            for _, m in current_msgs.iterrows():
                history_data.append({"role": "user" if m['role'] == "user" else "model", "parts": [m['content']]})
            
            chat = model.start_chat(history=history_data)
            response = chat.send_message(prompt)
            
            with st.chat_message("assistant"):
                st.write(response.text)
                save_message(st.session_state.device_id, st.session_state.current_chat_id, new_title, "assistant", response.text)
                update_usage(k_id)
                st.rerun()
            success = True
            break 
        except Exception:
            continue

    if not success:
        st.error("Všechny kapacity jsou momentálně vyčerpány.")
