import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# --- 1. KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

# Skrytí systémových prvků
st.markdown("""
    <style>
    [data-testid="stStatusWidget"], .stDeployButton, footer { display: none !important; }
    .thinking-box {
        background-color: #e1f5fe; border-left: 5px solid #0288d1;
        padding: 15px; border-radius: 5px; color: #01579b; font-weight: bold; margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABÁZE A SESSION ---
conn = st.connection("gsheets", type=GSheetsConnection)

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]
if "model_choice" not in st.session_state:
    st.session_state.model_choice = "gemini-1.5-flash" # Výchozí stabilní model

def load_db():
    try:
        return conn.read(worksheet="Users", ttl=0)
    except:
        return pd.DataFrame(columns=["user_id", "chat_id", "title", "role", "content", "timestamp"])

# --- 3. SIDEBAR A ADMIN PANEL ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.write(f"Moje ID: `{st.session_state.user_id}`")
    
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()

    st.divider()
    
    # Admin sekce
    with st.expander("🔐 Admin Panel"):
        pw = st.text_input("Heslo", type="password")
        if pw == st.secrets["ADMIN_PASSWORD"]:
            st.success("Přihlášen")
            st.session_state.model_choice = st.selectbox(
                "Vyber model:",
                ["gemini-1.5-flash", "gemini-1.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
            )
            st.info(f"Aktivní model: {st.session_state.model_choice}")
        elif pw:
            st.error("Nesprávné heslo")

# --- 4. ZOBRAZENÍ CHATU ---
df = load_db()
current_chat = df[df["chat_id"] == st.session_state.chat_id]

st.header(f"💬 Chat: {st.session_state.chat_id}")

for _, m in current_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 5. LOGIKA ODPOVĚDI ---
if prompt := st.chat_input("Napište zprávu..."):
    # Okamžité zobrazení uživatele
    with st.chat_message("user"):
        st.write(prompt)
    
    # Uložení zprávy uživatele
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    u_row = pd.DataFrame([{
        "user_id": st.session_state.user_id,
        "chat_id": st.session_state.chat_id,
        "title": prompt[:20],
        "role": "user",
        "content": prompt,
        "timestamp": now
    }])
    
    # Modrý box přemýšlení
    thinking = st.empty()
    thinking.markdown('<div class="thinking-box">🤖 SMART přemýšlí...</div>', unsafe_allow_html=True)

    # API Volání
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY_1"])
        model = genai.GenerativeModel(st.session_state.model_choice)
        
        # Jednoduchá odpověď (v4.2 styl)
        response = model.generate_content(prompt)
        ai_text = response.text
        
        thinking.empty()
        
        with st.chat_message("assistant"):
            st.write(ai_text)
            
        # Uložení do tabulky (obojí najednou pro stabilitu)
        ai_row = pd.DataFrame([{
            "user_id": st.session_state.user_id,
            "chat_id": st.session_state.chat_id,
            "title": prompt[:20],
            "role": "assistant",
            "content": ai_text,
            "timestamp": now
        }])
        
        updated_df = pd.concat([df, u_row, ai_row], ignore_index=True)
        conn.update(worksheet="Users", data=updated_df)
        
    except Exception as e:
        thinking.empty()
        st.error(f"Chyba: {e}")

st.markdown('<div style="text-align:center; color:gray; font-size:10px; margin-top:50px;">S.M.A.R.T. OS v4.2 Modded</div>', unsafe_allow_html=True)
