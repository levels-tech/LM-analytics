import pandas as pd
import streamlit as st

from UI.state_manager import auto_save_on_change
from model.scripts.call_streamlit import update_df, missing_fields
from model.scripts.call_streamlit import add_row
from UI.orders_section.order_widgets import OrderWidgets


"""
BLOCCO 1: Inizializzazione e Preparazione Dati
"""
def initialize_brand(df, brand, columns_to_show):
    """Prepara i dataframe principali filtrati"""
    # Filtra per ordini rilevanti
    df_rilevante = df[df["CHECK"] != "ESCLUSO"].copy()

    names_count = get_order_stats(df_rilevante, brand)

    df_rilevante_sorted = df_rilevante.sort_values(by=["CHECK", "Name"])

    # Filtra per brand e ordini da controllare
    brand_df = df_rilevante_sorted[
        (df_rilevante_sorted["CHECK"] != "VERO") & 
        (df_rilevante_sorted["Brand"] == f"{brand}")
    ].copy()
    
    # Drop duplicati e mantieni indice originale
    brand_df = brand_df.drop_duplicates(subset=columns_to_show)
    last_index = brand_df['original_index'].max()
    
    return brand_df, last_index, names_count

def get_order_stats(df_rilevante, brand):
    """Calcola statistiche ordini"""
    names_count = len(df_rilevante[
        df_rilevante["Brand"] == f"{brand}"
    ]["Name"].unique())
    
    return names_count

"""
BLOCCO 2: Gestione Visualizzazione Ordine
"""
class OrderDisplay:
    @staticmethod
    def show_order_header(name: str, name_df: pd.DataFrame):
        """Visualizza header ordine e messaggi informativi"""
        st.markdown("---") 
        st.subheader(f"Ordine: {name}")
        
        check = name_df["CHECK"].values[0]
        metodo = name_df["Payment Method"].values[0]
        
        # Mostra messaggi basati sul CHECK
        if check == "FALSO":
            
            if "Qromo" in metodo:# or "Satispay" in metodo:
                st.write(f"Non è stato possibile determinare con certezza il pagamento corrispondente all'ordine {name}")

            else:
                st.write(f"Il totale non coincide con l'importo effettivamente incassato. Modificare i valori delle colonne opportune.")
                if name_df["Shipping Country"].values[0] == "GB":
                    st.write("Verificare se la **Location** è **LIL House London**")
                st.write(f"Importo effettivamente incassato: **{name_df['Importo Pagato'].values[0]}**")
                
        ## Pagamento corrispondente all'ordine non trovato
        elif check == "NON TROVATO":
            st.write(f"Non è stato trovato un pagamento relativo all'ordine. Modificare i valori delle colonne opportune.")
            if name_df["Shipping Country"].values[0] == "GB":
                st.write("Verificare se la **Location** è **LIL House London**")        
            st.write(f"Importo effettivamente incassato: **0**")

        elif check == "LONDON":
            st.write(f"Il total è corretto, verificare se la **Location** dell'ordine è **LIL House London**")
            st.write(f"Location attuale: **{name_df['Location'].values[0]}**")

        elif check.startswith("VALUTA"):
            st.write(f"Il pagamento non è stato fatto in EURO, confermare l'importo effettivamente incassato.")
            st.write(f"Importo pagato in **{check.split('_')[1]}**: **{name_df['Importo Pagato'].values[0]}**")

        return check, metodo

    @staticmethod
    def show_order_data(name_df: pd.DataFrame, columns_to_show):
        """Visualizza dataframe ordine"""
        st.dataframe(name_df[columns_to_show], use_container_width=True)

"""
BLOCCO 3: Validazione Campi dell'ordine corrente
"""
def validate_current_order(brand_df, name, strings_to_exclude):
       
    # Check for required fields before showing the form
    # Controlla che ("Paid at", "Shipping Country", "Location" e "Lineitem sku") non siano Nan
    # Controlla la presenza di metodi di pagamento multipli (escluse Gift Cards)
    nan, double_payment_method = missing_fields(brand_df, name, strings_to_exclude)

    ## Shows a warning for each missing field            
    if nan:
        # if check == "FALSO":
        st.warning(f"Attenzione: I seguenti campi mancano ed è necessario inserirli per le analisi: {', '.join(nan)}")

        # Show specific requirements for each missing field
        for field in nan:
            if field == "Paid at":
                st.warning("Inserire la data di pagamento nella forma yyyy-mm-dd")
            elif field == "Shipping Country":
                st.warning("Inserire il codice a 2 lettere del paese (e.g. IT)")
            elif field == "Location":
                st.warning("Scegliere tra le locations proposte")
            elif field == "Lineitem sku":
                st.warning("Inserire lo SKU a 12 cifre")

    ## Shows a warning if there are multiple payment methods and asks to choose one
    if double_payment_method:
        st.warning(f"Attenzione: Payment Method va modificato, e va scelto un unico metodo di pagamento effettivamente usato")

    return nan, double_payment_method


