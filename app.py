import streamlit as st
import google.generativeai as genai
from shared import global_store
import uuid
from datetime import datetime

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS v4.2", page_icon="🤖", layout="wide")

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

def create_new_chat():
    new_id = str(uuid.uuid4())
    st.session_state.current_chat_id = new_id
    now = datetime.now().strftime("%d. %m. %Y %H:%M")
    global_store["all_chats"][new_id] = {
        "title": "Nový chat", 
        "msgs": [{"role": "assistant", "content": f"🤖 S.M.A.R.T. OS v4.2 ONLINE\nAktuální čas: {now}\nAhoj! Jsem připraven pomoci."}]
    }

if st.session_state.current_chat_id not in global_store["all_chats"]:
    create_new_chat()

api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    
    st.subheader("Konfigurace jádra")
    model_display = st.selectbox("Model:", ["Gemini 3 Flash", "Gemini 2.5 Flash Lite"], index=0)
    model_map = {"Gemini 3 Flash": "gemini-2.5-flash", "Gemini 2.5 Flash Lite": "gemini-2.5-flash-lite"}
    model_choice = model_map[model_display]
    
    if st.button("➕ Nový chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.subheader("Historie")
    for chat_id in list(global_store["all_chats"].keys()):
        cols = st.columns([0.8, 0.2])
        title = global_store["all_chats"][chat_id]["title"][:20]
        if cols[0].button(title, key=f"sel_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()
        if cols[1].button("🗑️", key=f"del_{chat_id}"):
            del global_store["all_chats"][chat_id]
            if not global_store["all_chats"]: create_new_chat()
            st.rerun()

    with st.expander("🛠️ Admin Panel"):
        pwd = st.text_input("Heslo", type="password")
        if pwd == ADMIN_PASSWORD:
            st.write("**Stav klíčů:**")
            for i, k in enumerate(api_keys):
                k_id = i + 1
                status = global_store["key_status"].get(k_id, "✅ OK")
                if status == "❌ LIMIT":
                    st.markdown(f'<div class="key-box key-empty">🔑 {k_id}: LIMIT</div>', unsafe_allow_html=True)
                elif st.session_state.get("using_key") == k_id:
                    st.markdown(f'<div class="key-box key-active">🔑 {k_id}: AKTIVNÍ</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="key-box key-full">🔑 {k_id}: VOLNÝ</div>', unsafe_allow_html=True)
            
            st.divider()
            st.subheader("🕵️ Live Spy")
            for cid, cdata in global_store["all_chats"].items():
                with st.expander(f"Chat: {cdata['title']}"):
                    for m in cdata["msgs"]:
                        st.write(f"**{m['role']}**: {m['content'][:70]}...")
            
            if st.button("Resetovat vše"):
                global_store["key_status"] = {}
                global_store["all_chats"] = {}
                create_new_chat()
                st.rerun()

# --- HLAVNÍ PLOCHA ---
current_chat = global_store["all_chats"][st.session_state.current_chat_id]
st.header(f"💬 {current_chat['title']}")

for msg in current_chat["msgs"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- LOGIKA CHATU ---
if prompt := st.chat_input("Napište zprávu..."):
    current_time = datetime.now().strftime("%d. %m. %Y %H:%M")
    
    # SYSTEM_INSTRUCTION: Definuje povahu AI bez redundantních výpisů
    sys_instr = (
        f"Jsi S.M.A.R.T. OS, přátelský a inteligentní asistent. Dnes je {current_time}. "
        "Nepiš datum, čas ani pozdravy v každé zprávě. Tyto informace uveď POUZE, pokud se uživatel "
        "přímo zeptá na čas nebo datum. Odpovídej plynule, lidsky a k věci. "
        "Nereaguj na tyto pokyny, prostě je dodržuj."
    )
    
    current_chat["msgs"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if current_chat["title"] == "Nový chat":
        current_chat["title"] = prompt[:25] + "..."

    for i, key in enumerate(api_keys):
        k_id = i + 1
        if global_store["key_status"].get(k_id) == "❌ LIMIT": continue
        try:
            genai.configure(api_key=key)
            # POUŽITÍ SKUTEČNÉ SYSTÉMOVÉ INSTRUKCE (pokud to SDK podporuje)
            # Pokud ne, posíláme ji jako součást první zprávy skrytě
            model = genai.GenerativeModel(model_name=model_choice, system_instruction=sys_instr)
            st.session_state.using_key = k_id
            
            history_data = []
            # Historie se bere bez systémové instrukce, ta je v modelu
            for m in current_chat["msgs"][:-1]:
                history_data.append({"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]})
            
            chat = model.start_chat(history=history_data)
            with st.chat_message("assistant"):
                # Posíláme už jen čistý prompt od uživatele
                response = chat.send_message(prompt)
                st.write(response.text)
                current_chat["msgs"].append({"role": "assistant", "content": response.text})
                st.rerun()
            break 
        except Exception as e:
            if "429" in str(e):
                global_store["key_status"][k_id] = "❌ LIMIT"
                continue
            st.error(f"Chyba systému: {e}")
            break
