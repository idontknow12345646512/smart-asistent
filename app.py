import streamlit as st
import google.generativeai as genai
from shared import global_store 
import urllib.parse
import requests
import random
from io import BytesIO
from PIL import Image

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

# --- POLLINATIONS FUNKCE ---
def get_pollinations_image(prompt_text):
    seed = random.randint(1, 9999999)
    encoded_prompt = urllib.parse.quote(prompt_text)
    # Použijeme model 'turbo' pro maximální stabilitu na školní síti
    url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=turbo&nologo=true"
    
    try:
        headers = {'User-Agent': f'SMART_User_{seed}'}
        response = requests.get(url, timeout=30, headers=headers)
        if response.status_code == 200:
            img_content = response.content
            try:
                # Ověření, že jde o skutečný obrázek
                Image.open(BytesIO(img_content)).verify()
                return img_content
            except:
                return None
    except:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Systémová jádra")
    # Tady jsou modely přesně podle tvých screenshotů
    model_choice = st.selectbox("Výběr procesoru:", [
        "gemini-3-flash", 
        "gemini-2.5-flash", 
        "gemini-2.5-flash-lite"
    ])
    image_mode = st.toggle("Grafický procesor (AI Art) 🎨")
    if st.button("🗑️ Reset paměti"):
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

# --- LOGIKA ---
if prompt := st.chat_input("Zadejte příkaz pro S.M.A.R.T..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Nalezení aktivního klíče
    active_model = None
    for key in api_keys:
        if not key: continue
        try:
            genai.configure(api_key=key)
            active_model = genai.GenerativeModel(model_choice)
            break
        except:
            continue

    if not active_model:
        st.error("🚨 Systémová chyba: API klíče nejsou dostupné.")
        st.stop()

    with st.chat_message("assistant"):
        if image_mode:
            status = st.empty()
            status.info("🧠 Model " + model_choice + " navrhuje vizuál...")
            
            try:
                # Gemini 3 Flash připraví detailní popis v angličtině
                architect_query = f"Create a short, powerful English image prompt for: {prompt}. Artistic style, 8k, detailed. Output ONLY the prompt."
                eng_prompt = active_model.generate_content(architect_query).text
                
                status.info("🎨 Kreslím obraz přes Pollinations...")
                img_data = get_pollinations_image(eng_prompt)
                
                if img_data:
                    status.empty()
                    st.image(img_data, use_container_width=True)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"Vizuální záznam vytvořen ({model_choice})", 
                        "image_bytes": img_data
                    })
                else:
                    status.error("❌ Grafický server neodpovídá. Zkus to prosím za chvilku.")
            except Exception as e:
                status.error(f"Chyba: {e}")
        else:
            # Klasický textový chat
            chat_hist = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                         for m in st.session_state.messages[:-1] if "content" in m]
            try:
                chat = active_model.start_chat(history=chat_hist)
                response = chat.send_message(prompt)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Chyba jádra {model_choice}: {e}")
