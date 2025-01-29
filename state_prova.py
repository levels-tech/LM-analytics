import streamlit as st
from state_manager import SessionStateManager

def initialize_state():
    """
    Inizializza lo stato di default se non esistente
    """
    if 'counter' not in st.session_state:
        st.session_state.counter = 0
    if 'text_input' not in st.session_state:
        st.session_state.text_input = ""

st.title("Demo Salvataggio Stato")
    
# Inizializza il gestore dello stato (5 min come tempo massimo)
state_manager = SessionStateManager(max_age_hours=0.083)

# Mostra l'età dell'ultimo stato salvato
state_age = state_manager.get_state_age_hours()
st.write(state_manager.max_age_hours)
if state_age is not None:
    st.info(f"Ultimo stato salvato {state_age:.1f} ore fa")

# Pulsante per ripristinare l'ultimo stato
state_is_valid = state_age is not None and state_age <= state_manager.max_age_hours
restore_button = st.button(
    "Ripristina Ultimo Stato",
    disabled=not state_is_valid,
    help="Il ripristino è possibile solo se lo stato è stato salvato negli ultimi 5 minuti"
)

if restore_button:
    state_dict = state_manager.load_last_state()
    if state_dict is not None:
        try:
            # Resetta lo stato corrente
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Applica il nuovo stato
            for key, value in state_dict.items():
                st.session_state[key] = value
            st.success("Ultimo stato ripristinato con successo!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore nel ripristino dello stato: {str(e)}")

# Inizializza lo stato di default se necessario
initialize_state()

# UI per input
st.text_input("Inserisci del testo:", key="text_input")

def increment_and_save():
    # Incrementa il contatore
    st.session_state.counter += 1
    # Salva lo stato
    if state_manager.save_state():
        st.write("Stato salvato automaticamente")

st.button("Incrementa Contatore", on_click=increment_and_save)

# Mostra lo stato corrente
st.write("Contatore:", st.session_state.counter)
st.write("Testo inserito:", st.session_state.text_input)

# Mostra lo stato corrente in formato JSON
st.json(dict(st.session_state))