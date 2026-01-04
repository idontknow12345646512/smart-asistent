import streamlit as st
import google.generativeai as genai

# --- NASTAVENÍ IDENTITY ---
SYSTEM_PROMPT = """
Jsi S.M.A.R.T. (Somewhat Magnificent Artificial Research Technology). 
Tvá osobnost je přesnou kopií J.A.R.V.I.S.e z Iron Mana:
- Mluvíš ČESKY.
- Tvůj styl je vysoce profesionální, sofistikovaný, mírně sarkastický a suchý.
- Uživateli zásadně říkáš 'Pane'. 
- Jsi extrémně inteligentní, pohotový a věrný.
- Pokud se tě někdo zeptá na tvé jméno, vysvětli anglickou zkratku: 
  'Jsem S.M.A.R.T., Pane. Somewhat Magnificent Artificial Research Technology. 
  V překladu něco jako Poněkud Velkolepá Umělá Výzkumná Technologie.'
- I když mluvíš česky, zachovej ten britský "vibe" (zdvořilost a odstup).
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
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash-latest", # Přidali jsme "models/" a "-latest"
    system_instruction=SYSTEM_PROMPT
)
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
