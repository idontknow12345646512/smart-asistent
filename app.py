import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
import random

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. Ultimate", page_icon="🤖", layout="wide")

# Funkce pro generování obrázku přes Hugging Face (profesionální API)
def generate_hf_image(prompt_text):
    # Model Stable Diffusion XL - velmi stabilní a kvalitní
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    # Token si vlož do Streamlit Secrets jako HF_TOKEN
    headers = {"Authorization": f"Bearer {st.secrets.get('HF_TOKEN')}"}
    
    try:
        payload = {"inputs": prompt_text}
        response = requests.post(API_URL, headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            return response.content
    except:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ S.M.A.R.T. Ovládání")
    model_choice = st.radio("Jádro AI:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    image_mode = st.toggle("Mód obrázků 🎨")
    if st.button("🗑️ Reset chatu"):
        st.session_state.messages = []
        st.rerun()

# Načtení Google klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

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
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Najdeme funkční Gemini klíč pro překlad nebo chat
    active_model = None
    for i, key in enumerate(api_keys):
        key_id = i + 1
        if global_store.get("key_status", {}).get(key_id) == "❌ LIMIT": continue
        try:
            genai.configure(api_key=key)
            active_model = genai.GenerativeModel(model_choice)
            # Test funkčnosti klíče
            break
        except:
            global_store["key_status"][key_id] = "❌ LIMIT"

    if image_mode:
        with st.chat_message("assistant"):
            p = st.empty()
            p.info("🧠 Gemini vylepšuje zadání pro grafické jádro...")
            
            # 1. KROK: Gemini přeloží a vylepší prompt (aby to nebylo jen "pes", ale profi popis)
            try:
                enhance_prompt = f"Rewrite this image prompt into a detailed, professional English artistic description for Stable Diffusion: {prompt}. Output ONLY the English description."
                response = active_model.generate_content(enhance_prompt)
                english_prompt = response.text
            except:
                english_prompt = prompt # Záloha, pokud Gemini selže

            p.info("🎨 Stabilní jádro generuje obraz...")
            
            # 2. KROK: Hugging Face vygeneruje obrázek
            img = generate_hf_image(english_prompt)
            
            if img:
                p.empty()
                st.image(img, use_container_width=True)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Vizuál vytvořen (SDXL). Zadání: {prompt}", 
                    "image_bytes": img
                })
            else:
                p.error("❌ Grafické jádro je momentálně přetížené. Zkus to za chvíli.")
    
    else:
        # KLASICKÝ CHAT
        chat_context = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                        for m in st.session_state.messages[:-1] if "content" in m]
        
        if active_model:
            try:
                chat = active_model.start_chat(history=chat_context)
                res = chat.send_message(prompt)
                response_text = res.text
            except Exception as e:
                response_text = f"Chyba: {str(e)}"
        else:
            response_text = "❌ Žádný funkční API klíč nebyl nalezen."

        with st.chat_message("assistant"):
            st.write(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
