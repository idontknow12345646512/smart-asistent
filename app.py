import streamlit as st
import google.generativeai as genai

# Konfigurace stránky
st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")

# Načtení klíče
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Chybí API klíč v Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Osobnost
SYSTEM_PROMPT = "Jsi S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). Mluv česky a buď jako Jarvis."

# Inicializace modelu - zkusíme nejstabilnější verzi
@st.cache_resource
def load_model():
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash", # Zkusíme bez prefixu models/
        system_instruction=SYSTEM_PROMPT
    )

model = load_model()

# Chatovací historie
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        # PŘÍMÉ VOLÁNÍ
        response = model.generate_content(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"SIRIUS ERROR: {e}")
        # DEBUG: Vypíše modely, které tvůj klíč skutečně vidí
        st.write("Dostupné modely pro váš klíč:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                st.write(f"- {m.name}")
