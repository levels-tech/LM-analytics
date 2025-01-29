import streamlit as st
import pickle
from pathlib import Path
import time

class SessionStateManager:
    def __init__(self, autosave_path="last_state.pkl", max_age_hours=24):
        self.autosave_path = Path(autosave_path)
        self.max_age_hours = max_age_hours
    
    def save_state(self):
        """
        Salva lo stato corrente nel file autosave
        """
        try:
            state_data = {
                'timestamp': time.time(),
                'state': dict(st.session_state)
            }
            with open(self.autosave_path, 'wb') as f:
                pickle.dump(state_data, f)
            return True
        except Exception as e:
            st.error(f"Errore durante il salvataggio dello stato: {str(e)}")
            return False
    
    def load_last_state(self):
        """
        Carica l'ultimo stato salvato se non è troppo vecchio
        """
        if not self.autosave_path.exists():
            return None
            
        try:
            with open(self.autosave_path, 'rb') as f:
                state_data = pickle.load(f)
                
            if not isinstance(state_data, dict) or 'timestamp' not in state_data or 'state' not in state_data:
                return None
                
            # Controlla l'età dello stato salvato
            age_hours = (time.time() - state_data['timestamp']) / 3600
            if age_hours > self.max_age_hours:
                return None
                
            return state_data['state']
            
        except Exception as e:
            st.error(f"Errore durante il caricamento dello stato: {str(e)}")
            return None