"""
BLOCCO 4: Gestione Qromo in Metodo e aggiunta pagamenti
"""
class MethodHandler:
    def __init__(self, pagamenti_df, name_df, name, brand):
        self.pagamenti_df = pagamenti_df
        self.name_df = name_df
        self.name = name
        self.brand = brand

    def handle_method(self, metodo: str):
        if "Qromo" not in metodo:
            st.session_state.numeri_pagamenti.append(self.name_df["Numero Pagamento"].values[0])
            st.session_state.metodo_pagamento = None
            return [], None

        return self._handle_qromo_in_method(metodo)

    def _handle_qromo_in_method(self, metodo: str):
        """Gestisce selezione pagamenti Qromo"""

        total = self.name_df["Total"].values[0]
        paid_at = str(self.name_df["Paid at"].values[0])[:10]

        filtered_rows = self._filter_qromo_payments(total)
        selected, importo_pagato = self._payment_selection(filtered_rows, paid_at, metodo)

        return selected, importo_pagato
        
    def _filter_qromo_payments(self, total: float):
        """Filtra pagamenti Qromo disponibili"""
        filtered = self.pagamenti_df[(self.pagamenti_df["Importo Pagato"] <= total)]
        
        satispay_mask = (filtered["Metodo"] == "Satispay") & (filtered["Numero Pagamento"] == "0")
        qromo_mask = filtered["Metodo"] == "Qromo"
        
        return filtered[satispay_mask | qromo_mask].sort_values(
            by="Data", ascending=False
        )


    def _payment_selection(self, rows: pd.DataFrame, paid_at: str, metodo):
        """Mostra selezione pagamenti"""
        if rows.empty:
            st.session_state.numeri_pagamenti = []
            st.session_state.metodo_pagamento = None
            return [], None
            
        selected = []
        importi = []
        
        st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
        for idx, row in rows.iterrows():
            label = self._format_payment_label(row, paid_at)
            if st.checkbox(label, key=f"widget_{self.name}_{idx}"):
                selected.append(row)
                importi.append(row["Importo Pagato"])
                st.session_state.numeri_pagamenti.append(row["Numero Pagamento"])
                st.session_state.metodo_pagamento = row["Metodo"]
        
        selected, importo_pagato = self._handle_selected_qromo_payments(metodo, selected, sum(importi))

        return selected, importo_pagato
        
    def _format_payment_label(self, row: pd.Series, paid_at: str):
        """Formatta label pagamento"""
        if str(row["Data"]).startswith(paid_at):
            return f"**{row['Importo Pagato']}€ pagati il {row['Data']}**"
        return f"{row['Importo Pagato']}€ pagati il {row['Data']}"


    # Handle selected payments and verifies double assignments in case it warns the user 
    # otherwise updates the list of payments to be added
    # Suggest the user to change the total if the sum of the selected payments is different from the total 
    def _handle_selected_qromo_payments(self, metodo, selected, sum_importi):
        if not selected:
            st.write("Non hai selezionato alcun pagamento.")
            st.write("Cambia il **Total** con **0**")
            return [0], 0.0
        
        if self.brand == "lil":
            self._handle_multiple_payment_assignments_lil()

        elif self.brand == "agee":
            self._handle_multiple_payment_assignments_agee()
        
        # Display selected payments info
        importo_pagato = sum_importi
        st.write(f"Cambia il **Total** con **{importo_pagato:.2f}**")
        
        if metodo.replace("Gift Card", "").replace("+", "").replace(" ", "") != st.session_state.metodo_pagamento:  # Added .iloc[0]
            st.write(f"Cambia il **Payment Method** con **{st.session_state.metodo_pagamento}**")
            st.session_state['cambiare_metodo'] = True

        return selected, importo_pagato

    def _handle_multiple_payment_assignments_lil(self):
        # Check for already assigned payments
        for numero in st.session_state.numeri_pagamenti:
            if numero in st.session_state.pagamenti_da_aggiungere_lil.keys():
                matching_name = st.session_state.pagamenti_da_aggiungere_lil[numero]
                
                ## Non permette doppio assegnamento di pagamenti a ordini
                if matching_name != self.name:
                    st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")
    
    def _handle_multiple_payment_assignments_agee(self):
        # Check for already assigned payments
        for numero in st.session_state.numeri_pagamenti:
            if numero in st.session_state.pagamenti_da_aggiungere_agee.keys():
                matching_name = st.session_state.pagamenti_da_aggiungere_agee[numero]
                
                ## Non permette doppio assegnamento di pagamenti a ordini
                if matching_name != self.name:
                    st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")



