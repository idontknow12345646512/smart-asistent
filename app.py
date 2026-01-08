import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import uuid
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx

# --- KONFIGURACE A STYL ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

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
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        text-align: center; color: gray; font-size: 0.75rem;
        padding: 10px; background: transparent; z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# --- COOKIES ---
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

# --- DATABÁZE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        u_df = conn.read(worksheet="Users", ttl=0)
        s_df = conn.read(worksheet="Stats", ttl=0)
        return u_df, s_df
    except:
        return pd.DataFrame(columns=["user_id", "chat_id", "title", "role", "content", "timestamp"]), \
               pd.DataFrame(columns=["key_id", "used"])

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
    
    st.subheader("Moje historie")
    unique_chats = user_history[['chat_id', 'title']].drop_duplicates()
    for _, row in unique_chats.iterrows():
        if st.button(row['title'][:20], key=f"btn_{row['chat_id']}", use_container_width=True):
            st.session_state.current_chat_id = row['chat_id']
            st.rerun()

# --- CHAT ---
current_msgs = user_history[user_history['chat_id'] == st.session_state.current_chat_id]
chat_title = current_msgs['title'].iloc[0] if not current_msgs.empty else "Nový chat"
st.header(f"💬 {chat_title}")

for _, m in current_msgs.iterrows():
    with st.chat_message(m['role']): st.write(m['content'])

# --- LOGIKA ODPOVĚDI (STREAMING + POJISTKA) ---
if prompt := st.chat_input("Napište zprávu..."):
    # POJISTKA: Pokud už na tento prompt odpovídáme, nepouštěj to znovu
    if "processing" not in st.session_state:
        st.session_state.processing = True
        
        with st.chat_message("user"): st.write(prompt)
        
        # Modrý obdélník
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown('<div class="thinking-box">🤖 SMART přemýšlí . . .</div>', unsafe_allow_html=True)
        
        new_title = chat_title if chat_title != "Nový chat" else prompt[:20]
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Uložení zprávy uživatele
        user_row = pd.DataFrame([{"user_id": st.session_state.device_id, "chat_id": st.session_state.current_chat_id, "title": new_title, "role": "user", "content": prompt, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, user_row], ignore_index=True))

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
                response_stream = chat.send_message(prompt, stream=True)
                
                thinking_placeholder.empty() # Smazání modrého boxu
                
                with st.chat_message("assistant"):
                    def stream_generator():
                        for chunk in response_stream:
                            yield chunk.text
                    
                    # PLYNULÉ PSANÍ
                    full_response = st.write_stream(stream_generator())
                    
                    # Uložení odpovědi AI
                    ai_row = pd.DataFrame([{"user_id": st.session_state.device_id, "chat_id": st.session_state.current_chat_id, "title": new_title, "role": "assistant", "content": full_response, "timestamp": now}])
                    fresh_u, fresh_s = load_db()
                    conn.update(worksheet="Users", data=pd.concat([fresh_u, ai_row], ignore_index=True))
                    
                    # Update statistik
                    k_id = str(i + 1)
                    if k_id not in fresh_s['key_id'].astype(str).values:
                        new_s = pd.DataFrame([{"key_id": k_id, "used": 1}])
                        fresh_s = pd.concat([fresh_s, new_s], ignore_index=True)
                    else:
                        fresh_s.loc[fresh_s['key_id'].astype(str) == k_id, 'used'] += 1
                    conn.update(worksheet="Stats", data=fresh_s)
                    
                    del st.session_state.processing # Uvolnění pojistky
                    st.rerun()
                success = True
                break
            except: continue
        
        if not success:
            del st.session_state.processing
            st.error("Chyba spojení.")

st.markdown('<div class="footer">S.M.A.R.T. OS může dělat chyby.</div>', unsafe_allow_html=True)

