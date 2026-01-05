import streamlit as st
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="S.M.A.R.T. Chat", page_icon="🤖")

# --- SDÍLENÁ PAMĚŤ ---
if "global_chat_history" not in st.session_state:
    st.session_state.global_chat_history = []
if "key_usage" not in st.session_state:
    st.session_state.key_usage = {f"Jádro {i}": "✅ OK" for i in range(1, 11)}

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Zadejte příkaz pro S.M.A.R.T.a..."):
    now = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # MONITORING: Zapíšeme zprávu pro Admina
    st.session_state.global_chat_history.append({"time": now, "user": "Student", "text": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # Logika AI s rotací klíčů
    response_text = "Všechna jádra jsou offline."
    for i, key in enumerate(api_keys):
        key_name = f"Jádro {i+1}"
        if st.session_state.key_usage[key_name] == "❌ LIMIT": continue
        
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
            res = model.generate_content(prompt)
            response_text = res.text
            break
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                st.session_state.key_usage[key_name] = "❌ LIMIT"
    
    with st.chat_message("assistant"):
        st.write(response_text)
    st.session_state.messages.append({"role": "assistant", "content": response_text})
