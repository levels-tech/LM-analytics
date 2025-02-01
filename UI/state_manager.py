import time
from pathlib import Path
import streamlit as st
import pickle
import io

# Lista di variabili da NON salvare nel pickle
EXCLUDED_STATE_VARS = {
    'restored_from_state',
    'state_upload',
    'files_processed',
    'FormSubmitter:process_files_button-True'
}

# Aggiungiamo anche i prefissi da escludere
EXCLUDED_PREFIXES = {
    'FormSubmitter:',
    'form',
    'multiselect',
    'confirm_changes_button_',
    'widget_'
}

class SessionStateManager:
    def __init__(self, autosave_path="last_state.pkl", max_age_hours=24):
        self.autosave_path = Path(autosave_path)
        self.max_age_hours = max_age_hours
    
    def _filter_state(self, state_dict):
        """Rimuove le variabili che non devono essere salvate"""
        return {
            k: v for k, v in state_dict.items() 
            if (k not in EXCLUDED_STATE_VARS and 
                not any(k.startswith(prefix) for prefix in EXCLUDED_PREFIXES))
        }
    
    def get_state_as_bytes(self):
        """
        Converte lo stato corrente in bytes per il download
        """
        try:
            state_data = {
                'timestamp': time.time(),
                'state': self._filter_state(dict(st.session_state))
            }
            buffer = io.BytesIO()
            pickle.dump(state_data, buffer)
            return buffer.getvalue()
        except Exception as e:
            st.error(f"Errore durante la preparazione dello stato: {str(e)}")
            return None
    
    def save_state(self):
        """
        Salva lo stato corrente nel file autosave
        """
        try:
            state_data = {
                'timestamp': time.time(),
                'state': self._filter_state(dict(st.session_state))
            }
            with open(self.autosave_path, 'wb') as f:
                pickle.dump(state_data, f)
            return True
        except Exception as e:
            st.error(f"Errore durante il salvataggio dello stato: {str(e)}")
            return False
    
    def load_state_from_bytes(self, state_bytes):
        """
        Carica lo stato da bytes
        """
        try:
            state_data = pickle.loads(state_bytes)
            if not isinstance(state_data, dict) or 'timestamp' not in state_data or 'state' not in state_data:
                st.error("Il file caricato non contiene un formato di stato valido")
                return None
                
            age_hours = (time.time() - state_data['timestamp']) / 3600
            if age_hours > self.max_age_hours:
                st.error(f"Il file di stato è più vecchio di {self.max_age_hours} ore")
                return None
                
            return state_data['state']
            
        except Exception as e:
            st.error(f"Errore durante il caricamento dello stato: {str(e)}")
            return None
    
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
                
            age_hours = (time.time() - state_data['timestamp']) / 3600
            if age_hours > self.max_age_hours:
                return None
                
            return state_data['state']
            
        except Exception as e:
            st.error(f"Errore durante il caricamento dello stato: {str(e)}")
            return None