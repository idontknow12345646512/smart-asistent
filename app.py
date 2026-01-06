import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store
import uuid

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS v3.1", page_icon="🤖", layout="wide")

ADMIN_PASSWORD = "tvojeheslo123"

# --- STYLY ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 12px; }
    .stSidebar { background-color: #111b21; }
    .key-box { padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid #444; }
    .key-full { background-color: #155724; color: #d4edda; }
    .key-empty { background-color: #721c24; color: #f8d7da; }
    .key-active { background-color: #0c5460; color: #d1ecf1; border: 2px solid #fff; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACE ---
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())

if "all_chats" not in global_store:
    global_store["all_chats"] = {}

if "key_status" not in global_store:
    global_store["key_status"] = {}

if st.session_state.current_chat_id not in global_store["all_chats"]:
    global_store["all_chats"][st.session_state.current_chat_id] = {"title": "Nový chat", "msgs": []}

# Načtení klíčů ze secrets
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    
    # Výběr modelu s varováním
    st.subheader("Konfigurace jádra")
    model_choice = st.selectbox(
        "Vyberte model:",
        ["gemini-3-flash", "gemini-2.5-flash-lite"],
        help="Každý model má své rychlostní limity."
    )
    
    # Varování podle modelu
    if model_choice == "gemini-3-flash":
        st.warning("⚠️ Limit: Max 5 zpráv / min")
    else:
        st.warning("⚠️ Limit: Max 10 zpráv / min")

    if st.button("➕ Nový chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.current_chat_id = new_id
        global_store["all_chats"][new_id] = {"title": "Nový chat", "msgs": []}
        st.rerun()

    st.subheader("Historie")
    for chat_id in list(global_store["all_chats"].keys()):
        cols = st.columns([0.8, 0.2])
        if cols[0].button(global_store["all_chats"][chat_id]["title"], key=f"sel_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()
        if cols[1].button("🗑️", key=f"del_{chat_id}"):
            del global_store["all_chats"][chat_id]
            st.rerun()

    st.divider()
    
    # --- ADMIN SEKCE S PŘEHLEDEM KLÍČŮ ---
    with st.expander("🛠️ Admin Panel"):
        pwd = st.text_input("Heslo", type="password")
        if pwd == ADMIN_PASSWORD:
            st.success("Admin přístup")
            
            # Statistiky klíčů
            st.write("**Stav zásobníků (Klíčů):**")
            used_count = 0
            for i, k in enumerate(api_keys):
                k_id = i + 1
                status = global_store["key_status"].get(k_id, "✅ Volný")
                
                # Vizualizace stavu
                if status == "❌ LIMIT":
                    st.markdown(f'<div class="key-box key-empty">🔑 Klíč {k_id}: VYČERPÁN</div>', unsafe_allow_html=True)
                elif "using" in st.session_state and st.session_state.using == k_id:
                    st.markdown(f'<div class="key-box key-active">🔑 Klíč {k_id}: AKTIVNÍ</div>', unsafe_allow_html=True)
                    used_count += 1
                else:
                    st.markdown(f'<div class="key-box key-full">🔑 Klíč {k_id}: PŘIPRAVEN</div>', unsafe_allow_html=True)

            st.write(f"Využito: {len(global_store['all_chats'])} chatů")
            if st.button("Resetovat limity klíčů"):
                global_store["key_status"] = {}
                st.rerun()
        elif pwd != "":
            st.error("Špatné heslo")

# --- HLAVNÍ PLOCHA ---
current_chat = global_store["all_chats"][st.session_state.current_chat_id]
st.header(f"💬 {current_chat['title']}")

for msg in current_chat["msgs"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- LOGIKA CHATU ---
if prompt := st.chat_input("Napište zprávu..."):
    current_chat["msgs"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if current_chat["title"] == "Nový chat":
        current_chat["title"] = prompt[:25] + "..."

    active_model = None
    
    # Rotace a monitoring klíčů
    for i, key in enumerate(api_keys):
        k_id = i + 1
        if global_store["key_status"].get(k_id) == "❌ LIMIT":
            continue
            
        try:
            genai.configure(api_key=key)
            # Mapování na reálné názvy modelů pro API (v1beta)
            # Poznámka: gemini-3-flash nahrazujeme nejnovějším dostupným v API
            api_model_name = "gemini-1.5-flash" if "3" in model_choice else "gemini-1.5-flash-8b"
            
            active_model = genai.GenerativeModel(api_model_name)
            st.session_state.using = k_id # Označíme klíč jako právě používaný
            break
        except:
            global_store["key_status"][k_id] = "❌ LIMIT"
            continue

    if active_model:
        with st.chat_message("assistant"):
            try:
                history_data = []
                for m in current_chat["msgs"][:-1]:
                    history_data.append({"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]})
                
                chat = active_model.start_chat(history=history_data)
                response = chat.send_message(prompt)
                
                st.write(response.text)
                current_chat["msgs"].append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ Dosáhli jste limitu zpráv za minutu pro tento klíč!")
                    global_store["key_status"][st.session_state.using] = "❌ LIMIT"
                else:
                    st.error(f"Chyba: {e}")
    else:
        st.error("Žádné volné klíče!")
