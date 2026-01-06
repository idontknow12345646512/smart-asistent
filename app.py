import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
from io import BytesIO

# --- KONFIGURACE PRO MOBILY A TABLETY ---
st.set_page_config(
    page_title="S.M.A.R.T. Terminal",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS pro opravu vzhledu na různých zařízeních
st.markdown("""
    <style>
    .stChatMessage { font-size: 1.1rem !important; border-radius: 15px !important; }
    /* Zvětšení vstupního pole na mobilu */
    @media (max-width: 600px) {
        .stChatInputContainer { padding-bottom: 50px !important; }
        .stTitle { font-size: 1.8rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- POMOCNÁ FUNKCE PRO OBRÁZKY ---
def get_image_data(url):
    try:
        # Stáhneme obrázek přímo na server, aby ho prohlížeč neblokoval
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        st.error(f"Chyba při stahování obrazových dat: {e}")
    return None

# --- SIDEBAR (NASTAVENÍ) ---
with st.sidebar:
    st.header("⚙️ Konfigurace S.M.A.R.T.")
    
    # Přepínání modelů
    model_choice = st.radio(
        "Výkonové jádro:",
        ["gemini-2.5-flash-lite", "gemini-1.5-pro"],
        help="Flash je bleskový, Pro je chytřejší, ale má přísné limity."
    )
    
    st.divider()
    
    # Mód obrázků
    image_mode = st.toggle("Generátor vizualizací 🎨")
    if image_mode:
        st.info("Režim obrázků aktivní.")
    
    if st.button("🗑️ Vymazat historii"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů ze Secrets
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")

# Paměť zpráv
if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_bytes" in msg:
            st.image(msg["image_bytes"], use_container_width=True)

# --- LOGIKA VSTUPU ---
if prompt := st.chat_input("Zadejte příkaz..."):
    now = datetime.now().strftime("%H:%M:%S")
    
    # 1. Zobrazení uživateli
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 2. Logování pro Admina
    log_entry = {"time": now, "user_text": prompt, "ai_text": "Generování..."}
    global_store["logs"].append(log_entry)
    current_log_index = len(global_store["logs"]) - 1

    # --- ZPRACOVÁNÍ: OBRÁZKY ---
    if image_mode:
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            status_placeholder.write("🎨 Sestavuji vizuální data...")
            
            # Kódování textu pro URL (řeší háčky a čárky)
            encoded_prompt = urllib.parse.quote(prompt)
            seed = datetime.now().microsecond
            image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux"
            
            # Stažení obrázku
            img_bytes = get_image_data(image_url)
            
            if img_bytes:
                status_placeholder.empty()
                st.image(img_bytes, use_container_width=True)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Vizuální záznam: {prompt}", 
                    "image_bytes": img_bytes
                })
                global_store["logs"][current_log_index]["ai_text"] = "[OBRÁZEK]"
            else:
                st.error("Nepodařilo se spojit s obrazovým jádrem.")
    
    # --- ZPRACOVÁNÍ: TEXT ---
    else:
        # Příprava kontextu pro Gemini
        chat_context = []
        for m in st.session_state.messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            if "content" in m:
                chat_context.append({"role": role, "parts": [m["content"]]})

        response_text = "⚠️ Všechna jádra jsou offline (zkontrolujte limity)."
        
        # Rotace klíčů
        for i, key in enumerate(api_keys):
            key_id = i + 1
            if global_store["key_status"].get(key_id) == "❌ LIMIT":
                continue
            
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_choice)
                chat = model.start_chat(history=chat_context)
                res = chat.send_message(prompt)
                response_text = res.text
                break 
            except Exception as e:
                if "429" in str(e):
                    global_store["key_status"][key_id] = "❌ LIMIT"

        with st.chat_message("assistant"):
            st.write(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        global_store["logs"][current_log_index]["ai_text"] = response_text
