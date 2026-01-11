import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import io

# --- 1. KONFIGURACE A ABSOLUTNÍ ČIŠTĚNÍ DESIGNU ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    /* Skrytí VŠECH červeně označených prvků */
    header, footer, .stDeployButton, [data-testid="stStatusWidget"], [data-testid="stHeader"], [data-testid="stBottomBlockContainer"] { 
        display: none !important; 
    }
    
    /* Skrytí Streamlit "Manage app" vpravo dole */
    .stAppToolbar { display: none !important; }
    footer { visibility: hidden; }

    /* Hlavní kontejner - vycentrování a čistota */
    .main-chat-container {
        max-width: 850px;
        margin: 0 auto;
        padding-top: 50px;
        padding-bottom: 120px;
    }

    /* VLASTNÍ PANEL PRO ZPRÁVU A PLUS (+) */
    .input-wrapper {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        z-index: 1000;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Styl pro tlačítko PLUS */
    .plus-button-container {
        background-color: #1e2129;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        display: flex;
        justify-content: center;
        align-items: center;
        border: 1px solid #30363d;
        cursor: pointer;
    }
    
    /* Úprava barvy pozadí aplikace */
    .stApp { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABÁZE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        u = conn.read(worksheet="Users", ttl=0)
        s = conn.read(worksheet="Stats", ttl=0)
    except:
        u = pd.DataFrame(columns=["user_id", "chat_id", "role", "content", "timestamp"])
        s = pd.DataFrame([{"key": "total_messages", "value": "0"}])
    return u, s

users_df, stats_df = load_data()
total_msgs = int(stats_df.loc[stats_df['key'] == 'total_messages', 'value'].values[0]) if not stats_df.empty else 0

# --- 3. SESSION STATE ---
if "chat_id" not in st.session_state: st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 4. SIDEBAR SE ŠIPKOU ---
# Sidebar se šipkou je v Streamlitu automatický, pokud ho nezakážeme CSS. 
# Zde ho necháváme pro historii a nastavení.
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.caption(f"Limit: {total_msgs}/200")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    st.divider()
    # Tady je to slíbené PLUS (+) pro nahrávání souborů
    up_file = st.file_uploader("Nahrát podklady (+)", type=["png", "jpg", "jpeg", "pdf", "txt"])

# --- 5. CHAT OKNO ---
st.markdown('<div class="main-chat-container">', unsafe_allow_html=True)

cur_chat = users_df[users_df["chat_id"] == st.session_state.chat_id]

# Zobrazení historie (bez ID chatu nahoře!)
for _, m in cur_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 6. CHAT INPUT ---
if prompt := st.chat_input("Zeptejte se na cokoliv..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    # AI LOGIKA (Gemini 3 -> 2.5)
    active_model = "gemini-3-flash" if total_msgs < 200 else "gemini-2.5-flash-lite"
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    
    payload = [prompt]
    if up_file:
        fb = up_file.read()
        if up_file.type == "text/plain": payload.append(f"Obsah souboru: {fb.decode('utf-8')}")
        else: payload.append({"mime_type": up_file.type, "data": fb})

    success = False
    for key in api_keys:
        if not key or success: continue
        try:
            genai.configure(api_key=key)
            m = genai.GenerativeModel(
                model_name=active_model,
                system_instruction="Jsi S.M.A.R.T. OS. Odpovídej VŽDY ČESKY. Jsi asistent pro studenty."
            )
            # Pokus o vyhledávání (Google Search)
            try:
                res = m.generate_content(payload, tools=[{"google_search_retrieval": {}}])
            except:
                res = m.generate_content(payload)
                
            txt = res.text
            success = True
            break
        except: continue

    if success:
        with st.chat_message("assistant"):
            st.markdown(txt)
        
        # Uložení
        now = datetime.now().strftime("%H:%M")
        u_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "user", "content": prompt, "timestamp": now}])
        a_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "assistant", "content": txt, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row, a_row], ignore_index=True))
        
        # Update limitu
        stats_df.loc[stats_df['key'] == 'total_messages', 'value'] = str(total_msgs + 1)
        conn.update(worksheet="Stats", data=stats_df)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
