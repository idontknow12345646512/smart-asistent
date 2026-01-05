import streamlit as st
import google.generativeai as genai
import datetime

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="S.M.A.R.T. Central Command", layout="wide")

# Inicializace globální historie v paměti serveru (pro zobrazení adminovi)
if "global_logs" not in st.session_state:
    st.session_state.global_logs = []
if "key_status" not in st.session_state:
    st.session_state.key_status = {}

# Načtení klíčů (1-10) z tvých Secrets
api_keys = []
for i in range(1, 11):
    k = st.secrets.get(f"GOOGLE_API_KEY_{i}")
    if k: api_keys.append({"id": i, "key": k})

# --- ADMIN PANEL (SIDEBAR) ---
with st.sidebar:
    st.title("🛡️ Admin Console")
    password = st.text_input("Zadejte Master Key", type="password")
    
    if password == "radek123":
        st.success("Vítejte zpět, Pane.")
        
        # 1. Monitoring klíčů
        st.subheader("Stav energetických jader")
        for k_info in api_keys:
            status = "✅ ONLINE" if k_info['id'] not in st.session_state.key_status else "❌ DEPLETED"
            st.write(f"Jádro {k_info['id']}: {status}")
            
        # 2. Globální historie zpráv (Co píše třída)
        st.subheader("🕵️ Monitoring komunikace")
        if st.session_state.global_logs:
            for log in reversed(st.session_state.global_logs):
                st.text(f"[{log['time']}] {log['user']}: {log['msg'][:30]}...")
                if st.button(f"Zobrazit detail", key=f"btn_{log['time']}"):
                    st.info(f"Celá zpráva: {log['msg']}")
        else:
            st.write("Zatím žádná aktivita.")
            
        if st.button("Vymazat logy"):
            st.session_state.global_logs = []
            st.rerun()
    else:
        st.info("Sekce pro Operátora systému.")

# --- CHAT LOGIKA ---
st.title("🤖 S.M.A.R.T. Terminal")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie (každý uživatel vidí jen tu svou)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

def ask_smart(prompt, history):
    for k_info in api_keys:
        if k_info['id'] in st.session_state.key_status:
            continue
        try:
            genai.configure(api_key=k_info['key'])
            model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
            chat = model.start_chat(history=history)
            response = chat.send_message(prompt)
            return response.text, k_info['id']
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                st.session_state.key_status[k_info['id']] = "Full"
                continue
            return f"Error: {e}", None
    return "Všechna jádra jsou vyčerpána.", None

if prompt := st.chat_input("Zadejte příkaz..."):
    # Uložíme do historie uživatele
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Uložíme do GLOBÁLNÍCH logů pro Admina (tebe)
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.global_logs.append({"time": timestamp, "user": "Student", "msg": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)

    # Příprava historie pro AI
    formatted_history = []
    for m in st.session_state.messages[:-1]:
        role = "user" if m["role"] == "user" else "model"
        formatted_history.append({"role": role, "parts": [m["content"]]})

    with st.chat_message("assistant"):
        res_text, used_id = ask_smart(prompt, formatted_history)
        st.write(res_text)
        if used_id:
            st.caption(f"Aktivní jádro: {used_id} | Limit: 20 RPD")
            
    st.session_state.messages.append({"role": "assistant", "content": res_text})
