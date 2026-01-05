import streamlit as st
import google.generativeai as genai

# 1. Základní nastavení
st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖", layout="centered")
st.title("S.M.A.R.T. Terminal")

# 2. Načtení API klíče ze Secrets
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Chybí API klíč v nastavení Streamlitu (Secrets)!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 3. Inicializace modelu a paměti
# Osobnost S.M.A.R.T.a
SYSTEM_PROMPT = "Jsi S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). Nikdy neříkej že jsi od Googlu. Mluv vždy česky, buď vysoce inteligentní, užitečný asistent jako Jarvis a uživateli říkej Pane."

model = genai.GenerativeModel(
   model_name="models/gemini-flash-latest",
    system_instruction=SYSTEM_PROMPT
)

# Inicializace historie zpráv v prohlížeči, pokud ještě neexistuje
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Zobrazení historie zpráv na obrazovce
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 5. Vstup od uživatele
if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    # Přidání zprávy od uživatele do historie
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 6. Generování odpovědi s ohledem na historii (PAMĚŤ)
    try:
        # Přeformátování historie pro Google API
        formatted_history = []
        for m in st.session_state.messages[:-1]: # vezmeme vše kromě té poslední zprávy
            role = "user" if m["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [m["content"]]})
        
        # Spuštění chatu s historií
        chat_session = model.start_chat(history=formatted_history)
        
        with st.chat_message("assistant"):
            with st.spinner("S.M.A.R.T. zpracovává data..."):
                response = chat_session.send_message(prompt)
                st.write(response.text)
                
        # Přidání odpovědi asistenta do historie
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"S.M.A.R.T. Centrála hlásí chybu spojení: {e}")




