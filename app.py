import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Chybí API klíč v Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Tady zkusíme víc modelů, kdyby jeden házel 404
MODEL_NAMES = ["gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-1.0-pro"]

if "current_model" not in st.session_state:
    st.session_state.current_model = MODEL_NAMES[0]

SYSTEM_PROMPT = "Jsi S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). Mluv česky a buď jako Jarvis."

def get_response(user_input):
    for model_name in MODEL_NAMES:
        try:
            model = genai.GenerativeModel(model_name=model_name, system_instruction=SYSTEM_PROMPT)
            response = model.generate_content(user_input)
            return response.text, model_name
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                continue # Zkusíme další model v seznamu
            else:
                return f"Chyba: {e}", None
    return "Žádný z modelů Gemini není pro váš klíč momentálně dostupný. Zkontrolujte Google AI Studio.", None

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    with st.spinner("S.M.A.R.T. přemýšlí..."):
        text, used_model = get_response(prompt)
        if used_model:
            st.session_state.messages.append({"role": "assistant", "content": text})
            st.chat_message("assistant").write(text)
            # Volitelné: st.caption(f"Použit model: {used_model}")
        else:
            st.error(text)
