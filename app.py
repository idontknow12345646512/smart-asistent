import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid

# --- 1. DESIGN ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    /* Skrytí ID a menu (Červená zóna) */
    header { visibility: hidden; }
    .stDeployButton { display: none !important; }
    
    /* Vyčištění plochy (Bílá zóna) */
    .stApp { background-color: #0e1117; }
    .main-content { max-width: 800px; margin: 0 auto; padding-bottom: 160px; }

    /* Fixní kontejner pro nahrávání nad inputem (Žlutá zóna - PLUS) */
    .upload-bar {
        position: fixed;
        bottom: 85px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        z-index: 1000;
    }
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

if "chat_id" not in st.session_state: st.session_state.chat_id = str(uuid.uuid4())[:8]

# --- 3. SIDEBAR (Šipka pro otevření) ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.rerun()
    st.divider()
    st.caption(f"Celkem zpráv: {total_msgs}/200")

# --- 4. CHAT PLOCHA ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)
cur_chat = users_df[users_df["chat_id"] == st.session_state.chat_id]

for _, m in cur_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 5. PLUS TLAČÍTKO A INPUT ---
# Tady je to "PLUS" přímo nad psaním
with st.container():
    st.markdown('<div class="upload-bar">', unsafe_allow_html=True)
    up_file = st.file_uploader("➕", type=["png", "jpg", "jpeg", "pdf", "txt"], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    
    prompt = st.chat_input("Zeptejte se na cokoliv...")

# --- 6. OPRAVENÁ AI LOGIKA ---
if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    
    # Rotace klíčů
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    # Výběr modelu
    model_to_use = "gemini-3-flash" if total_msgs < 200 else "gemini-2.5-flash-lite"
    
    # Sestavení zprávy
    parts = [{"text": prompt}]
    if up_file:
        file_bytes = up_file.read()
        if up_file.type == "text/plain":
            parts.append({"text": f"\nObsah souboru:\n{file_bytes.decode('utf-8')}"})
        else:
            parts.append({"inline_data": {"mime_type": up_file.type, "data": file_bytes}})

    success = False
    for key in api_keys:
        if not key or success: continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name=model_to_use,
                system_instruction="Jsi S.M.A.R.T. OS. Mluv VŽDY ČESKY. Jsi asistent pro studenty."
            )
            # Volání generování (opraveno pro v3 a v2.5)
            response = model.generate_content(parts)
            
            if response.text:
                ai_text = response.text
                success = True
                break
        except:
            continue

    if success:
        with st.chat_message("assistant"):
            st.markdown(ai_text)
        
        # Uložení
        now = datetime.now().strftime("%H:%M")
        u_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "user", "content": prompt, "timestamp": now}])
        a_row = pd.DataFrame([{"user_id": "public", "chat_id": st.session_state.chat_id, "role": "assistant", "content": ai_text, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([users_df, u_row, a_row], ignore_index=True))
        
        # Statistiky
        stats_df.loc[stats_df['key'] == 'total_messages', 'value'] = str(total_msgs + 1)
        conn.update(worksheet="Stats", data=stats_df)
        st.rerun()
    else:
        st.error("Chyba: AI neodpovídá. Zkontroluj API klíče v Secrets.")

st.markdown('</div>', unsafe_allow_html=True)
