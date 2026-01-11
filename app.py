import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import io
from docx import Document

# --- 1. KONFIGURACE A ULTRA ČISTÝ DESIGN ---
st.set_page_config(page_title="Gemini 3", page_icon="🤖", layout="wide")

# CSS pro napodobení vzhledu z obrázku (zaoblený input, skrytí ID a patičky)
st.markdown("""
    <style>
    /* Skrytí Streamlit prvků a ID */
    [data-testid="stStatusWidget"], .stDeployButton, footer, #MainMenu, header, [data-testid="stHeader"] { display: none !important; }
    
    /* Kontejner pro zprávy */
    .main-content { 
        max-width: 800px; 
        margin: 0 auto; 
        padding-bottom: 150px; 
    }

    /* Styl pro zprávy (čistší vzhled) */
    .stChatMessage { background-color: transparent !important; border: none !important; }
    
    /* PLOVOUCÍ INPUT JAKO NA OBRÁZKU */
    div[data-testid="stChatInput"] {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        max-width: 800px;
        width: 90%;
        z-index: 1000;
        background-color: #1e1f20;
        border-radius: 28px !important;
        padding: 10px;
    }
    
    /* Úprava textového pole uvnitř inputu */
    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        border: none !important;
        color: #e3e3e3 !important;
    }

    /* Skrytí červeného banneru a ID v sidebar */
    [data-testid="stSidebar"] section { padding-top: 2rem; }
    .css-17l2pu2 { display: none; } 
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA DATABÁZE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        u = conn.read(worksheet="Users", ttl=0)
        s = conn.read(worksheet="Stats", ttl=0)
        if "key" not in s.columns: s = pd.DataFrame(columns=["key", "value"])
    except:
        u = pd.DataFrame(columns=["user_id", "chat_id", "role", "content", "timestamp"])
        s = pd.DataFrame(columns=["key", "value"])
    return u, s

users_df, stats_df = load_data()

# Počítadlo zpráv
if not stats_df.empty and 'total_messages' in stats_df['key'].values:
    total_msgs = int(stats_df.loc[stats_df['key'] == 'total_messages', 'value'].values[0])
else:
    total_msgs = 0

# --- 3. SESSION STATE ---
if "chat_id" not in st.session_state: st.session_state.chat_id = str(uuid.uuid4())[:8]
if "last_res" not in st.session_state: st.session_state.last_res = ""

# --- 4. SIDEBAR (Jen to nejnutnější) ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.session_state.last_res = ""
        st.rerun()
    st.divider()
    up_file = st.file_uploader("Nahrát soubor", type=["png", "jpg", "jpeg", "pdf", "txt"])

# --- 5. HLAVNÍ CHAT OKNO ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

cur_chat = users_df[users_df["chat_id"] == st.session_state.chat_id]

# Pokud je chat prázdný, zobrazíme uvítání
if cur_chat.empty:
    st.markdown("<h2 style='text-align: center; margin-top: 100px;'>Zeptejte se Gemini 3</h2>", unsafe_allow_html=True)

for _, m in cur_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 6. LOGIKA ODPOVĚDI ---
if prompt := st.chat_input("Zeptejte se Gemini 3"):
    with st.chat_message("user"):
        st.write(prompt)
    
    # Rozhodnutí o modelu (v3 vs v2.5)
    active_model = "gemini-3-flash" if total_msgs < 200 else "gemini-2.5-flash-lite"
    
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    success = False
    
    # Příprava historie a payloadu (jako v předchozích verzích)
    hist = []
    for _, m in cur_chat.tail(10).iterrows():
        hist.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})
    
    payload = [prompt]
    if up_file:
        fb = up_file.read()
        if up_file.type == "text/plain": payload.append(f"\n\nSoubor: {fb.decode('utf-8')}")
        else: payload.append({"mime_type": up_file.type, "data": fb})

    for key in api_keys:
        if not key or success: continue
        try:
            genai.configure(api_key=key)
            m = genai.GenerativeModel(
                model_name=active_model,
                system_instruction="Jsi S.M.A.R.T. OS. Odpovídej VŽDY ČESKY. Jsi stručný a věcný. Používej Markdown."
            )
            res = m.start_chat(history=hist).send_message(payload)
            txt = res.text
            success = True
            break
        except: continue

    if success:
        with st.chat_message("assistant"):
            st.markdown(txt)
        
        # Uložení
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        u_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "user", "content": prompt, "timestamp": now}])
        a_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "assistant", "content": txt, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row, a_row], ignore_index=True))
        
        # Update statistik
        if 'total_messages' not in stats_df['key'].values:
            new_stats = pd.concat([stats_df, pd.DataFrame([{"key": "total_messages", "value": "1"}])], ignore_index=True)
        else:
            stats_df.loc[stats_df['key'] == 'total_messages', 'value'] = str(total_msgs + 1)
            new_stats = stats_df
        conn.update(worksheet="Stats", data=new_stats)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
