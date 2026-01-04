import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")

# 1. Načtení klíče
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Chybí API klíč v Secrets!")
    st.stop()

# 2. Nastavení modelu - POUŽÍVÁME NÁZEV Z VAŠÍ DIAGNOSTIKY
# Vybral jsem 2.0-flash, který je ve vašem seznamu
SYSTEM_PROMPT = "Jsi S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). Mluv česky a buď jako Jarvis."

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash", 
    system_instruction=SYSTEM_PROMPT
)

# 3. Chatovací historie
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 4. Samotná komunikace
if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        response = model.generate_content(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"Chyba: {e}")
