import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# --- 1. DESIGN PODLE NÁKRESU ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    /* ČERVENÁ: Odstranění rušivých ID a horní lišty */
    header { visibility: hidden; }
    .stDeployButton { display: none !important; }
    
    /* BÍLÁ: Přesunutí a vyčištění plochy */
    .stApp { background-color: #0e1117; }
    .main-content { max-width: 850px; margin: 0 auto; padding-bottom: 150px; }

    /* ŽLUTÁ: Úprava inputu, aby vypadal, že má u sebe "+" (v rámci možností Streamlitu) */
    div[data-testid="stChatInput"] {
        border-radius: 20px !important;
    }
    
    /* Ponechání Manage app (vpravo dole) */
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABÁZE (OPRAVA NAČÍTÁNÍ) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        u = conn.read(worksheet="Users", ttl=0)
    except:
        u = pd.DataFrame(columns=["user_id", "chat_id", "role", "content", "timestamp"])
    try:
        s = conn.read(worksheet="Stats", ttl=0)
    except:
        s = pd.DataFrame([{"key": "total_messages", "value": "0"}])
    return u, s

users_df, stats_df = load_data()
total_msgs = int(stats_df.loc[stats_df['key'] == 'total_messages', 'value'].values[0]) if not stats_df.empty else 0

# --- 3. SESSION STATE ---
if "chat_id" not in st.session_state: st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 4. SIDEBAR (ŽLUTÁ ŠIPKA PRO OTEVŘENÍ) ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    
    st.divider()
    # ŽLUTÁ: Tady je to "+" pro přidání souboru
    up_file = st.file_uploader("➕ PŘIDAT SOUBOR", type=["png", "jpg", "jpeg", "pdf", "txt"])
    st.caption(f"Zprávy: {total_msgs}/200")

# --- 5. CHAT OKNO ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
cur_chat = users_df[users_df["chat_id"] == st.session_state.chat_id]

for _, m in cur_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 6. OPRAVA ODPOVÍDÁNÍ AI ---
if prompt := st.chat_input("Zeptejte se na cokoliv..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    # Rotace klíčů (pro případ přetížení)
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    active_model = "gemini-3-flash" if total_msgs < 200 else "gemini-2.5-flash-lite"
    
    payload = [prompt]
    if up_file:
        fb = up_file.read()
        if up_file.type == "text/plain": payload.append(f"Soubor: {fb.decode('utf-8')}")
        else: payload.append({"mime_type": up_file.type, "data": fb})

    success = False
    ai_response = ""

    for key in api_keys:
        if not key or success: continue
        try:
            genai.configure(api_key=key)
            # DŮLEŽITÉ: System instruction pro češtinu
            model = genai.GenerativeModel(
                model_name=active_model,
                system_instruction="Jsi S.M.A.R.T. OS. Mluv VŽDY ČESKY. Odpovídej věcně a pomáhej studentům."
            )
            # Bezpečnostní pojistka: nejdřív zkusit s vyhledáváním, pak bez něj
            try:
                res = model.generate_content(payload, tools=[{"google_search_retrieval": {}}])
            except:
                res = model.generate_content(payload)
            
            ai_response = res.text
            success = True
            break
        except Exception as e:
            continue

    if success:
        with st.chat_message("assistant"):
            st.markdown(ai_response)
        
        # Uložení dat
        now = datetime.now().strftime("%H:%M")
        u_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "user", "content": prompt, "timestamp": now}])
        a_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "assistant", "content": ai_response, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row, a_row], ignore_index=True))
        
        # Update statistik
        stats_df.loc[stats_df['key'] == 'total_messages', 'value'] = str(total_msgs + 1)
        conn.update(worksheet="Stats", data=stats_df)
        st.rerun()
    else:
        st.error("AI momentálně neodpovídá. Zkuste to za chvíli nebo zkontrolujte API klíče.")

st.markdown('</div>', unsafe_allow_html=True)
