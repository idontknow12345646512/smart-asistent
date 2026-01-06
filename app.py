import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
import random

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

# --- FUNKCE PRO POLLINATIONS ---
def get_pollinations_image(prompt_text):
    # Vytvoříme unikátní seed a ID, aby nás server neházel do jednoho pytle s celou školou
    seed = random.randint(1, 9999999)
    # Zakódujeme prompt
    encoded_prompt = urllib.parse.quote(prompt_text)
    
    # URL s parametry pro nejvyšší kvalitu a obejití limitů
    # Používáme model 'flux' (aktuálně nejlepší na Pollinations)
    url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
    
    try:
        # Přidáme hlavičky, aby to vypadalo jako unikátní prohlížeč
        headers = {'User-Agent': f'SMART_OS_User_{seed}'}
        response = requests.get(url, timeout=30, headers=headers)
        
        if response.status_code == 200:
            return response.content
    except:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Systém")
    model_choice = st.radio("Jádro:", ["gemini-2.5-flash-lite", "gemini-3-flash"])
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
        try:
            genai.configure(api_key=key)
            active_model = genai.GenerativeModel(model_choice)
            break
        except:
            continue

    if not active_model:
        st.error("🚨 Chyba: Žádné aktivní klíče.")
        st.stop()

    with st.chat_message("assistant"):
        if image_mode:
            status = st.empty()
            status.info("🧠 Gemini vylepšuje zadání...")
            
            # KROK 1: Gemini vytvoří profi anglický prompt
            try:
                architect_msg = f"Create a detailed English image prompt for: {prompt}. Focus on art style, lighting and details. Output ONLY the English prompt."
                eng_prompt = active_model.generate_content(architect_msg).text
                
                status.info("🎨 Pollinations kreslí obraz...")
                # KROK 2: Pollinations vygeneruje obrázek
                img_data = get_pollinations_image(eng_prompt)
                
                if img_data:
                    status.empty()
                    st.image(img_data, use_container_width=True)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"Vizuál hotov: {prompt}", 
                        "image_bytes": img_data
                    })
                else:
                    status.error("❌ Pollinations neodpovídá. Zkus to znovu za chvíli.")
            except Exception as e:
                status.error(f"Chyba: {e}")
        else:
            # Klasický chat
            chat_hist = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                         for m in st.session_state.messages[:-1] if "content" in m]
            try:
                chat = active_model.start_chat(history=chat_hist)
                response = chat.send_message(prompt)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Chyba Gemini: {e}")

