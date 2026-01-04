import streamlit as st
import google.generativeai as genai

# 1. Načtení klíče
api_key = st.secrets["AIzaSyDkI3d4VdVClJBMlblDB0fh_dNZA_lFMHE"]

# 2. Konfigurace - ZDE JE ZMĚNA (přidána verze v1beta)
genai.configure(api_key=api_key)

# 3. Definice identity
SYSTEM_PROMPT = "Jsi S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). Mluv česky, buď jako Jarvis a říkej mi Pane."

# 4. Inicializace modelu - ZDE JSME PŘIDALI 'models/'
# Pokud nepůjde flash, zkus 'models/gemini-1.0-pro'
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

st.title("S.M.A.R.T. Terminal")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        # Volání AI
        response = model.generate_content(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"Došlo k chybě v komunikaci: {e}")
