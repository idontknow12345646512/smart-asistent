import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
import random
from io import BytesIO
from PIL import Image

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

# --- FUNKCE PRO POLLINATIONS S VALIDACÍ ---
def get_pollinations_image(prompt_text):
    seed = random.randint(1, 9999999)
    encoded_prompt = urllib.parse.quote(prompt_text)
    
    # Používáme model 'flux' pro nejlepší kvalitu
    url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
    
    try:
        headers = {'User-Agent': f'SMART_OS_User_{seed}'}
        response = requests.get(url, timeout=30, headers=headers)
        
        if response.status_code == 200:
            # --- KLÍČOVÁ OPRAVA: Kontrola, zda jsou data skutečně obrázek ---
            img_content = response.content
            try:
                img = Image.open(BytesIO(img_content))
                img.verify() # Ověří, zda je soubor nepoškozený
                return img_content
            except Exception:
                return None # Data nejsou validní obrázek (např. chybová hláška v textu)
    except:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Systém")
    # Aktualizované názvy modelů
    model_choice = st.radio("Jádro:", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"])
    image_mode = st.toggle("Generátor obrazu 🎨")
    if st.button("🗑️ Reset"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_bytes" in msg:
            st.image(msg["image_bytes"], use_container_width=True)

# --- HLAVNÍ LOGIKA ---
if prompt := st.chat_input("Zadejte příkaz..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Výběr funkčního klíče Gemini
    active_model = None
    for key in api_keys:
        if not key: continue
        try:
            genai.configure(api_key=key)
            active_model = genai.GenerativeModel(model_choice)
            # Zkušební volání (volitelné)
            break
        except:
            continue

    if not active_model:
        st.error("🚨 Chyba: Žádné aktivní klíče Gemini nebyly nalezeny.")
        st.stop()

    with st.chat_message("assistant"):
        if image_mode:
            status = st.empty()
            status.info("🧠 Gemini vylepšuje zadání pro grafiku...")
            
            try:
                # Gemini přeloží a vylepší prompt pro Pollinations
                architect_msg = f"Create a short, detailed English image prompt for: {prompt}. Focus on lighting and art style. Output ONLY the English prompt."
                response = active_model.generate_content(architect_msg)
                eng_prompt = response.text
                
                status.info("🎨 Pollinations kreslí obraz (Flux jádro)...")
                img_data = get_pollinations_image(eng_prompt)
                
                if img_data:
                    status.empty()
                    st.image(img_data, use_container_width=True)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"Vizuál pro: {prompt}", 
                        "image_bytes": img_data
                    })
                else:
                    status.error("❌ Grafické jádro poslalo nečitelná data nebo je přetížené. Zkus to prosím znovu.")
            except Exception as e:
                status.error(f"Chyba při generování: {e}")
        else:
            # Klasický chat
            chat_hist = []
            for m in st.session_state.messages[:-1]:
                if "content" in m:
                    role = "user" if m["role"] == "user" else "model"
                    chat_hist.append({"role": role, "parts": [m["content"]]})
            
            try:
                chat = active_model.start_chat(history=chat_hist)
                response = chat.send_message(prompt)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Chyba Gemini: {e}")
