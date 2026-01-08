import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Admin Panel", layout="wide")

# --- TVRDÁ OCHRANA HESLEM ---
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# Funkce pro zpracování hesla
def check_password():
    if st.session_state["pwd_input"] == st.secrets["ADMIN_PASSWORD"]:
        st.session_state.admin_logged_in = True
        st.success("Přihlášeno!")
    else:
        st.error("Nesprávné heslo!")
    
    # Tady se děje to kouzlo: Vymažeme hodnotu klíče 'pwd_input' ze stavu aplikace
    st.session_state["pwd_input"] = ""

if not st.session_state.admin_logged_in:
    st.title("🔐 Chráněná zóna")
    
    # Používáme parametr 'key', abychom k políčku mohli přistupovat přes session_state
    # 'on_change' nebo přímý stisk tlačítka vyvolá smazání
    st.text_input("Zadejte admin heslo", type="password", key="pwd_input")
    
    if st.button("Vstoupit"):
        check_password()
        # Pokud se heslo shodovalo, stránka se díky rerun() překreslí už jako přihlášená
        if st.session_state.admin_logged_in:
            st.rerun()
            
    st.stop() # Zastaví veškerý kód pod tímto řádkem

# --- KÓD ADMINA (spustí se jen po přihlášení) ---
# (Sem zkopíruj zbytek svého admin kódu z předchozí verze)
conn = st.connection("gsheets", type=GSheetsConnection)
st.title("📊 Administrace")

if st.button("Odhlásit"):
    st.session_state.admin_logged_in = False
    st.rerun()

try:
    users_df = conn.read(worksheet="Users", ttl=0)
    stats_df = conn.read(worksheet="Stats", ttl=0)
    
    # Rychlé statistiky
    total_used = stats_df['used'].sum()
    st.metric("Celkem dotazů přes Flash modely", total_used)
    
    # Spy prohlížeč
    uid = st.selectbox("Vyberte ID zařízení:", users_df['user_id'].unique())
    st.table(users_df[users_df['user_id'] == uid])

except Exception as e:
    st.error(f"Chyba při načítání dat: {e}")
