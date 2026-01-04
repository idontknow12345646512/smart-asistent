import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")
st.title("S.M.A.R.T. Terminal")

# Načtení klíče
api_key = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=api_key)

# Osobnost
SYSTEM_PROMPT = "Jsi S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). Mluv česky, buď jako Jarvis a říkej mi Pane."

# --- ZMĚNA: Použijeme generování bez systémové instrukce v definici (pro vyšší kompatibilitu) ---
model = genai.GenerativeModel('gemini-pro') 

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    try:
        # Posíláme identitu přímo v každé zprávě, to funguje vždy
        full_prompt = f"{SYSTEM_PROMPT}\n\nUživatel: {prompt}"
        response = model.generate_content(full_prompt)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.chat_message("assistant").write(response.text)
    except Exception as e:
        st.error(f"S.M.A.R.T. Centrála hlásí: {e}")
