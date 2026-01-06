import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 

# Nastavení stránky optimalizované i pro mobily
st.set_page_config(page_title="S.M.A.R.T. Terminal", page_icon="🤖", layout="centered")

# --- SIDEBAR: OVLÁDACÍ CENTRUM ---
with st.sidebar:
    st.title("🛡️ S.M.A.R.T. Config")
    
    # Elegantnější výběr modelu
    st.subheader("Výkon systému")
    model_choice = st.radio(
        "Vyberte procesorové jádro:",
        ["gemini-2.5-flash-lite", "gemini-1.5-pro"],
        help="Flash je velmi rychlý. Pro je extrémně chytrý, ale má nízké limity."
    )
    
    st.divider()
    
    # Mód generování obrázků
    st.subheader("Výstupní moduly")
    image_mode = st.toggle("Generátor vizualizací (DALL-E mód) 🎨")
    if image_mode:
        st.warning("Režim obrázků aktivní. AI bude tvořit grafiku.")

# Načtení tvých 10 API klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")
st.caption(f"Aktuální konfigurace: {model_choice}")

# Paměť chatu (maže se po F5)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"], use_container_width=True)

# --- VSTUP OD UŽIVATELE ---
if prompt := st.chat_input("Zadejte příkaz..."):
    now = datetime.now().strftime("%H:%M:%S")
    
    # Zápis do historie a logu
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    log_entry = {"time": now, "user_text": prompt, "ai_text": "Zpracovávám..."}
    global_store["logs"].append(log_entry)
    current_log_index = len(global_store["logs"]) - 1

    if image_mode:
        # Generování obrázku přes Pollinations (zdarma a spolehlivé)
        # Upravíme prompt, aby byl v URL bezpečný
        clean_prompt = prompt.replace(" ", "_").replace("?", "")
        image_url = f"https://pollinations.ai/p/{clean_prompt}?width=1024&height=1024&seed={datetime.now().second}"
        
        response_text = f"🎨 Generuji vizualizaci pro: **{prompt}**"
        
        with st.chat_message("assistant"):
            st.write(response_text)
            st.image(image_url, use_container_width=True)
            
        st.session_state.messages.append({"role": "assistant", "content": response_text, "image_url": image_url})
        global_store["logs"][current_log_index]["ai_text"] = "[Obrázek vygenerován]"
    
    else:
        # Klasický textový chat s historií (kontextem)
        chat_context = []
        for m in st.session_state.messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            if "content" in m:
                chat_context.append({"role": role, "parts": [m["content"]]})

        response_text = "⚠️ Všechna jádra offline. Zkontrolujte API klíče v Secrets."
        
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
                if "429" in str(e) or "Quota" in str(e):
                    global_store["key_status"][key_id] = "❌ LIMIT"
                else:
                    response_text = f"Chyba systému na jádru {key_id}."

        with st.chat_message("assistant"):
            st.write(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        global_store["logs"][current_log_index]["ai_text"] = response_text