class ModifyOrderSelector:

    def __init__(self, name, name_df, PAYMENTS, importo_pagato, selected_rows, brand_locations, columns_to_show):
        self.name = name 
        self.name_df = name_df
        self.PAYMENTS = PAYMENTS
        self.importo_pagato = importo_pagato
        self.selected_rows = selected_rows
        self.brand_locations = brand_locations
        self.colums_to_show = columns_to_show
        

    def display_multiselect(self):
        # Dropdown to select which columns to edit (multi-select)
        return st.multiselect(
            "Selezionare le colonne da modificare:", 
            self.colums_to_show, 
            key=f"multiselect_{self.name}")

    def editing_form(self, columns_to_edit):
        # Create a form for editing the selected columns
        # Handles each case of selected columns
        # Handles the update of the order with the new values

        with st.form(f"edit_row_form_{self.name}"):
            st.write("Modifica dell'ordine:", self.name)

            # Create a dictionary to store new values
            new_values = {}

            # Handle each selected column
            for column in columns_to_edit:
                
                if column.startswith('Lineitem'):
                    # For Lineitem columns, show input for each row
                    st.write(f"Modifica {column}:")
                    for idx, row in self.name_df.iterrows():
                        
                        new_value = OrderWidgets.create_lineitem_input(column, self.name, row, idx)
                        if row.original_index not in new_values:
                            new_values[row.original_index] = {
                                'values': {},
                            }
                        new_values[row.original_index]['values'][column] = new_value

                else:
                    current_value = self.name_df[column].values[0]
                    
                    # Special handling for Location field
                    if column == "Location":
                        new_value = OrderWidgets.create_location_input(self.name, current_value, self.brand_locations)
                        

                    elif column == "Payment Method":
                        new_value = OrderWidgets.create_payment_method_input(self.name, current_value, self.PAYMENTS)


                    elif column == "Total":
                        if len(self.selected_rows) == 0:
                            self.importo_pagato = float(self.name_df["Importo Pagato"].values[0])
                        new_value = OrderWidgets.create_total_input(self.name, current_value, self.importo_pagato)


                    else:
                        # For other non-Lineitem columns
                        input_key = f"widget_{column}_{self.name}_0"
                        new_value = st.text_input(
                            f"Valore attuale per {column}: {current_value}",
                            value=str(current_value) if pd.notna(current_value) else "",
                            key=input_key
                        )
                        
                    
                # Apply the same value to all rows for non-Lineitem columns
                # Quindi fa forward dei valori nuovi nelle righe sotto anche
                for _, row in self.name_df.iterrows():
                    if row.original_index not in new_values:
                        new_values[row.original_index] = {
                            'values': {},
                        }
                    new_values[row.original_index]['values'][column] = new_value

            # Add a submit button
            submit = st.form_submit_button("Conferma Modifiche")
        
        return submit, new_values


"""
BLOCCO 5: Gestione Aggiornamenti
"""

