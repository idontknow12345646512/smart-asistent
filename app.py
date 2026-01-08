import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import uuid
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    [data-testid="stStatusWidget"], .stDeployButton, footer { display: none !important; }
    .thinking-box {
        background-color: #e1f5fe; border-left: 5px solid #0288d1;
        padding: 15px; border-radius: 5px; color: #01579b;
        font-weight: bold; margin: 10px 0;
    }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        text-align: center; color: gray; font-size: 0.75rem;
        padding: 10px; background: transparent; z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# --- COOKIES ---
def get_manager(): return stx.CookieManager()
cookie_manager = get_manager()
device_id = cookie_manager.get(cookie="smart_os_device_id")

if not device_id:
    if "temp_id" not in st.session_state: st.session_state.temp_id = str(uuid.uuid4())[:8]
    device_id = st.session_state.temp_id
    cookie_manager.set("smart_os_device_id", device_id, expires_at=datetime.now() + pd.Timedelta(days=365))

st.session_state.device_id = device_id
if "current_chat_id" not in st.session_state: st.session_state.current_chat_id = str(uuid.uuid4())

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
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.rerun()
    st.subheader("Historie")
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

# --- LOGIKA S POJISTKOU ---
if prompt := st.chat_input("Napište zprávu..."):
    # VYTVOŘÍME UNIKÁTNÍ OTISK ZPRÁVY (Prompt + ChatID)
    prompt_hash = f"{st.session_state.current_chat_id}_{prompt}"
    
    if "last_processed" not in st.session_state or st.session_state.last_processed != prompt_hash:
        st.session_state.last_processed = prompt_hash # OKAMŽITĚ ZAMKNOUT
        
        with st.chat_message("user"): st.write(prompt)
        
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown('<div class="thinking-box">🤖 SMART přemýšlí . . .</div>', unsafe_allow_html=True)
        
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        new_title = chat_title if chat_title != "Nový chat" else prompt[:20]
        
        # 1. Uložit uživatele hned
        u_row = pd.DataFrame([{"user_id": st.session_state.device_id, "chat_id": st.session_state.current_chat_id, "title": new_title, "role": "user", "content": prompt, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row], ignore_index=True))

        api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
        model_name = "gemini-2.5-flash" if not is_lite_mode else "gemini-2.5-flash-lite"
        
        success = False
        for i, key in enumerate(api_keys):
            if not key: continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_name=model_name)
                
                # Sestavení historie (včetně té právě odeslané zprávy)
                hist = []
                for _, m in current_msgs.iterrows():
                    hist.append({"role": "user" if m['role'] == "user" else "model", "parts": [m['content']]})
                
                chat = model.start_chat(history=hist)
                response_stream = chat.send_message(prompt, stream=True)
                
                thinking_placeholder.empty()
                
                with st.chat_message("assistant"):
                    def stream_generator():
                        for chunk in response_stream: yield chunk.text
                    
                    full_res = st.write_stream(stream_generator())
                    
                    # 2. Uložit AI odpověď
                    ai_row = pd.DataFrame([{"user_id": st.session_state.device_id, "chat_id": st.session_state.current_chat_id, "title": new_title, "role": "assistant", "content": full_res, "timestamp": now}])
                    f_u, f_s = load_db()
                    conn.update(worksheet="Users", data=pd.concat([f_u, ai_row], ignore_index=True))
                    
                    # Statistiky
                    k_id = str(i + 1)
                    if k_id not in f_s['key_id'].astype(str).values:
                        f_s = pd.concat([f_s, pd.DataFrame([{"key_id": k_id, "used": 1}])], ignore_index=True)
                    else:
                        f_s.loc[f_s['key_id'].astype(str) == k_id, 'used'] += 1
                    conn.update(worksheet="Stats", data=f_s)
                    
                    st.rerun() # Finální refresh - už neprojde IFem, protože prompt_hash je stejný
                success = True
                break
            except: continue

st.markdown('<div class="footer">S.M.A.R.T. OS v7.9</div>', unsafe_allow_html=True)
