import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 

st.set_page_config(page_title="S.M.A.R.T. Chat", page_icon="🤖")

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")

# Paměť pro probíhající chat (vydrží do F5)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení chatu
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Zadejte příkaz..."):
    now = datetime.now().strftime("%H:%M:%S")
    
    # 1. Monitoring pro admina
    global_store["logs"].append({"time": now, "text": prompt})
    
    # 2. Zobrazení uživateli
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # --- TA NEJDŮLEŽITĚJŠÍ ČÁST: PŘÍPRAVA KONTEXTU ---
    # Vytvoříme seznam zpráv tak, jak ho Gemini vyžaduje pro paměť
    chat_context = []
    for m in st.session_state.messages[:-1]: # Vezmeme všechny starší zprávy
        role = "user" if m["role"] == "user" else "model"
        chat_context.append({"role": role, "parts": [m["content"]]})

    response_text = "Všechna jádra jsou offline."
    
    for i, key in enumerate(api_keys):
        key_id = i + 1
        if global_store["key_status"].get(key_id) == "❌ LIMIT": continue
        
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
            
            # TADY SE DĚJE TA MAGIE: Spustíme chat i s historií
            chat = model.start_chat(history=chat_context)
            res = chat.send_message(prompt)
            
            response_text = res.text
            break 
        except Exception as e:
            if "429" in str(e):
                global_store["key_status"][key_id] = "❌ LIMIT"
    
    with st.chat_message("assistant"):
        st.write(response_text)
    
    st.session_state.messages.append({"role": "assistant", "content": response_text})
