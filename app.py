import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# --- 1. KONFIGURACE A STYLY ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    /* Skrytí systémových prvků Streamlitu */
    [data-testid="stStatusWidget"], .stDeployButton, footer { display: none !important; }
    
    /* Modrý box pro přemýšlení */
    .thinking-box {
        background-color: #e1f5fe; border-left: 5px solid #0288d1;
        padding: 15px; border-radius: 5px; color: #01579b;
        font-weight: bold; margin: 10px 0;
    }

    /* Fixní patička - Zůstává vidět i během psaní */
    .fixed-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        text-align: center; color: gray; font-size: 0.8rem;
        padding: 10px; background: white; border-top: 1px solid #eee;
        z-index: 1000;
    }
    /* Odsazení obsahu od patičky */
    .main-content { margin-bottom: 60px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE (Místo Cookies) ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. DATABÁZE (GSheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        return conn.read(worksheet="Users", ttl=0)
    except:
        return pd.DataFrame(columns=["user_id", "chat_id", "title", "role", "content", "timestamp"])

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.info(f"ID: {st.session_state.user_id}")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()

# --- 5. CHAT ROZHRANÍ ---
df = load_db()
current_chat = df[df["chat_id"] == st.session_state.chat_id]

st.header(f"💬 Chat: {st.session_state.chat_id}")

# Zobrazení historie
st.markdown('<div class="main-content">', unsafe_allow_html=True)
for _, m in current_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 6. LOGIKA ODPOVĚDI (MODELY 2.5) ---
if prompt := st.chat_input("Napište zprávu..."):
    # Zobrazení uživatele hned
    with st.chat_message("user"):
        st.write(prompt)
    
    # Indikátor přemýšlení
    thinking = st.empty()
    thinking.markdown('<div class="thinking-box">🤖 SMART přemýšlí...</div>', unsafe_allow_html=True)

    # Automatický datum a čas
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        # Nastavení API (bere první klíč)
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY_1"])
        
        # Určení modelu (Admin přepíná v admin.py, zde je default 2.5)
        # Pokud v session_state z admin.py nic není, použijeme flash
        model_name = st.session_state.get("selected_model", "gemini-2.5-flash")
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction="Jsi S.M.A.R.T. OS, inteligentní asistent. Tvým hlavním úkolem je pomáhat studentům se školou, vysvětlovat látku a řešit úkoly plynule a srozumitelně."
        )
        
        # Generování (v4.2 styl - bez streamování pro max. stabilitu)
        response = model.generate_content(prompt)
        ai_text = response.text
        
        thinking.empty()
        
        with st.chat_message("assistant"):
            st.write(ai_text)
            
        # Zápis do GSheets
        u_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.chat_id, "title": prompt[:20], "role": "user", "content": prompt, "timestamp": now}])
        ai_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.chat_id, "title": prompt[:20], "role": "assistant", "content": ai_text, "timestamp": now}])
        
        updated_df = pd.concat([df, u_row, ai_row], ignore_index=True)
        conn.update(worksheet="Users", data=updated_df)
        
    except Exception as e:
        thinking.empty()
        st.error(f"Chyba: {e}")
st.markdown('</div>', unsafe_allow_html=True)

# --- 7. FIXNÍ PATIČKA ---
st.markdown('<div class="fixed-footer">S.M.A.R.T. OS může dělat chyby.</div>', unsafe_allow_html=True)
