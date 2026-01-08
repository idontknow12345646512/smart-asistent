import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import uuid
import pandas as pd
from datetime import datetime

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS v5.9", page_icon="🤖", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

LIMIT_PER_KEY = 20 

# --- IDENTIFIKACE ZAŘÍZENÍ (TRVALÁ PŘES URL) ---
query_params = st.query_params
if "dev" in query_params:
    st.session_state.device_id = query_params["dev"]
elif "device_id" not in st.session_state:
    # Generování nového ID při první návštěvě a uložení do URL
    new_id = str(uuid.uuid4())[:8]
    st.session_state.device_id = new_id
    st.query_params["dev"] = new_id

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

# Načtení dat a kontrola stavu modelů
users_df, stats_df = load_db()
total_used = stats_df['used'].astype(int).sum() if not stats_df.empty else 0
is_lite_mode = total_used >= 200 # Celkový limit pro v3.0 model
user_history = users_df[users_df['user_id'] == st.session_state.device_id]

# --- UI: UPOZORNĚNÍ NA LITE MODEL (NAHOŘE) ---
if is_lite_mode:
    st.warning("⚠️ Právě se používá úsporný model v2.5 z důvodu vysokého vytížení systému.", icon="ℹ️")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.info(f"Vaše ID: {st.session_state.device_id}")
    st.caption("Pro zachování historie si uložte URL adresu do záložek.")
    
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.rerun()

    st.subheader("Moje historie")
    unique_chats = user_history[['chat_id', 'title']].drop_duplicates()
    if not unique_chats.empty:
        for _, row in unique_chats.iterrows():
            if st.button(row['title'][:20], key=f"btn_{row['chat_id']}", use_container_width=True):
                st.session_state.current_chat_id = row['chat_id']
                st.rerun()
    else:
        st.write("Zatím žádná historie.")

# --- CHAT PLOCHA ---
current_msgs = user_history[user_history['chat_id'] == st.session_state.current_chat_id]
chat_title = current_msgs['title'].iloc[0] if not current_msgs.empty else "Nový chat"
st.header(f"💬 {chat_title}")

# Zobrazení zpráv z historie
for _, m in current_msgs.iterrows():
    with st.chat_message(m['role']): 
        st.write(m['content'])

# --- LOGIKA ODPOVĚDI ---
if prompt := st.chat_input("Napište zprávu..."):
    with st.chat_message("user"): 
        st.write(prompt)
    
    new_title = chat_title if chat_title != "Nový chat" else prompt[:20]
    save_message(st.session_state.device_id, st.session_state.current_chat_id, new_title, "user", prompt)

    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    # Přesné názvy modelů podle tvého zadání
    model_name = "gemini-2.5-flash" if not is_lite_mode else "gemini-2.5-flash-lite"
    
    success = False
    for i, key in enumerate(api_keys):
        if not key: continue
        k_id = i + 1
        
        # Kontrola, zda konkrétní klíč nepřesáhl 20 pro v3.0 model
        k_row = stats_df[stats_df['key_id'].astype(str) == str(k_id)]
        k_usage = int(k_row['used'].iloc[0]) if not k_row.empty else 0
        
        if not is_lite_mode and k_usage >= LIMIT_PER_KEY:
            continue 

        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name=model_name)
            
            # Sestavení historie pro Gemini
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
        st.error("Omlouváme se, všechny dostupné kapacity jsou vyčerpány.")

# --- UI: PATIČKA (DOLE) ---
st.markdown("""
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: gray;
        text-align: center;
        font-size: 0.75rem;
        padding: 10px;
        z-index: 100;
    }
    </style>
    <div class="footer">
        S.M.A.R.T. OS může dělat chyby. Ověřujte si důležité informace.
    </div>
    """, unsafe_allow_html=True)
