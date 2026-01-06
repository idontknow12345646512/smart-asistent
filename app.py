import streamlit as st
import google.generativeai as genai
from shared import global_store
import uuid

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS v3.2", page_icon="🤖", layout="wide")

ADMIN_PASSWORD = "tvojeheslo123"

# --- STYLY ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 12px; }
    .stSidebar { background-color: #111b21; }
    .key-box { padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid #444; font-size: 0.8rem; }
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

api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    
    st.subheader("Konfigurace jádra")
    # POUŽITÍ PŘESNÝCH NÁZVŮ Z TVÉHO SCREENSHOTU
    model_display = st.selectbox(
        "Vyberte model:",
        ["Gemini 3 Flash", "Gemini 2.5 Flash Lite"],
        index=0
    )
    
    # Mapování na systémové názvy, které vyžaduje API
    model_map = {
        "Gemini 3 Flash": "gemini-3-flash",
        "Gemini 2.5 Flash Lite": "gemini-2.5-flash-lite"
    }
    model_choice = model_map[model_display]
    
    if model_choice == "gemini-3-flash":
        st.warning("⚠️ Jádro v3: Max 5 zpráv / min")
    else:
        st.info("⚠️ Jádro v2.5 Lite: Max 10 zpráv / min")

    if st.button("➕ Nový chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.current_chat_id = new_id
        global_store["all_chats"][new_id] = {"title": "Nový chat", "msgs": []}
        st.rerun()

    st.subheader("Historie")
    for chat_id in list(global_store["all_chats"].keys()):
        cols = st.columns([0.8, 0.2])
        if cols[0].button(global_store["all_chats"][chat_id]["title"][:20], key=f"sel_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()
        if cols[1].button("🗑️", key=f"del_{chat_id}"):
            del global_store["all_chats"][chat_id]
            st.rerun()

    st.divider()
    
    with st.expander("🛠️ Admin Panel"):
        pwd = st.text_input("Heslo", type="password")
        if pwd == ADMIN_PASSWORD:
            st.success("Admin přístup")
            st.write("**Stav klíčů:**")
            for i, k in enumerate(api_keys):
                k_id = i + 1
                status = global_store["key_status"].get(k_id, "✅ Volný")
                
                if status == "❌ LIMIT":
                    st.markdown(f'<div class="key-box key-empty">🔑 {k_id}: PRÁZDNÝ (LIMIT)</div>', unsafe_allow_html=True)
                elif "using_key" in st.session_state and st.session_state.using_key == k_id:
                    st.markdown(f'<div class="key-box key-active">🔑 {k_id}: POUŽÍVÁN NYNÍ</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="key-box key-full">🔑 {k_id}: PLNÝ / PŘIPRAVEN</div>', unsafe_allow_html=True)
            
            if st.button("Resetovat limity"):
                global_store["key_status"] = {}
                st.rerun()

# --- HLAVNÍ PLOCHA ---
current_chat = global_store["all_chats"][st.session_state.current_chat_id]
st.header(f"💬 {current_chat['title']}")

# Zobrazení historie
for msg in current_chat["msgs"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- LOGIKA CHATU ---
if prompt := st.chat_input("Zadejte příkaz..."):
    current_chat["msgs"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if current_chat["title"] == "Nový chat":
        current_chat["title"] = prompt[:25]

    active_model = None
    
    # Hledání klíče
    for i, key in enumerate(api_keys):
        k_id = i + 1
        if global_store["key_status"].get(k_id) == "❌ LIMIT": continue
            
        try:
            genai.configure(api_key=key)
            # POUŽITÍ PŘESNÉHO NÁZVU MODELU
            active_model = genai.GenerativeModel(model_name=model_choice)
            st.session_state.using_key = k_id
            
            # Testovací volání pro ověření limitu
            history_data = []
            for m in current_chat["msgs"][:-1]:
                history_data.append({"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]})
            
            chat = active_model.start_chat(history=history_data)
            
            with st.chat_message("assistant"):
                response = chat.send_message(prompt)
                st.write(response.text)
                current_chat["msgs"].append({"role": "assistant", "content": response.text})
                st.rerun()
            break 
            
        except Exception as e:
            if "429" in str(e) or "limit" in str(e).lower():
                global_store["key_status"][k_id] = "❌ LIMIT"
                continue
            else:
                st.error(f"Chyba u modelu {model_choice}: {e}")
                break

    if not active_model:
        st.error("🚨 Žádné volné klíče nebo model není dostupný.")