class UpdateHandler:
    def __init__(self, name, name_df, new_values, orders_count, columns_to_edit, double_payment_method, brand):
        self.name = name
        self.name_df = name_df
        self.new_values = new_values
        self.orders_count = orders_count
        self.columns_to_edit = columns_to_edit
        self.double_payment_method = double_payment_method
        self._success_processed = False  # New flag to track if success has been processed
        self.brand = brand


    def update_submitted(self, nan, selected_rows, check, importo_pagato, pagamenti):
        can_continue = self._verify_original_order_inconsistencies(nan)
        if can_continue:
            self.addional_sanity_checks_and_updates(selected_rows, check, importo_pagato, pagamenti)


    def _verify_original_order_inconsistencies(self, nan):
        if not self.new_values:
            st.error("Modificare almeno una colonna")
            return False
        
        if "Payment Method" not in self.columns_to_edit:
            if self.double_payment_method:
                st.error("È necessario compilare il campo Payment Method e scegliere un unico metodo di pagamento")
                return False
            if st.session_state.get('cambiare_metodo', False):
                st.error("È necessario compilare il campo Payment Method e cambiare il metodo affinchè coincida con il pagamento scelto")
                return False
        
        # Recupera l'ultima riga e i valori corrispondenti
        row = self.name_df.iloc[-1]
        row_new_values = self.new_values[row.original_index]['values']

        for field in nan:
            if pd.isna(row[field]):
                if not ((field in row_new_values and row_new_values[field].strip()) or 
                        (field == "Paid at" and row_new_values.get("Total") == 0)):
                    
                    st.error(f"Il campo {field} è obbligatorio")
                    return False
        return True
    

    def addional_sanity_checks_and_updates(self, selected_rows, check, importo_pagato, pagamenti):
        name = self.name
        name_df = self.name_df              # never modified
        new_values = self.new_values        # never modified

        if "Total" not in self.columns_to_edit:
            # No total change, proceed with update
            self._update_order()
            return
        
        new_total = float(new_values[list(new_values.keys())[0]]['values']['Total'])
        if len(selected_rows) == 0:                                         # Caso di Qromo in Metodo
            importo_pagato = float(name_df["Importo Pagato"].values[0])

        if check.startswith("VALUTA"):                                      # Caso di valuta diversa (solo Paypal)
            importo_pagato = new_total
            numero_pagamento = name_df["Numero Pagamento"].values[0]
            st.session_state.pagamenti.loc[st.session_state.pagamenti['Numero Pagamento'] == numero_pagamento, 'Lordo'] = importo_pagato
            st.session_state.pagamenti.loc[st.session_state.pagamenti['Numero Pagamento'] == numero_pagamento, 'CHECK'] = "VERO"

        if new_total != importo_pagato:
            st.session_state[f'needs_confirmation_{name}'] = True
            st.session_state[f'new_values_{name}'] = new_values                                  

        else:
            st.session_state[f'needs_confirmation_{name}'] = False
            self._update_order()
            self.handle_multiple_payment_methods(new_total,importo_pagato, pagamenti)


    ## Non funziona come pensava
    def handle_multiple_payment_methods(self, new_total, importo_pagato, pagamenti):
        
        name = self.name
        name_df = self.name_df
        
        # After updating, check for payment method split if needed
        if "Payment Method" in self.columns_to_edit:
            original_total = float(name_df["Total"].values[0])
            original_payment_method = name_df["Payment Method"].values[0]
            
            ## TODO: E nel caso di Gift Card??
            ## TODO: Inutile controllare "new_total == importo_pagato" siamo già in questa condizione
            if (new_total == importo_pagato and 
                new_total != original_total and 
                "+" in original_payment_method and 
                "Gift Card" not in original_payment_method):
                
                payment_key = f"Payment Method_{name}_0"
                ## TODO: Potenzialmente qua non entra mai -- Payment Method_{name}_0 non è mai settata altrove
                if payment_key in st.session_state:
                    new_payment_method = st.session_state[payment_key]
                    
                    ## TODO: E se contiene altri pagamenti???
                    if new_payment_method and "+" not in new_payment_method:
                        ## TODO: E se la differenza è negativa???
                        difference = original_total - new_total
                        st.session_state[f'needs_aggiungi_check_{name}'] = True
                        st.session_state[f'additional_values_add_{name}'] = {
                            'difference': difference,
                            'numero': name_df["Numero Pagamento"].values[0],
                            'old_payment_method': original_payment_method
                        }

    def _update_order(self):
        """Aggiorna ordine"""
        updated_df, _ = update_df(st.session_state.processed_data, self.new_values, self.name)
        st.session_state.processed_data = updated_df
        st.session_state.saved_updates.add(self.name)
        self.orders_count += 1
        st.session_state[f'success_{self.name}'] = True

        auto_save_on_change()


    def needs_double_check_lil(self, pagamenti, last_index_lil):
        name = self.name

        diff_values = st.session_state[f'additional_values_add_{name}']['difference']
        old_payment_method = st.session_state[f'additional_values_add_{name}']['old_payment_method']
        numero_pagamento = st.session_state[f'additional_values_add_{name}']['numero']

        if "Cash" in old_payment_method:
            st.warning(f"Mancano {diff_values:.2f} euro per quest'ordine. Aggiungere una riga in cui {diff_values:.2f} euro sono stati pagati con Cash? Altrimenti saltare questo step e andare avanti.")

            with st.form(f"add_row_cash_{name}"): 
                # Submit button after all other form elements
                confirm_submit = st.form_submit_button("Aggiungere")
                
                if confirm_submit:
                    new_result = add_row(st.session_state.processed_data, [diff_values], ["Cash"], name, last_index_lil)
                    st.session_state.processed_data = new_result
                    st.session_state.saved_updates.add(name)
                    last_index_lil += 1

                    st.session_state[f'success_{name}'] = True
                    st.session_state[f'success_aggiunto_{name}'] = True
        
        else:
            payments_used = list(map(str.strip, old_payment_method.split('+')))
            st.warning(f"Mancano {diff_values:.2f}€ per quest'ordine: aggiungere altri pagamenti? Scegliere tra i seguenti, altrimenti saltare questo step e andare avanti.")
            pagamenti_to_show = pagamenti[(pagamenti['CHECK'] != "VERO") 
                                        & (pagamenti["Importo Pagato"] <= diff_values) 
                                        & (pagamenti["Metodo"].isin(payments_used))
                                        & (pagamenti["Numero Pagamento"] != numero_pagamento)]
            pagamenti_to_show = pagamenti_to_show.sort_values(by = "Importo Pagato", ascending = False)
            
            ## TODO: Checkbox simile a quella di Qromo si può gestire con una funzione?
            ## TODO: Mostrare metodo di pagamento (Qromo / Satispay tra parentesi accanto al pagamento da selezionare)
            if not pagamenti_to_show.empty:
                st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                selected_rows = []
                importi_pagati = []
                metodi = []

                for index, row in pagamenti_to_show.iterrows():
                    unique_key = f"widget_add_pagamenti_{name}_{index}"
                    if st.checkbox(f"{row['Importo Pagato']}€ pagati alle {row['Data']} con {row['Metodo']}", key=unique_key):
                        selected_rows.append(row)
                        importi_pagati.append(row["Importo Pagato"])
                        st.session_state.numeri_pagamenti.append(row["Numero Pagamento"])
                        if row["Metodo"] not in metodi:
                            metodi.append(row["Metodo"]) 

                        st.session_state.metodo_pagamento = metodi
                        # proceed = True

                # Handle selected payments
                if len(selected_rows) > 0:
                    # Check for already assigned payments
                    for numero in st.session_state.numeri_pagamenti:                                    
                        if numero not in st.session_state.pagamenti_da_aggiungere_lil.keys():
                            st.session_state.pagamenti_da_aggiungere_lil[numero] = name
                        else:
                            matching_name = st.session_state.pagamenti_da_aggiungere_lil[numero]
                            if matching_name != name:
                                st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")

                    # Display selected payments info
                    importo_pagato = sum(importi_pagati)
                    # st.write("Hai selezionato:")
                    # selected_df = pd.DataFrame(selected_rows)
                    # st.write(selected_df[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]])

                    with st.form(f"add_row_other_{name}"): 
                        # Submit button after all other form elements
                        confirm_submit = st.form_submit_button("Aggiungere")
                        
                        if confirm_submit:
                            new_result = add_row(st.session_state.processed_data, importi_pagati, st.session_state.metodo_pagamento, name, last_index_lil)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            last_index_lil += 1


                            st.session_state[f'success_{name}'] = True
                            st.session_state[f'success_aggiunto_{name}'] = True

                            st.session_state.metodo_pagamento = None
                            selected_rows = []
        
    def needs_double_check_agee(self, pagamenti, last_index_agee):
        name = self.name

        diff_values = st.session_state[f'additional_values_add_{name}']['difference']
        old_payment_method = st.session_state[f'additional_values_add_{name}']['old_payment_method']
        numero_pagamento = st.session_state[f'additional_values_add_{name}']['numero']

        if "Cash" in old_payment_method:
            st.warning(f"Mancano {diff_values:.2f} euro per quest'ordine. Aggiungere una riga in cui {diff_values:.2f} euro sono stati pagati con Cash? Altrimenti saltare questo step e andare avanti.")

            with st.form(f"add_row_cash_{name}"): 
                # Submit button after all other form elements
                confirm_submit = st.form_submit_button("Aggiungere")
                
                if confirm_submit:
                    new_result = add_row(st.session_state.processed_data, [diff_values], ["Cash"], name, last_index_agee)
                    st.session_state.processed_data = new_result
                    st.session_state.saved_updates.add(name)
                    last_index_agee += 1

                    st.session_state[f'success_{name}'] = True
                    st.session_state[f'success_aggiunto_{name}'] = True
        
        else:
            payments_used = list(map(str.strip, old_payment_method.split('+')))
            st.warning(f"Mancano {diff_values:.2f}€ per quest'ordine: aggiungere altri pagamenti? Scegliere tra i seguenti, altrimenti saltare questo step e andare avanti.")
            pagamenti_to_show = pagamenti[(pagamenti['CHECK'] != "VERO") 
                                        & (pagamenti["Importo Pagato"] <= diff_values) 
                                        & (pagamenti["Metodo"].isin(payments_used))
                                        & (pagamenti["Numero Pagamento"] != numero_pagamento)]
            pagamenti_to_show = pagamenti_to_show.sort_values(by = "Importo Pagato", ascending = False)
            
            ## TODO: Checkbox simile a quella di Qromo si può gestire con una funzione?
            ## TODO: Mostrare metodo di pagamento (Qromo / Satispay tra parentesi accanto al pagamento da selezionare)
            if not pagamenti_to_show.empty:
                st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                selected_rows = []
                importi_pagati = []
                metodi = []

                for index, row in pagamenti_to_show.iterrows():
                    unique_key = f"widget_add_pagamenti_{name}_{index}"
                    if st.checkbox(f"{row['Importo Pagato']}€ pagati alle {row['Data']} con {row['Metodo']}", key=unique_key):
                        selected_rows.append(row)
                        importi_pagati.append(row["Importo Pagato"])
                        st.session_state.numeri_pagamenti.append(row["Numero Pagamento"])
                        if row["Metodo"] not in metodi:
                            metodi.append(row["Metodo"]) 

                        st.session_state.metodo_pagamento = metodi
                        # proceed = True

                # Handle selected payments
                if len(selected_rows) > 0:
                    # Check for already assigned payments
                    for numero in st.session_state.numeri_pagamenti:                                    
                        if numero not in st.session_state.pagamenti_da_aggiungere_agee.keys():
                            st.session_state.pagamenti_da_aggiungere_agee[numero] = name
                        else:
                            matching_name = st.session_state.pagamenti_da_aggiungere_agee[numero]
                            if matching_name != name:
                                st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")

                    # Display selected payments info
                    importo_pagato = sum(importi_pagati)
                    # st.write("Hai selezionato:")
                    # selected_df = pd.DataFrame(selected_rows)
                    # st.write(selected_df[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]])

                    with st.form(f"add_row_other_{name}"): 
                        # Submit button after all other form elements
                        confirm_submit = st.form_submit_button("Aggiungere")
                        
                        if confirm_submit:
                            new_result = add_row(st.session_state.processed_data, importi_pagati, st.session_state.metodo_pagamento, name, last_index_agee)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            last_index_agee += 1


                            st.session_state[f'success_{name}'] = True
                            st.session_state[f'success_aggiunto_{name}'] = True

                            st.session_state.metodo_pagamento = None
                            selected_rows = []    




    def needs_confirmation(self):
        st.warning("Il totale inserito non corrisponde all'importo effettivamente pagato. Salvare comunque le modifiche?")
        with st.form(f"confirm_form_{self.name}"):
            confirm_submit = st.form_submit_button("Salvare le modifiche")         
            if confirm_submit:
                st.session_state[f'needs_confirmation_{self.name}'] = False
                self._update_order()


    def show_success_lil(self):
        st.success("Modifiche salvate con successo!")
        
        for n in st.session_state.numeri_pagamenti:
            if n not in st.session_state.pagamenti_da_aggiungere_lil.keys():
                st.session_state.pagamenti_da_aggiungere_lil[n] = self.name
    
    def show_success_agee(self):
        st.success("Modifiche salvate con successo!")
        
        for n in st.session_state.numeri_pagamenti:
            if n not in st.session_state.pagamenti_da_aggiungere_agee.keys():
                st.session_state.pagamenti_da_aggiungere_agee[n] = self.name


    def double_check_success_lil(self):
        st.success("Aggiunto con successo!")
        for n in st.session_state.numeri_pagamenti:
            if n not in st.session_state.pagamenti_da_aggiungere_lil.keys():
                st.session_state.pagamenti_da_aggiungere_lil[n] = self.name

    
    def double_check_success_agee(self):
        st.success("Aggiunto con successo!")
        for n in st.session_state.numeri_pagamenti:
            if n not in st.session_state.pagamenti_da_aggiungere_agee.keys():
                st.session_state.pagamenti_da_aggiungere_agee[n] = self.name
    
    def get_orders_count(self):
        return self.orders_count