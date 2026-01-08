import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import uuid
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
import time

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# CSS pro modrý obdélník
st.markdown("""
    <style>
    .thinking-box {
        background-color: #e1f5fe;
        border-left: 5px solid #0288d1;
        padding: 15px;
        border-radius: 5px;
        color: #01579b;
        font-weight: bold;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- COOKIES ---
@st.cache_resource
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()
device_id = cookie_manager.get(cookie="smart_os_device_id")

if not device_id:
    if "temp_id" not in st.session_state:
        st.session_state.temp_id = str(uuid.uuid4())[:8]
    device_id = st.session_state.temp_id
    cookie_manager.set("smart_os_device_id", device_id, expires_at=datetime.now() + pd.Timedelta(days=365))
st.session_state.device_id = device_id

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())

# --- DB FUNKCE ---
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

# Načtení dat
users_df, stats_df = load_db()
total_used = stats_df['used'].astype(int).sum() if not stats_df.empty else 0
is_lite_mode = total_used >= 200
user_history = users_df[users_df['user_id'] == st.session_state.device_id]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.info(f"ID: {st.session_state.device_id}")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.rerun()

# --- CHAT ---
current_msgs = user_history[user_history['chat_id'] == st.session_state.current_chat_id]
chat_title = current_msgs['title'].iloc[0] if not current_msgs.empty else "Nový chat"
st.header(f"💬 {chat_title}")

for _, m in current_msgs.iterrows():
    with st.chat_message(m['role']): st.write(m['content'])

# --- LOGIKA ODPOVĚDI SE STREAMINGEM ---
if prompt := st.chat_input("Napište zprávu..."):
    with st.chat_message("user"): st.write(prompt)
    
    thinking_placeholder = st.empty()
    thinking_placeholder.markdown('<div class="thinking-box">🤖 SMART přemýšlí . . .</div>', unsafe_allow_html=True)
    
    new_title = chat_title if chat_title != "Nový chat" else prompt[:20]
    save_message(st.session_state.device_id, st.session_state.current_chat_id, new_title, "user", prompt)

    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    model_name = "gemini-2.5-flash" if not is_lite_mode else "gemini-2.5-flash-lite"
    
    success = False
    for i, key in enumerate(api_keys):
        if not key: continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name=model_name)
            
            history_data = []
            for _, m in current_msgs.iterrows():
                history_data.append({"role": "user" if m['role'] == "user" else "model", "parts": [m['content']]})
            
            chat = model.start_chat(history=history_data)
            
            # TADY JE TA ZMĚNA: stream=True
            response_stream = chat.send_message(prompt, stream=True)
            
            # Jakmile dorazí první kousek dat, smažeme modrý box
            thinking_placeholder.empty()
            
            with st.chat_message("assistant"):
                # Funkce pro generování kousků textu pro Streamlit
                def stream_generator():
                    for chunk in response_stream:
                        yield chunk.text
                
                # Zobrazení plynulého psaní
                full_response = st.write_stream(stream_generator())
                
                # Po dopsání uložíme a aktualizujeme statistiky
                save_message(st.session_state.device_id, st.session_state.current_chat_id, new_title, "assistant", full_response)
                update_usage(i+1)
                st.rerun()
            
            success = True
            break
        except: continue

    if not success:
        thinking_placeholder.empty()
        st.error("Kapacita vyčerpána.")

st.markdown("<div style='position: fixed; bottom: 0; width: 100%; text-align: center; color: gray; font-size: 0.75rem; padding: 10px;'>S.M.A.R.T. OS může dělat chyby.</div>", unsafe_allow_html=True)
