import streamlit as st
import google.generativeai as genai

st.title("S.M.A.R.T. Terminal")

# Přímé nastavení bez složitostí
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Vložte klíč do Secrets!")
    st.stop()

# Zkusíme nejstabilnější verzi názvu
model = genai.GenerativeModel('gemini-1.5-flash')

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        # Žádné systémové instrukce, jen čistý text pro test
        response = model.generate_content(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"Chyba: {e}")
