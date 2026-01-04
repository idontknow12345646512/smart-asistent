import streamlit as st
import google.generativeai as genai

# 1. Konfigurace stránky
st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")

# 2. Načtení klíče
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Chybí API klíč v Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 3. Nastavení modelu (bez mezer navíc)
SYSTEM_PROMPT = "Jsi S.M.A.R.T. Mluv česky a buď jako Jarvis."

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

# 4. Chatovací historie
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. Chatování
if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        response = model.generate_content(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"Chyba: {e}")
