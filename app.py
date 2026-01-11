import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import io
from docx import Document

# --- 1. KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    [data-testid="stStatusWidget"], .stDeployButton, footer, #MainMenu, header { display: none !important; }
    .thinking-box {
        background-color: #1e2129; border-left: 5px solid #0288d1;
        padding: 15px; border-radius: 5px; color: #e0e0e0;
        font-weight: bold; margin: 10px 0;
    }
    .fixed-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        text-align: center; color: #888; font-size: 0.8rem;
        padding: 15px; background: #0e1117;
        border-top: 1px solid #262730; z-index: 1000;
    }
    .main-content { margin-bottom: 120px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POMOCNÉ FUNKCE ---
def create_docx(text):
    doc = Document()
    doc.add_heading('S.M.A.R.T. OS Výstup', 0)
    doc.add_paragraph(text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. DATABÁZE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        u = conn.read(worksheet="Users", ttl=0)
    except:
        u = pd.DataFrame(columns=["user_id", "chat_id", "title", "role", "content", "timestamp"])
    try:
        s = conn.read(worksheet="Stats", ttl=0)
        if "key" not in s.columns: # Oprava KeyError
            s = pd.DataFrame(columns=["key", "value"])
    except:
        s = pd.DataFrame(columns=["key", "value"])
    return u, s

users_df, stats_df = load_data()

# Zjištění počtu zpráv
if not stats_df.empty and 'total_messages' in stats_df['key'].values:
    total_msgs = int(stats_df.loc[stats_df['key'] == 'total_messages', 'value'].values[0])
else:
    total_msgs = 0

# --- 4. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())[:8]
if "chat_id" not in st.session_state: st.session_state.chat_id = str(uuid.uuid4())[:8]
if "last_res" not in st.session_state: st.session_state.last_res = ""

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    label = "Gemini 3" if total_msgs < 200 else "Gemini 2.5 Lite"
    st.caption(f"🚀 Režim: {label} ({total_msgs}/200)")
    
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.session_state.last_res = ""
        st.rerun()
    
    st.divider()
    up_file = st.file_uploader("Nahrát podklady", type=["png", "jpg", "jpeg", "pdf", "txt"])
    
    if st.session_state.last_res:
        st.download_button("📥 Word", data=create_docx(st.session_state.last_res), file_name="smart.docx", use_container_width=True)

# --- 6. CHAT ---
cur_chat = users_df[users_df["chat_id"] == st.session_state.chat_id]
st.subheader("💬 S.M.A.R.T. Chat")
st.markdown('<div class="main-content">', unsafe_allow_html=True)
for _, m in cur_chat.iterrows():
    with st.chat_message(m["role"]): st.write(m["content"])

# --- 7. LOGIKA ---
if prompt := st.chat_input("Zeptejte se..."):
    with st.chat_message("user"): st.write(prompt)
    t = st.empty()
    t.markdown('<div class="thinking-box">🤖 SMART přemýšlí...</div>', unsafe_allow_html=True)
    
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    p_model = "gemini-3-flash" if total_msgs < 200 else "gemini-2.5-flash-lite"
    
    hist = []
    for _, m in cur_chat.tail(10).iterrows():
        hist.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})

    payload = [prompt]
    if up_file:
        fb = up_file.read()
        if up_file.type == "text/plain": payload.append(f"\n\nSoubor: {fb.decode('utf-8')}")
        else: payload.append({"mime_type": up_file.type, "data": fb})

    success = False
    for key in api_keys:
        if not key or success: continue
        try:
            genai.configure(api_key=key)
            try:
                m = genai.GenerativeModel(model_name=p_model, tools=[{"google_search_retrieval": {}}])
                res = m.start_chat(history=hist).send_message(payload)
            except:
                m = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
                res = m.start_chat(history=hist).send_message(payload)
            
            txt = res.text
            success = True
            break
        except: continue

    t.empty()
    if success:
        with st.chat_message("assistant"): st.markdown(txt)
        st.session_state.last_res = txt
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Uložení zpráv
        u_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.chat_id, "role": "user", "content": prompt, "timestamp": now}])
        a_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.chat_id, "role": "assistant", "content": txt, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row, a_row], ignore_index=True))
        
        # Update Stats (s pojistkou)
        if 'total_messages' not in stats_df['key'].values:
            new_stats = pd.concat([stats_df, pd.DataFrame([{"key": "total_messages", "value": "1"}])], ignore_index=True)
        else:
            stats_df.loc[stats_df['key'] == 'total_messages', 'value'] = str(total_msgs + 1)
            new_stats = stats_df
        conn.update(worksheet="Stats", data=new_stats)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="fixed-footer">S.M.A.R.T. OS může dělat chyby.</div>', unsafe_allow_html=True)
