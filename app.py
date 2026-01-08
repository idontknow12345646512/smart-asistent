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
    /* Skrytí systémových prvků a menu vpravo nahoře */
    [data-testid="stStatusWidget"], .stDeployButton, footer, #MainMenu, header { display: none !important; }
    
    /* Modrý box pro přemýšlení */
    .thinking-box {
        background-color: #1e2129; border-left: 5px solid #0288d1;
        padding: 15px; border-radius: 5px; color: #e0e0e0;
        font-weight: bold; margin: 10px 0;
    }

    /* Fixní patička s barvou pozadí aplikace */
    .fixed-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        text-align: center; color: #888; font-size: 0.8rem;
        padding: 15px; background: #0e1117; /* Sladěno s dark mode Streamlitu */
        border-top: 1px solid #262730;
        z-index: 1000;
    }
    .main-content { margin-bottom: 80px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE ---
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
    # ID odstraněno podle tvého přání
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()

# --- 5. CHAT ROZHRANÍ ---
df = load_db()
current_chat = df[df["chat_id"] == st.session_state.chat_id]

# Nadpis chatu bez IDčka
st.subheader("💬 S.M.A.R.T. Chat")

st.markdown('<div class="main-content">', unsafe_allow_html=True)
for _, m in current_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 6. LOGIKA ODPOVĚDI (MODELY 2.5 + ROTACE) ---
if prompt := st.chat_input("Napište zprávu..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    thinking = st.empty()
    thinking.markdown('<div class="thinking-box">🤖 SMART přemýšlí...</div>', unsafe_allow_html=True)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    # Bere model vybraný v adminu, jinak default 2.5 Flash
    model_name = st.session_state.get("selected_model", "gemini-2.5-flash")
    
    success = False
    ai_text = ""

    for key in api_keys:
        if not key: continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction="Jsi S.M.A.R.T. OS asistent. Pomáháš studentům se školou. Odpovídej vždy česky, srozumitelně a k věci."
            )
            response = model.generate_content(prompt)
            ai_text = response.text
            success = True
            break
        except: continue

    thinking.empty()

    if success:
        with st.chat_message("assistant"):
            st.write(ai_text)
            
        u_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.chat_id, "title": prompt[:20], "role": "user", "content": prompt, "timestamp": now}])
        ai_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.current_chat_id if "current_chat_id" in st.session_state else st.session_state.chat_id, "title": prompt[:20], "role": "assistant", "content": ai_text, "timestamp": now}])
        
        updated_df = pd.concat([df, u_row, ai_row], ignore_index=True)
        conn.update(worksheet="Users", data=updated_df)
    else:
        st.error("❌ Došlo k chybě spojení.")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="fixed-footer">S.M.A.R.T. OS může dělat chyby.</div>', unsafe_allow_html=True)
