import streamlit as st
import pandas as pd
from model.scripts.call_streamlit import update_df

class PaymentManager:
    def __init__(self):
        if 'payment_manager_state' not in st.session_state:
            st.session_state.payment_manager_state = {
                'payments_to_check': None,      # DataFrame completo dei pagamenti da controllare
                'pending_updates': {},          # Modifiche in attesa di essere applicate
                'completed_payments': set(),    # Set degli ID dei pagamenti già processati
                'processed_count': 0            # Contatore dei pagamenti processati
            }
    
    def initialize_payments_to_check(self, full_payments_df):
        """
        Inizializza la lista dei pagamenti da controllare se non è già stata inizializzata
        """
        if st.session_state.payment_manager_state['payments_to_check'] is None:
            payments_to_check = full_payments_df[
                (full_payments_df["CHECK"] == "NON TROVATO")
            ].copy()
            st.session_state.payment_manager_state['payments_to_check'] = payments_to_check
    
    def get_payments_to_display(self):
        """
        Restituisce tutti i pagamenti da controllare con indicatore di processamento
        """
        all_payments = st.session_state.payment_manager_state['payments_to_check']
        if all_payments is not None:
            display_df = all_payments.copy()
            display_df['processed'] = display_df['original_index'].isin(
                st.session_state.payment_manager_state['completed_payments']
            )
            return display_df
        return pd.DataFrame()
    
    def mark_payment_completed(self, payment_idx):
        """
        Marca un pagamento come completato e incrementa il contatore
        """
        if payment_idx not in st.session_state.payment_manager_state['completed_payments']:
            st.session_state.payment_manager_state['completed_payments'].add(payment_idx)
            st.session_state.payment_manager_state['processed_count'] += 1
    
    def get_processed_count(self):
        """Restituisce il numero di pagamenti processati"""
        return st.session_state.payment_manager_state['processed_count']
    
    def add_pending_update(self, payment_idx, new_values):
        """Aggiunge o aggiorna una modifica in attesa per un pagamento"""
        st.session_state.payment_manager_state['pending_updates'][payment_idx] = new_values
    
    def get_pending_update(self, payment_idx):
        """Recupera una modifica in attesa per un pagamento"""
        return st.session_state.payment_manager_state['pending_updates'].get(payment_idx)
    
    def apply_all_updates(self, main_df, payments_df):
        """
        Applica tutte le modifiche in sospeso ai DataFrame principali
        """
        updates = st.session_state.payment_manager_state['pending_updates']
        
        for idx, new_values in updates.items():
            main_df, payments_df = update_df(main_df, new_values, idx, payments_df)
            
        for idx in st.session_state.payment_manager_state['completed_payments']:
            payments_df.loc[payments_df['original_index'] == idx, 'CHECK'] = "VERO"
        
        return main_df, payments_df
    
    def should_proceed_to_excel(self):
        """
        Verifica se si può procedere alla generazione dell'Excel
        """
        total_to_check = len(self.get_payments_to_display())
        return self.get_processed_count() >= total_to_check
    
    def get_total_payments(self):
        """Restituisce il numero totale di pagamenti da controllare"""
        payments = self.get_payments_to_display()
        return len(payments) if payments is not None else 0
    
    def reset_state(self):
        """Resetta lo stato del manager"""
        st.session_state.payment_manager_state = {
            'payments_to_check': None,
            'pending_updates': {},
            'completed_payments': set(),
            'processed_count': 0
        }