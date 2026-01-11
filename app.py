import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import uuid
import io
from docx import Document # Pro generování Wordu

# --- 1. KONFIGURACE A STYLY ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    [data-testid="stStatusWidget"], .stDeployButton, footer, #MainMenu, header { display: none !important; }
    .thinking-box {
        background-color: #1e2129; border-left: 5px solid #0288d1;
        padding: 15px; border-radius: 5px; color: #e0e0e0;
        font-weight: bold; margin: 10px 0;
    }
    .fixed-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        text-align: center; color: #888; font-size: 0.8rem;
        padding: 15px; background: #0e1117;
        border-top: 1px solid #262730; z-index: 1000;
    }
    .main-content { margin-bottom: 120px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POMOCNÉ FUNKCE (Export Word) ---
def create_docx(text):
    doc = Document()
    doc.add_heading('S.M.A.R.T. OS - Exportovaný dokument', 0)
    doc.add_paragraph(text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. SESSION STATE ---
if "user_id" not in st.session_state: st.session_state.user_id = str(uuid.uuid4())[:8]
if "chat_id" not in st.session_state: st.session_state.chat_id = str(uuid.uuid4())[:8]
if "last_ai_response" not in st.session_state: st.session_state.last_ai_response = ""

# --- 4. DATABÁZE ---
conn = st.connection("gsheets", type=GSheetsConnection)
def load_db():
    try: return conn.read(worksheet="Users", ttl=0)
    except: return pd.DataFrame(columns=["user_id", "chat_id", "title", "role", "content", "timestamp"])

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🤖 S.M.A.R.T. OS")
    if st.button("➕ Nový chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())[:8]
        st.session_state.last_ai_response = ""
        st.rerun()
    
    st.divider()
    st.subheader("📁 1. Nahrávání souborů")
    uploaded_file = st.file_uploader("PDF, Obrázky, TXT", type=["png", "jpg", "jpeg", "pdf", "txt", "csv"])
    
    st.divider()
    st.subheader("📄 4. Generování")
    if st.session_state.last_ai_response:
        st.download_button(
            label="📥 Stáhnout poslední odpověď jako .docx",
            data=create_docx(st.session_state.last_ai_response),
            file_name=f"smart_export_{datetime.now().strftime('%H%M%S')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

# --- 6. CHAT ROZHRANÍ ---
df = load_db()
current_chat = df[df["chat_id"] == st.session_state.chat_id]

st.subheader("💬 S.M.A.R.T. Chat (v6.0)")
st.markdown('<div class="main-content">', unsafe_allow_html=True)
for _, m in current_chat.iterrows():
    with st.chat_message(m["role"]):
        st.write(m["content"])

# --- 7. LOGIKA (S VYHLEDÁVÁNÍM, LaTeXem A MULTIMODALITOU) ---
if prompt := st.chat_input("Napište zprávu..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    thinking = st.empty()
    thinking.markdown('<div class="thinking-box">🤖 SMART analyzuje, vyhledává a přemýšlí...</div>', unsafe_allow_html=True)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11)]
    
    # Příprava historie
    history = []
    for _, m in current_chat.iterrows():
        history.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})

    # Příprava obsahu (Multimodalita)
    content_to_send = [prompt]
    if uploaded_file:
        file_bytes = uploaded_file.read()
        if uploaded_file.type in ["text/plain", "text/csv"]:
            content_to_send.append(f"\n\nObsah souboru:\n{file_bytes.decode('utf-8')}")
        else:
            content_to_send.append({"mime_type": uploaded_file.type, "data": file_bytes})

    success = False
    for key in api_keys:
        if not key: continue
        try:
            genai.configure(api_key=key)
            # POUŽITÍ GOOGLE SEARCH (Nástroje)
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                tools=[{"google_search_retrieval": {}}], # 3. Webový vyhledávač
                system_instruction="Jsi S.M.A.R.T. OS. Používej LaTeX pro matiku (např. $$x^2$$). Pomáhej se školou."
            )
            
            chat_session = model.start_chat(history=history)
            response = chat_session.send_message(content_to_send)
            
            ai_text = response.text
            st.session_state.last_ai_response = ai_text # Uložení pro export
            success = True
            break
        except: continue

    thinking.empty()

    if success:
        with st.chat_message("assistant"):
            st.markdown(ai_text) # 2. Podpora Markdown a LaTeX
            
        u_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.chat_id, "title": prompt[:20], "role": "user", "content": prompt, "timestamp": now}])
        ai_row = pd.DataFrame([{"user_id": st.session_state.user_id, "chat_id": st.session_state.chat_id, "title": prompt[:20], "role": "assistant", "content": ai_text, "timestamp": now}])
        conn.update(worksheet="Users", data=pd.concat([df, u_row, ai_row], ignore_index=True))
        st.rerun()
    else:
        st.error("❌ Chyba spojení.")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="fixed-footer">S.M.A.R.T. OS může dělat chyby.</div>', unsafe_allow_html=True)
