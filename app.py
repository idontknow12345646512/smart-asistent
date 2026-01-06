import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store
import uuid

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

# Custom CSS pro "Gemini" vzhled
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stChatInput { border-radius: 20px; }
    .sidebar-content { background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACE STAVU ---
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())
if st.session_state.current_chat_id not in global_store["all_chats"]:
    global_store["all_chats"][st.session_state.current_chat_id] = {"title": "Nový chat", "msgs": []}

# --- SIDEBAR: HISTORIE KONVERZACÍ ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.current_chat_id = str(uuid.uuid4())
        global_store["all_chats"][st.session_state.current_chat_id] = {"title": "Nový chat", "msgs": []}
        st.rerun()

    st.subheader("Historie")
    # Zobrazení seznamu chatů
    for chat_id in list(global_store["all_chats"].keys()):
        cols = st.columns([0.8, 0.2])
        if cols[0].button(global_store["all_chats"][chat_id]["title"], key=f"select_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()
        if cols[1].button("🗑️", key=f"del_{chat_id}"):
            del global_store["all_chats"][chat_id]
            if st.session_state.current_chat_id == chat_id:
                st.session_state.current_chat_id = str(uuid.uuid4())
                global_store["all_chats"][st.session_state.current_chat_id] = {"title": "Nový chat", "msgs": []}
            st.rerun()

    st.divider()
    
    # --- ADMIN ROZHRANÍ ---
    with st.expander("🛠️ Admin Panel"):
        st.write("**Stav API klíčů:**")
        for k_id, status in global_store.get("key_status", {}).items():
            st.write(f"Klíč {k_id}: {status}")
        
        st.write(f"**Celkem chatů v paměti:** {len(global_store['all_chats'])}")
        if st.button("🔥 Vymazat všechna data"):
            global_store["all_chats"] = {}
            global_store["key_status"] = {}
            st.rerun()

# --- HLAVNÍ PLOCHA ---
current_chat = global_store["all_chats"][st.session_state.current_chat_id]

# Dynamický název chatu podle první zprávy
st.title(current_chat["title"])

# Zobrazení zpráv z historie aktuálního chatu
for msg in current_chat["msgs"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- LOGIKA CHATU ---
if prompt := st.chat_input("Zeptejte se na cokoliv..."):
    # Uložení zprávy uživatele
    current_chat["msgs"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Aktualizace názvu chatu, pokud je to první zpráva
    if current_chat["title"] == "Nový chat":
        current_chat["title"] = prompt[:30] + "..." if len(prompt) > 30 else prompt
        st.rerun()

    # Hledání funkčního klíče
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]
    active_model = None
    
    for i, key in enumerate(api_keys):
        k_id = i + 1
        if global_store["key_status"].get(k_id) == "❌ LIMIT": continue
        try:
            genai.configure(api_key=key)
            active_model = genai.GenerativeModel("gemini-1.5-flash") # Stabilní verze
            break
        except:
            global_store["key_status"][k_id] = "❌ LIMIT"
            continue

    if active_model:
        with st.chat_message("assistant"):
            try:
                # Příprava historie pro model
                history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                          for m in current_chat["msgs"][:-1]]
                
                chat = active_model.start_chat(history=history)
                response = chat.send_message(prompt)
                
                st.write(response.text)
                current_chat["msgs"].append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Chyba: {e}")
    else:
        st.error("Žádný funkční klíč.")
