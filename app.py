import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# --- 1. KOMPLETNÍ ODSTRANĚNÍ SYSTÉMOVÝCH PRVKŮ ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    /* 1. Úplné skrytí horní lišty a menu (červená zóna) */
    header, [data-testid="stHeader"] { visibility: hidden; height: 0px; }
    
    /* 2. Odstranění bílého pruhu a "Manage app" (červená zóna) */
    footer, [data-testid="stBottomBlockContainer"], #MainMenu { display: none !important; }
    [data-testid="stAppToolbar"] { display: none !important; }
    
    /* 3. Vyčištění spodku aplikace od bílých stínů */
    .stAppDeployButton { display: none !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }

    /* 4. Úprava barev a čistota */
    .stApp { background-color: #0e1117; color: white; }
    
    /* 5. Tlačítko pro Sidebar (žlutá šipka) - Streamlit ho má vlevo nahoře nativně, 
       jen ho musíme nechat viditelné i bez headeru */
    .st-emotion-cache-6qob1r { position: fixed; top: 10px; left: 10px; z-index: 10000; color: white; }
    
    /* 6. Design chatovacího řádku s PLUSkem */
    div[data-testid="stChatInput"] {
        border: 1px solid #30363d !important;
        border-radius: 20px !important;
        background-color: #161b22 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA DAT ---
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

if "chat_id" not in st.session_state: st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. SIDEBAR (ŠIPKA VLEVO NAHOŘE) ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.caption(f"Zprávy: {total_msgs}/200")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    st.divider()
    # TADY JE TO PLUS PRO SOUBOR
    up_file = st.file_uploader("➕ PŘIDAT SOUBOR", type=["png", "jpg", "jpeg", "pdf", "txt"])

# --- 4. CHAT ---
st.markdown('<div style="max-width: 800px; margin: 0 auto; padding-top: 20px;">', unsafe_allow_html=True)

cur_chat = users_df[users_df["chat_id"] == st.session_state.chat_id]
for _, m in cur_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 5. PSANÍ ZPRÁVY ---
if prompt := st.chat_input("Zeptejte se na cokoliv..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    # Automatický výběr modelu
    active_model = "gemini-3-flash" if total_msgs < 200 else "gemini-2.5-flash-lite"
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    
    payload = [prompt]
    if up_file:
        fb = up_file.read()
        if up_file.type == "text/plain": payload.append(f"Soubor: {fb.decode('utf-8')}")
        else: payload.append({"mime_type": up_file.type, "data": fb})

    success = False
    for key in api_keys:
        if not key or success: continue
        try:
            genai.configure(api_key=key)
            m = genai.GenerativeModel(
                model_name=active_model,
                system_instruction="Jsi S.M.A.R.T. OS. Odpovídej VŽDY ČESKY. Jsi užitečný asistent."
            )
            # Pokus s vyhledáváním
            try: res = m.generate_content(payload, tools=[{"google_search_retrieval": {}}])
            except: res = m.generate_content(payload)
            
            txt = res.text
            success = True
            break
        except: continue

    if success:
        with st.chat_message("assistant"):
            st.markdown(txt)
        
        # Uložení do GSheets
        now = datetime.now().strftime("%H:%M")
        u_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "user", "content": prompt, "timestamp": now}])
        a_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "assistant", "content": txt, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row, a_row], ignore_index=True))
        
        # Update limitu
        stats_df.loc[stats_df['key'] == 'total_messages', 'value'] = str(total_msgs + 1)
        conn.update(worksheet="Stats", data=stats_df)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
