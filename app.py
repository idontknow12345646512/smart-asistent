import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse  # Důležité pro opravu těch obrázků!

# --- KONFIGURACE ---
st.set_page_config(
    page_title="S.M.A.R.T. App",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stChatMessage { font-size: 1.1rem !important; border-radius: 15px !important; }
    @media (max-width: 600px) { .stTitle { font-size: 2rem !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Systém")
    model_choice = st.radio("Procesor:", ["gemini-2.5-flash-lite", "gemini-1.5-pro"])
    st.divider()
    image_mode = st.toggle("Mód generování obrázků 🎨")
    if st.button("🗑️ Vyčistit paměť"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], use_container_width=True)

# --- LOGIKA VSTUPU ---
if prompt := st.chat_input("Zadejte příkaz..."):
    now = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)

    log_entry = {"time": now, "user_text": prompt, "ai_text": "Zpracovávám..."}
    global_store["logs"].append(log_entry)
    current_log_index = len(global_store["logs"]) - 1

    if image_mode:
        # --- OPRAVA OBRÁZKŮ (Kódování textu) ---
        seed = datetime.now().microsecond
        # Tohle převede "Černý mustang" na formát, který funguje v URL:
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux"
        
        response_text = f"🎨 Generuji vizualizaci pro: **{prompt}**"
        
        with st.chat_message("assistant"):
            st.write(response_text)
            st.image(image_url, use_container_width=True)
            
        st.session_state.messages.append({"role": "assistant", "content": response_text, "image_url": image_url})
        global_store["logs"][current_log_index]["ai_text"] = "[OBRÁZEK]"
    
    else:
        # TEXTOVÝ CHAT
        chat_context = []
        for m in st.session_state.messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            if "content" in m:
                chat_context.append({"role": role, "parts": [m["content"]]})

        response_text = "⚠️ Jádra offline."
        
        for i, key in enumerate(api_keys):
            key_id = i + 1
            if global_store["key_status"].get(key_id) == "❌ LIMIT": continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_choice)
                chat = model.start_chat(history=chat_context)
                res = chat.send_message(prompt)
                response_text = res.text
                break 
            except Exception as e:
                if "429" in str(e): global_store["key_status"][key_id] = "❌ LIMIT"

        with st.chat_message("assistant"):
            st.write(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        global_store["logs"][current_log_index]["ai_text"] = response_text
