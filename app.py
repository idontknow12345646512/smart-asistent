import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import io

# --- 1. KONFIGURACE A STYLY ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    /* Skrytí červených ID a systémových lišt */
    [data-testid="stStatusWidget"], .stDeployButton, footer, #MainMenu, header { display: none !important; }
    
    /* Úprava barvy pozadí a textu pro mobilní přehlednost */
    .stApp { background-color: #0e1117; }
    
    /* Styl pro kontejner chatu */
    .main-content { margin-bottom: 120px; }

    /* Úprava chat inputu - aby vypadal moderně a čistě */
    div[data-testid="stChatInput"] {
        border-radius: 15px !important;
        background-color: #1e2129 !important;
    }

    /* Fixní patička sladěná s pozadím */
    .fixed-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        text-align: center; color: #555; font-size: 0.7rem;
        padding: 5px; background: #0e1117;
        border-top: 1px solid #262730; z-index: 999;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABÁZE A STATISTIKY ---
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

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.caption(f"Zprávy celkem: {total_msgs}/200")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()

# --- 5. CHAT ROZHRANÍ ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
cur_chat = users_df[users_df["chat_id"] == st.session_state.chat_id]

for _, m in cur_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 6. INTEGROVANÉ NAHRÁVÁNÍ SOUBORŮ ("+") ---
# Na mobilu je lepší mít nahrávání hned nad inputem
with st.container():
    col1, col2 = st.columns([1, 6])
    with col1:
        # Tlačítko pro soubor stylizované jako "+"
        up_file = st.file_uploader("➕", type=["png", "jpg", "jpeg", "pdf", "txt"], label_visibility="collapsed")
    
    with col2:
        prompt = st.chat_input("Napište zprávu...")

# --- 7. LOGIKA ODPOVĚDI (VŽDY ČESKY) ---
if prompt:
    with st.chat_message("user"):
        st.write(prompt)
        if up_file: st.caption(f"📎 Soubor: {up_file.name}")
    
    # Výběr modelu
    active_model = "gemini-3-flash" if total_msgs < 200 else "gemini-2.5-flash-lite"
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    
    # Příprava dat pro AI
    payload = [prompt]
    if up_file:
        fb = up_file.read()
        if up_file.type == "text/plain": payload.append(f"\nObsah: {fb.decode('utf-8')}")
        else: payload.append({"mime_type": up_file.type, "data": fb})

    success = False
    for key in api_keys:
        if not key or success: continue
        try:
            genai.configure(api_key=key)
            m = genai.GenerativeModel(
                model_name=active_model,
                tools=[{"google_search_retrieval": {}}],
                system_instruction="Jsi S.M.A.R.T. OS. Odpovídej VŽDY ČESKY. Pomáhej studentům. Pokud vidíš obrázek nebo PDF, podrobně ho analyzuj."
            )
            res = m.generate_content(payload)
            txt = res.text
            success = True
            break
        except:
            continue

    if success:
        with st.chat_message("assistant"):
            st.markdown(txt)
        
        # Uložení
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        u_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "user", "content": prompt, "timestamp": now}])
        a_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "assistant", "content": txt, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row, a_row], ignore_index=True))
        
        # Update statistik
        stats_df.loc[stats_df['key'] == 'total_messages', 'value'] = str(total_msgs + 1)
        conn.update(worksheet="Stats", data=stats_df)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="fixed-footer">S.M.A.R.T. OS (v8.1) | Vždy česky</div>', unsafe_allow_html=True)
