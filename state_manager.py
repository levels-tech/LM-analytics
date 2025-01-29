import streamlit as st
import pickle
import time
# import io
from pathlib import Path

class SessionStateManager:
    def __init__(self, autosave_path="last_state.pkl", max_age_hours=24):
        self.autosave_path = Path(autosave_path)
        self.max_age_hours = max_age_hours
    
    def save_state(self):
        """
        Salva lo stato corrente nel file autosave insieme al timestamp
        """
        state_dict = {
            'data': {
                key: value for key, value in st.session_state.items()
                if isinstance(value, (str, int, float, bool, list, dict))
            },
            'timestamp': time.time()
        }
        
        try:
            with open(self.autosave_path, 'wb') as f:
                pickle.dump(state_dict, f)
            return True
        except Exception as e:
            st.error(f"Errore durante il salvataggio dello stato: {str(e)}")
            return False
    
    def load_last_state(self):
        """
        Carica l'ultimo stato salvato se non è troppo vecchio
        """
        if not self.autosave_path.exists():
            st.warning("Nessun stato precedente trovato")
            return None
            
        try:
            with open(self.autosave_path, 'rb') as f:
                saved_data = pickle.load(f)
            
            if not isinstance(saved_data, dict) or 'data' not in saved_data or 'timestamp' not in saved_data:
                st.error("Il file dello stato non contiene un formato valido")
                return None
                
            # Controlla l'età dello stato salvato
            age_hours = (time.time() - saved_data['timestamp']) / 3600
            if age_hours > self.max_age_hours:
                st.warning(f"Lo stato salvato è più vecchio di {self.max_age_hours} ore. Ripristino non consentito.")
                return None
                
            return saved_data['data']
            
        except Exception as e:
            st.error(f"Errore durante il caricamento dello stato: {str(e)}")
            return None
    
    def get_state_age_hours(self):
        """
        Restituisce l'età dello stato salvato in ore, o None se non esiste
        """
        if not self.autosave_path.exists():
            return None
            
        try:
            with open(self.autosave_path, 'rb') as f:
                saved_data = pickle.load(f)
            
            if not isinstance(saved_data, dict) or 'timestamp' not in saved_data:
                return None
                
            return (time.time() - saved_data['timestamp']) / 3600
            
        except Exception:
            return None