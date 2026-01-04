import streamlit as st
import google.generativeai as genai

# Konfigurace vzhledu
st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")
st.markdown("---")

# 1. Kontrola klíče v Secrets
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ CHYBA: API klíč nebyl nalezen v nastavení Streamlitu (Secrets).")
    st.stop()

api_key = st.secrets["GOOGLE_API_KEY"]

if not api_key or api_key == "sem_vloz_tvuj_klic":
    st.error("❌ CHYBA: API klíč v Secrets je prázdný nebo neplatný.")
    st.stop()

# 2. Nastavení AI
try:
    genai.configure(api_key=api_key)
    # Zkusíme nejuniverzálnější název modelu
        model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest", 
    system_instruction=SYSTEM_PROMPT
)
        system_instruction="Jsi S.M.A.R.T., asistent jako Jarvis. Mluv česky a říkej mi Pane."
    )
except Exception as e:
    st.error(f"❌ Chyba při konfiguraci AI: {e}")
    st.stop()

# 3. Chatovací historie
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 4. Samotný chat
if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            # Tady zkusíme vygenerovat odpověď
            response = model.generate_content(prompt)
            if response.text:
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            else:
                st.warning("AI vrátila prázdnou odpověď. Zkuste jiný dotaz.")
        except Exception as e:
            st.error(f"❌ S.M.A.R.T. se nemohl spojit s centrálou.")
            st.info("Zkuste v Google AI Studiu vytvořit ÚPLNĚ NOVÝ klíč.")
            st.exception(e) # Toto vypíše detail chyby

