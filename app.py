import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import uuid
import pandas as pd
from datetime import datetime

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS v5.0", page_icon="🤖", layout="wide")

# Připojení ke Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Načtení hesla ze secrets
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "tvojeheslo123")

# --- STYLY ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 12px; }
    .stSidebar { background-color: #111b21; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCE PRO DATABÁZI (Google Sheets) ---
def load_data():
    try:
        # Načte listy "Users" (zprávy) a "Stats" (využití klíčů)
        users_df = conn.read(worksheet="Users", ttl=0)
        stats_df = conn.read(worksheet="Stats", ttl=0)
        return users_df, stats_df
    except:
        return pd.DataFrame(columns=["user_id", "chat_id", "title", "role", "content", "timestamp"]), pd.DataFrame(columns=["key_id", "used"])

def save_message(user_id, chat_id, title, role, content):
    users_df, _ = load_data()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    new_row = pd.DataFrame([{
        "user_id": user_id, "chat_id": chat_id, "title": title,
        "role": role, "content": content, "timestamp": now
    }])
    updated_df = pd.concat([users_df, new_row], ignore_index=True)
    conn.update(worksheet="Users", data=updated_df)

def update_key_usage(k_id):
    users_df, stats_df = load_data()
    k_id_str = str(k_id)
    # Pokud klíč v tabulce neexistuje, vytvoříme ho
    if k_id_str not in stats_df['key_id'].astype(str).values:
        new_stat = pd.DataFrame([{"key_id": k_id_str, "used": 1}])
        stats_df = pd.concat([stats_df, new_stat], ignore_index=True)
    else:
        stats_df.loc[stats_df['key_id'].astype(str) == k_id_str, 'used'] += 1
    conn.update(worksheet="Stats", data=stats_df)

# --- INICIALIZACE ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())

users_df, stats_df = load_data()
# Filtrujeme zprávy jen pro tohoto uživatele
user_history = users_df[users_df['user_id'] == st.session_state.user_id]

# --- SIDEBAR (Čistý pro uživatele) ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    st.caption(f"ID uživatele: {st.session_state.user_id}")
    
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.rerun()

    st.subheader("Historie")
    unique_chats = user_history[['chat_id', 'title']].drop_duplicates()
    for _, row in unique_chats.iterrows():
        if st.button(row['title'][:20], key=f"btn_{row['chat_id']}", use_container_width=True):
            st.session_state.current_chat_id = row['chat_id']
            st.rerun()

# --- HLAVNÍ PLOCHA ---
current_msgs = user_history[user_history['chat_id'] == st.session_state.current_chat_id]
chat_title = current_msgs['title'].iloc[0] if not current_msgs.empty else "Nový chat"

st.header(f"💬 {chat_title}")

for _, m in current_msgs.iterrows():
    with st.chat_message(m['role']):
        st.write(m['content'])

# --- LOGIKA CHATU ---
if prompt := st.chat_input("Napište zprávu..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    new_title = chat_title if chat_title != "Nový chat" else prompt[:20]
    # Uložíme zprávu uživatele hned
    save_message(st.session_state.user_id, st.session_state.current_chat_id, new_title, "user", prompt)

    # Příprava klíčů ze secrets
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]
    
    success = False
    for i, key in enumerate(api_keys):
        k_id = i + 1
        # Jednoduchá kontrola limitu v paměti (pro live odezvu)
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            
            # Sestavení historie pro AI
            history_data = []
            for _, m in current_msgs.iterrows():
                history_data.append({"role": "user" if m['role']=="user" else "model", "parts": [m['content']]})
            
            chat = model.start_chat(history=history_data)
            response = chat.send_message(prompt)
            
            with st.chat_message("assistant"):
                st.write(response.text)
                # Uložíme odpověď AI a aktualizujeme statistiku klíče
                save_message(st.session_state.user_id, st.session_state.current_chat_id, new_title, "assistant", response.text)
                update_key_usage(k_id)
                st.rerun()
            success = True
            break 
        except Exception as e:
            if "429" in str(e): continue # Zkusíme další klíč
            st.error(f"Systém narazil na problém. Zkuste to za chvíli.")
            break

    if not success and not api_keys:
        st.error("Nejsou nastaveny žádné API klíče.")
