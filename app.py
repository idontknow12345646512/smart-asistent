import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")

# Načtení klíče
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Chybí API klíč v Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Definice modelu - zkusíme nejzákladnější stabilní volání
# Pokud toto vyhodí 404, model pro váš klíč skutečně neexistuje
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Nepodařilo se inicializovat model: {e}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        # Přidáme instrukci přímo do promptu pro maximální stabilitu
        full_prompt = f"Jsi S.M.A.R.T., mluv česky a říkej mi Pane. Odpověz na: {prompt}"
        response = model.generate_content(full_prompt)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"S.M.A.R.T. Centrála hlásí chybu: {e}")
        st.info("Tip: Pokud vidíte '404', váš klíč nemá přístup k modelu Gemini 1.5 Flash.")
