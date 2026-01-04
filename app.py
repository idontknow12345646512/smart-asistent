import streamlit as st
import google.generativeai as genai
from google.generativeai.types import RequestOptions

st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")

# Načtení klíče
api_key = st.secrets["GOOGLE_API_KEY"]

# --- KLÍČOVÁ ZMĚNA: Vynutíme verzi v1 ---
genai.configure(api_key=api_key, transport='rest') # Přepnuto na REST transport

SYSTEM_PROMPT = "Jsi S.M.A.R.T. Mluv česky, buď jako Jarvis a říkej mi Pane."

# Zkusíme model bez prefixu a s explicitním nastavením
model = genai.GenerativeModel('gemini-1.5-flash')

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        # Použijeme RequestOptions pro vynucení verze API
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nUživatel: {prompt}",
            request_options=RequestOptions(api_version='v1') # Přepnuto na stabilní v1
        )
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"S.M.A.R.T. Centrála hlásí: {e}")
