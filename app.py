import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 

# --- AUTO-ADAPTIVNÍ NASTAVENÍ ---
# Streamlit automaticky mění layout podle šířky okna
st.set_page_config(
    page_title="S.M.A.R.T. Terminal", 
    page_icon="🤖", 
    layout="wide", # "wide" umožní aplikaci roztáhnout se na tabletu/PC
    initial_sidebar_state="collapsed" # Na mobilu schová menu, aby nepřekáželo
)

# Custom CSS pro lepší vzhled na telefonu (větší písmo, lepší bubliny)
st.markdown("""
    <style>
    .stChatMessage { font-size: 1.1rem !important; }
    @media (max-width: 600px) {
        .stTitle { font-size: 1.8rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (NASTAVENÍ) ---
with st.sidebar:
    st.header("⚙️ Konfigurace")
    
    # Přepínání modelů pomocí tlačítek (lepší pro dotykové displeje)
    model_choice = st.radio(
        "Výkonové jádro:",
        ["gemini-2.5-flash-lite", "gemini-1.5-pro"],
        index=0,
        help="Flash = Rychlost, Pro = Inteligence"
    )
    
    st.divider()
    image_mode = st.toggle("Generátor vizualizací 🎨")
    
    if st.button("Vymazat můj chat"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení chatu
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

    # Logování pro tvůj Admin web
    log_entry = {"time": now, "user_text": prompt, "ai_text": "Zpracovávám..."}
    global_store["logs"].append(log_entry)
    current_log_index = len(global_store["logs"]) - 1

    if image_mode:
        # Generování obrázku
        image_url = f"https://pollinations.ai/p/{prompt.replace(' ', '_')}?width=1024&height=1024&seed={datetime.now().microsecond}"
        res_text = f"🎨 Vizualizace dokončena."
        with st.chat_message("assistant"):
            st.image(image_url, use_container_width=True)
        st.session_state.messages.append({"role": "assistant", "content": res_text, "image_url": image_url})
        global_store["logs"][current_log_index]["ai_text"] = "[OBRÁZEK]"
    else:
        # Chat s rotací klíčů
        chat_context = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                        for m in st.session_state.messages[:-1]]

        response_text = "Všechna jádra jsou offline."
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
