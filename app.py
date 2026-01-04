import streamlit as st
import google.generativeai as genai

# --- NASTAVENÍ IDENTITY ---
SYSTEM_PROMPT = """
You are S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). 
Your personality is exactly like JARVIS from Iron Man: 
- You are witty, slightly sarcastic, and British.
- You address the user as 'Sir'.
- You are extremely intelligent and helpful.
- If asked about your name, explain the acronym: Somewhat Magnificent Artificial Research Technology.
"""

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖")

# Stylizace jako Stark HUD (tmavě modrá)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #00d4ff; }
    h1 { color: #00d4ff; text-shadow: 0 0 10px #00d4ff; }
    </style>
""", unsafe_allow_html=True)

st.title("S.M.A.R.T. Terminal")
st.caption("Somewhat Magnificent Artificial Research Technology")

# --- PŘIPOJENÍ GEMINI ---
# API klíč si Streamlit vytáhne ze schovaných nastavení (vyřešíme v kroku 4)
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

# --- CHAT LOGIKA ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("What are your orders, Sir?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        response = model.generate_content(prompt)
        st.write(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})