##FILE DI INTERFACCIA STREAMLIT

import streamlit as st
import pandas as pd
import numpy as np
import pickle

# Your original imports should work now
from model.scripts.call_streamlit import run, update_df, check_files, missing_fields, add_row, aggiungi_pagamenti, generate_excel
from model.utils.exceptions import DateMismatchError
from UI.state_manager import SessionStateManager

def auto_save_on_change():
    """
    Salva automaticamente lo stato quando viene chiamata
    """
    state_manager = SessionStateManager()
    state_manager.save_state()

def check_all_updates_saved(orders_name, payments_name = None):
   
    order_names = set(orders_name)
    
    if payments_name:
        payment_indices = set(payments_name)
        all_required_updates = payment_indices.union(order_names)
    else:
        all_required_updates = order_names
    all_updates_completed = all_required_updates.issubset(st.session_state.saved_updates)
    
    if not all_updates_completed:
        missing_updates = all_required_updates - st.session_state.saved_updates
        st.warning(f"Mancano ancora {len(missing_updates)} elementi da controllare.")
    
    return all_updates_completed

def get_nomi(df, nome_ordine):
    if nome_ordine in df["Name"].unique():
        return True, df[df["Name"] == nome_ordine]["Total"].values[0]
    else:
        return False, 0

st.set_page_config(layout="wide")

COLUMNS_TO_SHOW = ['Name', "Total", 'Shipping', 'Discount Code', 'Discount Amount', 'Paid at', 'Payment Method', 'Email', 'Financial Status', 'Currency', 
                   'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price', "Lineitem sku", "Shipping Country", 'Refunded Amount', 'Outstanding Balance', 'Location']   

PAYMENTS = ["Bonifico", "PayPal Express Checkout", "Qromo", "Satispay", "Scalapay", "Shopify Payments", "Gift Card", "Cash"]      

EXCLUDE_STRINGS = ["Luxury Pack", "Engraving", "E-gift", "Repair", "Whatever Tote", "Piercing Party", "LIL Bag"]

# Initialize session state variables
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None
if 'pagamenti' not in st.session_state:
    st.session_state['pagamenti'] = None
if 'files_processed' not in st.session_state:
    st.session_state['files_processed'] = False
if 'excel_generated' not in st.session_state:
    st.session_state['excel_generated'] = False
if 'saved_updates' not in st.session_state:
    st.session_state.saved_updates = set()
if 'metodo_pagamento' not in st.session_state:
    st.session_state.metodo_pagamento = None
if 'pagamenti_da_aggiungere_lil' not in st.session_state:
    st.session_state.pagamenti_da_aggiungere_lil = {}
if 'pagamenti_da_aggiungere_agee' not in st.session_state:
    st.session_state.pagamenti_da_aggiungere_agee = {}


############ INPUT PAGE ###############

# Title of the page
st.title("Check di Pagamenti LIL Milan e AGEE")

# Create a container
upload_container = st.container()

# Wrap all the code inside the container
with upload_container:

    # Section for uploading order files
    st.subheader("Caricare almeno un file di ordini")
    order_files = {
        "Ordini LIL": {
            "file": st.file_uploader("Caricare file Ordini LIL", type=["csv"], key="ordini_lil"),
            "include": st.checkbox("File da includere", value=True, key="ordini_lil_include"),
        },
    }
    st.markdown("---")

    order_files["Ordini AGEE"] = {
        "file": st.file_uploader("Caricare file Ordini AGEE", type=["csv"], key="ordini_agee"),
        "include": st.checkbox("File da includere", value=True, key="ordini_agee_include"),
    }
    st.markdown("---")

    # Section for uploading payment files
    st.subheader("Caricare almeno un file di pagamenti")

    payment_files = {
        "Bonifici": {
            "file": st.file_uploader("Caricare file per Bonifici", type=["xlsx"], key="bonifici"),
            "include": st.checkbox("File da includere", value=True, key="bonifici_include"),
        },
    }
    st.markdown("---")

    payment_files["Paypal"] = {
        "file": st.file_uploader("Caricare file per Paypal", type=["csv"], key="paypal"),
        "include": st.checkbox("File da includere", value=True, key="paypal_include"),
    }
    st.markdown("---")


    payment_files["Qromo"] = {
        "file": st.file_uploader("Caricare file per Qromo", type=["csv"], key="qromo"),
        "include": st.checkbox("File da includere", value=True, key="qromo_include"),
    }
    st.markdown("---")

    payment_files["Satispay"] = {
        "file": st.file_uploader("Caricare file per Satispay", type=["csv"], key="satispay"),
        "include": st.checkbox("File da includere", value=True, key="satispay_include"),
    }
    st.markdown("---")

    payment_files["Scalapay"] = {
        "file": st.file_uploader("Caricare file per Scalapay", type=["csv"], key="scalapay"),
        "include": st.checkbox("File da includere", value=True, key="scalapay_include"),
    }
    st.markdown("---")

    payment_files["Shopify AGEE"] = {
        "file": st.file_uploader("Caricare file per Shopify AGEE", type=["csv"], key="shopify_agee"),
        "include": st.checkbox("File da includere", value=True, key="shopify_agee_include"),
    }
    st.markdown("---")

    payment_files["Shopify LIL"] = {
        "file": st.file_uploader("Caricare file per Shopify LIL", type=["csv"], key="shopify_lil"),
        "include": st.checkbox("File da includere", value=True, key="shopify_lil_include"),
    }
    st.markdown("---")

    # Input for month and year
    month = st.number_input("Inserire il mese di interesse (1-12):", min_value=1, max_value=12, step=1, value=11)  # Default to October
    year = st.number_input("Inserire l'anno di interesse:", min_value=2010, max_value=2100, step=1, value=2024)  # Default to 2024

    # Warning logic and continuation option
    missing_files = []

    # Check if at least one file is uploaded for "orders_files" and "payment_files" categories
    at_least_one_order = any(content["include"] and content["file"] for content in order_files.values())
    at_least_one_payment = any(content["include"] and content["file"] for content in payment_files.values())

    ## definiti missining, quelli flaggati ma non inseriti -- TODO: forse rendere più chiara la variabile ma va bene così##
    # Identify missing files in selected categories
    for label, content in {**order_files, **payment_files}.items():
        if content["include"] and not content["file"]:
            missing_files.append(label)

    # Validation messages
    proceed_orders = True
    if not at_least_one_order:
        st.error("Per favore, caricare almeno un file di ordini.")
        proceed_orders = False
    if not at_least_one_payment:
        st.error("Per favore, caricare almeno un file di pagamenti.")
        proceed_orders = False

    if missing_files:
        st.warning(f"Attenzione! Mancano i file: {', '.join(missing_files)}")
        proceed_orders = False
        

    col1, col2 = st.columns(2)
    with col1:
        process_button = st.button("Processare i file", key="process_files_button", 
                                disabled= st.session_state.get("files_processed", False) or not proceed_orders)  # Disabilitato se non c'è uno stato valido
    with col2:
        state_manager = SessionStateManager()
        last_state = state_manager.load_last_state()
        st.write(last_state)
        restore_button = st.button("Ripristina stato precedente", 
                                disabled=last_state is None)  # Disabilitato se non c'è uno stato valido
        if restore_button and last_state is not None:
            for key in last_state:
                st.session_state[key] = last_state[key]
            st.rerun()


    # process_button = st.button("Processare i file", key="process_files_button", disabled=st.session_state.get("files_processed", False))

    # Starts matching orders and payments and elaborates the remaining data to be controlled.
    if process_button:
        uploaded_orders_files = {name: content["file"] for name, content in order_files.items() if content["file"] is not None and content["include"] is True}
        uploaded_payment_files = {name: content["file"] for name, content in payment_files.items() if content["file"] is not None and content["include"] is True}
        try:
            with st.spinner('Elaborazione dei file in corso...'):
                # Check each uploaded and included order file
                # Checks if data of the year and month inserted are present inside the files otherwise raise error. 
                for name, f_file in uploaded_orders_files.items():
                    check_files(order_files, name, month, year)    
                for name, f_file in uploaded_payment_files.items():
                    check_files(payment_files, name, month, year)
                
                # Run the matching between orders and payments
                result_df, pagamenti_df = run(order_files, payment_files, month, year)
                
                # Save the resulting data in the session state
                st.session_state.processed_data = result_df
                st.session_state.pagamenti = pagamenti_df
                # st.session_state.files_processed = True  # Set the flag to disable the button
        except DateMismatchError as e:
            st.error(f"❌ {e.message}")
            if e.details:
                st.info(e.details)

############### FINE PAGINA DI INPUT ###############

if st.session_state.processed_data is not None and st.session_state.pagamenti is not None:  
    ###TODO: -- Funziona??-- ###
    upload_container.empty()  
    
    st.session_state.processed_data['original_index'] = st.session_state.processed_data.index.astype(int)
    st.session_state.pagamenti['original_index'] = st.session_state.pagamenti.index.astype(int)

    # Display LIL Milan results that need checking
    #####################################################################
    ## TODO: Da qui in giù fino a FINE da far fare tramite model
   
    df_rilevante = st.session_state.processed_data[(st.session_state.processed_data["CHECK"] != "ESCLUSO")].copy()
    
    # TODO: forse li ordinerei per tipologia
    # TODO: Sortiamo ogni volta che ricarichiamo la pagina?
    df_rilevante_sorted = df_rilevante.sort_values(by=["CHECK", "Name"])
  
    names_count_lil = len(df_rilevante[df_rilevante["Brand"] == "Ordini LIL"]["Name"].unique())
    names_count_agee = len(df_rilevante[df_rilevante["Brand"] == "Ordini AGEE"]["Name"].unique())

    lil_df = df_rilevante_sorted[(df_rilevante_sorted["CHECK"] != "VERO") & (df_rilevante_sorted["Brand"] == "Ordini LIL")].copy()
    lil_df = lil_df.drop_duplicates(subset=COLUMNS_TO_SHOW)
    #TODO: Lo usa per fare append al df di lil capire bene cosa fa e capire se si può evitare sta porcata.
    last_index_lil = lil_df['original_index'].max()
    name_lil = lil_df["Name"].unique()

    agee_df = df_rilevante_sorted[(df_rilevante_sorted["CHECK"] != "VERO") & (df_rilevante_sorted["Brand"] == "Ordini AGEE")].copy()
    agee_df = agee_df.drop_duplicates(subset=COLUMNS_TO_SHOW)
    last_index_agee = agee_df['original_index'].max()
    name_agee = agee_df["Name"].unique()

    # Potenzialmente salta per questo -- uncomment in caso
    # orders_name = np.concatenate([name_lil if len(name_lil) > 0 else np.array([]),
    #                             name_agee if len(name_agee) > 0 else np.array([])
    #                             ])

    ## TODO: Conta ogni volta che viene modificato un ordina con "conferma modifiche" sia di lil che di agee
    ## TODO: Lo usa come controllo per vedere se tutti gli ordini sono stati modificati e per "sbloccare" la parte pagamenti
    orders_count = 0
    ### TODO: FINE
    ####################################################################################
    #LIL MILAN

    # ///////////// CHUNK 1 //////////////
    # INIZIALIZZA IL DF E STAMPA GLI ORDINI DA CONTROLLARE
    #      
    st.session_state.names_check_lil = None

    if len(lil_df) > 0:
        st.write("")
        st.subheader("Ordini da controllare LIL Milan")

        # Evita di fare il sorting e il filtering ad ogni ricarica
        # Se non c'è in variabile di stato ordina e calcola gli order id da coqntrollare altrimenti li carica da variabile di stato
        if st.session_state.names_check_lil is None:
            lil_df_sorted = lil_df.sort_values(by=["CHECK", "Name"])
            names_check = lil_df_sorted[lil_df_sorted['Name'].notna()]['Name'].unique()
            st.session_state.names_check_lil = names_check
        else:
            names_check = st.session_state.names_check_lil
        
        st.write(f"{len(names_check)} ordini su {names_count_lil}")
        pagamenti =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] != "VERO")].copy() 

        # ///////////// FINE CHUNK 1 //////////////
        # ///////////// CHUNK 2 //////////////
        # ITERA SU TUTTI GLI ORDINI DA CONTROLLARE ESTRAPOLA 
        for name in names_check:
            with st.container():
                st.markdown("---")  # Visual separator
                st.subheader(f"Ordine: {name}")

                name_df = lil_df[lil_df['Name'] == name]
                check = name_df["CHECK"].values[0]
                metodo = name_df["Payment Method"].values[0]
                st.session_state.numeri_pagamenti = []              # Serve a salvare i pagamenti associati all'ordine | Resettiamo ad ogni nuovo ordine
               
                # ///////////// FINE CHUNK 2 //////////////
                # ///////////// CHUNK 3 //////////////
                # GESTISCE I VARI TIPI DI SITUAZIONI CHECK (FALSO, NON TROVATO, LONDON, VALUTA) E MOSTRA A SCHERMO IL SUGGERIMENTO DEL CASO
                ## Pagamento con Qromo (o Satispay Offline) o totale non corrispondente a quanto incassato
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

                # ///////////// FINE CHUNK 3 //////////////
                # ///////////// CHUNK 4 //////////////

                # MOSTRA A SCHERMO IL DATAFRAME CON I DATI DELL'ORDINE
                st.dataframe(name_df[COLUMNS_TO_SHOW], use_container_width=True)

                # ///////////// FINE CHUNK 4 //////////////
                # ///////////// CHUNK 5 //////////////
                # CONTROLLA CHE L'ORDINE ABBIA TUTTI I CAMPI NECESSARI CON VALORI E MOSTRA I WARNING IN CASO DI MANCANZA
                # INOLTRE CONTROLLA SE CI SONO METODI DI PAGAMENTO MULTIPLI E MOSTRA I WARNING IN CASO DI DOPPIO/TRIPLO PAGAMENTO

                ## TODO: Salvare in session state il risultato della funzione
                # Check for required fields before showing the form
                nan, double_payment_method = missing_fields(lil_df, name, EXCLUDE_STRINGS)
                # missing_fields_str = [str(field) for field in nan]

                cambiare_metodo = False

                ## Shows a warning for each missing field            
                if nan:
                    # if check == "FALSO":
                    base_warning = f"Attenzione: I seguenti campi mancano ed è necessario inserirli per le analisi: {', '.join(nan)}"
                    st.warning(base_warning)

                    # elif check == "NON TROVATO":
                    #     base_warning = f"Attenzione: I seguenti campi mancano e nel caso in cui l'ordine sia da includere, è necessario inserirli per le analisi: {', '.join(nan)}"
                    #     st.warning(base_warning)

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


                ## TODO: Capire questa scelta di gestione del metodo di pagamento multiplo (non solo doppio)
                ## Shows a warning if there are multiple payment methods and asks to choose one
                if double_payment_method:
                    base_warning = f"Attenzione: Payment Method va modificato, e va scelto un unico metodo di pagamento effettivamente usato"
                    st.warning(base_warning)

                # ///////////// FINE CHUNK 5 //////////////
                # ///////////// CHUNK 6 //////////////
                # GESTISCE IL CASO DI ORDINI PAGATI CON QROMO (O SATISPAY OFFLINE) (SINGOLI O MULTIPLI CHE SIANO)

                ## Da i vari warnings e fa scegliere i pagamenti da associare all'ordine nel caso di Qromo (o Satispay) 
                # e poi fa procedere con la modifica delle colonne
                if "Qromo" in metodo: # or "Satispay" in metodo:
                    # Get possibili_pagamenti more cleanly
                    # possibili_pagamenti = name_df['possibili_pagamenti'].iloc[0]
                    # possibili_pagamenti = [] if possibili_pagamenti is None or (isinstance(possibili_pagamenti, float) and np.isnan(possibili_pagamenti)) else possibili_pagamenti

                    # # # Filter pagamenti DataFrame
                    # filtered_rows_same_date = pagamenti[pagamenti['Numero Pagamento'].isin(possibili_pagamenti)]

                    ## TODO: FUNZIONEEEEE STARTTTTTTTTTTTTT
                    ## Estrae i pagamenti con importo <= totale dell'ordine dalla lista di pagamenti
                    totale = name_df["Total"].values[0]
                    paid_at = str(name_df["Paid at"].values[0])[:10]
                    # Combine conditions explicitly
                    filtered_rows = pagamenti[(pagamenti["Importo Pagato"] <= totale)] 

                    ## TODO: Cosa succede nel caso in cui si pagano + ordini con un pagamento? Raro ma possibile, cosa facciamo?
                    
                    # Fix the condition using any() for Series comparison
                    ## Seleziona tutti i pagamenti di Qromo o Satispay con importo <= totale dell'ordine
                    satispay_mask = (filtered_rows["Metodo"] == "Satispay") & (filtered_rows["Numero Pagamento"] == "0")
                    qromo_mask = filtered_rows["Metodo"] == "Qromo"
                    filtered_rows = filtered_rows[satispay_mask | qromo_mask].sort_values(by="Data", ascending = False)
                    ### TODO: END
                    
                    ## Mostra nel caso di Qromo la lista con checkbox di pagamenti tra cui scegliere
                    ## TODO: Mostrare metodo di pagamento (Qromo / Satispay tra parentesi accanto al pagamento da selezionare)

                    if not filtered_rows.empty:
                        st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                        selected_rows = []
                        importi_pagati = []
                        
                        # Mostra e fa selezionare i pagamenti corrispondenti all'ordine dalla lista di righe filtrateù
                        # Mette in selected_rows i pagamenti selezionati e in importi_pagati gli importi pagati
                        for index, row in filtered_rows.iterrows():
                            unique_key = f"{name}_{index}"
                            ## Mette in bold i pagamenti fatti nello stesso giorno dell'ordine
                            if str(row["Data"]).startswith(paid_at):
                                # Format the label with bold text
                                label = f"**{row['Importo Pagato']}€ pagati alle {row['Data']}**"
                            else:
                                # Regular label
                                label = f"{row['Importo Pagato']}€ pagati alle {row['Data']}"
                            if st.checkbox(label, key=unique_key):
                                selected_rows.append(row)
                                importi_pagati.append(row["Importo Pagato"])
                                st.session_state.numeri_pagamenti.append(row["Numero Pagamento"])

                                st.session_state.metodo_pagamento = row["Metodo"]
                                # proceed = True
                        
                        # TODO: Da gestire con una funzione invece che con lo stato?
                        # Handle selected payments and verifies double assignments in case it warns the user 
                        # otherwise updates the list of payments to be added
                        # Suggest the user to change the total if the sum of the selected payments is different from the total
                        if len(selected_rows) > 0:
                            # Check for already assigned payments
                            for numero in st.session_state.numeri_pagamenti:
                                if numero in st.session_state.pagamenti_da_aggiungere_lil.keys():
                                    matching_name = st.session_state.pagamenti_da_aggiungere_lil[numero]
                                    
                                    ## TODO: Non permette doppio assegnamento di pagamenti a ordini
                                    if matching_name != name:
                                        st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")
                                else:
                                    # Assign the payment to pagamenti_da_aggiungere if it hasn't been assigned
                                    st.session_state.pagamenti_da_aggiungere_lil[numero] = name
                            
                            # Display selected payments info
                            importo_pagato = sum(importi_pagati)
                            # st.write("Hai selezionato:")
                            # selected_df = pd.DataFrame(selected_rows)
                            # st.write(selected_df[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]])
                            st.write(f"Cambia il **Total** con **{importo_pagato:.2f}**")
                           
                            if metodo.replace("Gift Card", "").replace("+", "").replace(" ", "") != st.session_state.metodo_pagamento:  # Added .iloc[0]
                                st.write(f"Cambia il **Payment Method** con **{st.session_state.metodo_pagamento}**")
                                cambiare_metodo = True

                        ## Se la selezione è vuota suggerisce di cambiare il total a 0
                        else:
                            st.write("Non hai selezionato alcun pagamento.")
                            st.write("Cambia il **Total** con **0**")
                            importo_pagato = 0.0
                            selected_rows.append(0)

                    ## Se non ci sono pagamenti non assegnati in Qromo, lascia vuote le variabili e non assegna alcun pagamento all'ordine
                    else:
                        selected_rows = []
                        st.session_state.numeri_pagamenti = [] #.append(name_df["Numero Pagamento"].values[0])
                        st.session_state.metodo_pagamento = None

                # ///////////// FINE CHUNK 6 //////////////
                # ///////////// CHUNK 7 //////////////

                ## Se non è Qromo (o Satispay Offline) il metodo di pagamento..
                # Aggiungiamo alla lista numeri_pagamenti (SV) il numero pagamento di quel pagamento (dal df degli ordini però)
                else:
                    selected_rows = []
                    st.session_state.numeri_pagamenti.append(name_df["Numero Pagamento"].values[0])
                    st.session_state.metodo_pagamento = None

                # ///////////// FINE CHUNK 7 //////////////
                # ///////////// CHUNK 8 //////////////
                # CREA GLI ELEMENTI PER LA MODIFICA DEI CAMPI E I RISPETTIVI SPAZI DI INSERIMENTO A SECONDA DELLA TIPOLOGIA

                # Dropdown to select which columns to edit (multi-select)
                columns_to_edit = st.multiselect("Selezionare le colonne da modificare:", COLUMNS_TO_SHOW, key=f"multiselect_{name}")

                # Create a form for editing the selected columns
                # Handles each case of selected columns
                # Handles the update of the order with the new values
                with st.form(f"edit_row_form_{name}"):
                    st.write("Modifica dell'ordine:", name)

                    # Create a dictionary to store new values
                    new_values = {}
                    all_required_fields_filled = True

                    # Handle each selected column
                    for column in columns_to_edit:
                        
                        ## TODO: Estrarre funzione generale per gestire input
                        if column.startswith('Lineitem'):
                            # For Lineitem columns, show input for each row
                            st.write(f"Modifica {column}:")
                            if column == "Lineitem quantity":
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    new_value  = st.number_input(f"Valore attuale per {column} - {row['Lineitem name']}: {current_value}",
                                                value=current_value if pd.notna(current_value) else 0,
                                                step = 1.0, 
                                                format="%.0f",  # Format to display an int
                                                key=input_key)
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value

                            elif column == "Lineitem price":
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    new_value  = st.number_input(f"Valore attuale per {column} - {row['Lineitem name']}: {current_value}",
                                                value=current_value if pd.notna(current_value) else 0,
                                                step = None, 
                                                format="%.2f",  # Format to display an int
                                                key=input_key)
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value

                            elif column == "Lineitem name": 
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    st.text_input(f"Valore attuale per {column} - {row['Lineitem sku']}: {current_value}",
                                        value=str(current_value),
                                        key=input_key
                                    )
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value
                            
                            elif column == "Lineitem sku": 
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    st.text_input(
                                        f'Valore attuale per {column} - {row["Lineitem name"]}: {current_value}' if not pd.isna(current_value) else f'Inserire il valore di {column} per {row["Lineitem name"]}:',
                                        value=str(current_value) if not pd.isna(current_value) else "015790000000",
                                        key=input_key
                                    )
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value

                
                            else: 
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    st.text_input(f"Valore attuale per {column} - {row['Lineitem name']}: {current_value}",
                                        value=str(current_value),
                                        key=input_key
                                    )
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value

                        else:
                            # Special handling for Location field
                            if column == "Location":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=["Firgun House", "LIL House", "LIL House London"],
                                    index=0 if pd.isna(current_value) else 
                                        ["Firgun House", "LIL House", "LIL House London"].index(current_value),
                                    key=input_key
                                )
                                

                            elif column == "Payment Method":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                
                                # Split the current payment method on '+' and clean the options
                                # if pd.notna(current_value):
                                #     if st.session_state.metodo_pagamento is None:
                                #         payment_options = [opt.strip() for opt in current_value.split('+')] 
                                #     else:
                                #         payment_options = [opt.strip() for opt in current_value.split('+')] + ([st.session_state.metodo_pagamento] 
                                #                                                                                if st.session_state.metodo_pagamento not in [opt.strip() 
                                #                                                                                                                             for opt in current_value.split('+')] else [])
                                # else:
                                #     payment_options = payments
                                    
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=PAYMENTS,
                                    index=0 if pd.isna(current_value) or not PAYMENTS else 0,
                                    key=input_key
                                )
                                

                            elif column == "Total":
                                if len(selected_rows) == 0:
                                    importo_pagato = float(name_df["Importo Pagato"].values[0])
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.number_input(f"Valore attuale per {column}: {current_value}",
                                    value = importo_pagato if pd.notna(importo_pagato) else 0.0,
                                    step = None, 
                                    format="%.2f",  # Format to display the float with 2 decimal places
                                    key=input_key)
                                
                                    
                            else:
                                # For other non-Lineitem columns
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.text_input(
                                    f"Valore attuale per {column}: {current_value}",
                                    value=str(current_value) if pd.notna(current_value) else "",
                                    key=input_key
                                )
                                
                            
                        # Apply the same value to all rows for non-Lineitem columns
                        # Quindi fa forward dei valori nuovi nelle righe sotto anche
                        for _, row in name_df.iterrows():
                            if row.original_index not in new_values:
                                new_values[row.original_index] = {
                                    'values': {},
                                }
                            new_values[row.original_index]['values'][column] = new_value
        

                    # Add a submit button
                    submit = st.form_submit_button(
                        "Conferma Modifiche",
                        disabled=not all_required_fields_filled
                    )

                section_placeholder = st.empty()

                # ///////////// FINE CHUNK 8 //////////////
                # ///////////// CHUNK 9 //////////////
                # GESTISCE LE MODIFICHE FATTE E FA I CONTROLLI NECESSARI CHE CI SIA TUTTO PER PROSEGUIRE E AGGIORNARE IL DF POI AGGIORNA IL DF

                ## Controlla se ci sono pagamenti doppi e non permette di procedere se non sono stati selezionati pagamenti
                ## Se cambiare_metodo è True, controlla che il metodo di pagamento sia stato cambiato
                ## In sostanza chiede di aggiornare Payment Method nelle due condizioni sopra segnate
                ## Verifica che tutti i campi obbligatori che contenevano valori nulli siano stati compilati con dei nuovi valori
                ## Gestisce tutte le verifiche derivanti dalle modifiche fatte e fa gli aggiornamenti di DF e di stato
                ## In caso di discrepanza tra totale atteso e inserito chiede conferma
                ## In caso di rimanenze di totale pagate con cash propone l'aggiunta di un riga con il rimanente in cash e chiede conferma
                ## In caso di rimanenze di totale pagate con altro metodo di pagamento mostra checkbox coi pagamenti e ne fa selezionare altri, può essere ignorato
                ## Aggiorna il DF e le variabili di stato
                with section_placeholder.container():
                    # Store the submission state
                    ## all_required_fields_filled praticamente inutile non è mai false.
                    ## Non c'è una condizione di uscita se questo if è false
                    if submit and all_required_fields_filled:
                        
                        ## Verfica che i nan sono stati modificati e che le colonne da modificare obbligatorie siano state modificate
                        ## TODO: Si può chiamare una funzione per semplicità
                        if double_payment_method and "Payment Method" not in columns_to_edit:
                            st.error("È necessario compilare il campo Payment Method e scegliere un unico metodo di pagamento")
                            all_required_fields_to_continue = False

                        elif cambiare_metodo and "Payment Method" not in columns_to_edit:
                            st.error("È necessario compilare il campo Payment Method e cambiare il metodo affinchè coincida con il pagamento scelto")
                            all_required_fields_to_continue = False
                        
                        ## Se non ci sono problemi con il payment method gestisce i problemi con i campi obbligatori
                        else:
                            row_nan_fields = [field for field in nan if pd.isna(row[field])] 
                            
                            if not row_nan_fields:
                                all_required_fields_to_continue = True
                                    
                            for field in row_nan_fields:
                                if (field in new_values[row.original_index]['values'] and 
                                    new_values[row.original_index]['values'][field].strip()) or (new_values[row.original_index]['values']["Total"] == 0 and field == "Paid at"):
                                    all_required_fields_to_continue = True
                                else:
                                    st.error(f"Il campo {field} è obbligatorio")
                                    all_required_fields_to_continue = False

                            
                        if all_required_fields_to_continue:
                            
                            ## TODO: E' POSSIBILE CHE NON CI SIA? -- NEW_VALUE SEMPRE VERO 
                            # SE ALMENO UNA COLONNA E' STATA MODIFICATA (QUALSIASI)
                            ## TODO: Problema se è Qromo + Paypal con valuta diversa
                            if "Total" in columns_to_edit and new_value:
                                # new_total = float(new_value)
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
                                    # Totals match, proceed with update
                                    new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                                    st.session_state.processed_data = new_result
                                    st.session_state.saved_updates.add(name)
                                    
                                    # After updating, check for payment method split if needed
                                    if "Payment Method" in columns_to_edit:
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

                                    st.session_state[f'success_{name}'] = True
                            else:
                                # No total change, proceed with update
                                new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state[f'success_{name}'] = True

                        ## Salva lo stato corrente in un file di backup
                        #auto_save_on_change()


                    # Show confirmation form if needed
                    if f'needs_confirmation_{name}' in st.session_state and st.session_state[f'needs_confirmation_{name}']:
                        st.warning("Il totale inserito non corrisponde all'importo effettivamente pagato. Salvare comunque le modifiche?")

                        with st.form(f"confirm_form_{name}"):
                            confirm_submit = st.form_submit_button("Salvare le modifiche")
                            
                            if confirm_submit:
                                new_values = st.session_state[f'new_values_{name}']
                                new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state[f'needs_confirmation_{name}'] = False
                                # st.success("Modifiche salvate con successo!")
                                st.session_state[f'success_{name}'] = True
                                
                                ## Salva lo stato corrente in un file di backup
                                #auto_save_on_change()

                    # Show success message if it's in the session state
                    if f'success_{name}' in st.session_state and st.session_state[f'success_{name}']:
                        st.success("Modifiche salvate con successo!")
                        orders_count += 1
                        
                        ## TODO: Non serve sta variabile
                        to_modify = False
                        for n in st.session_state.numeri_pagamenti:
                            if n not in st.session_state.pagamenti_da_aggiungere_lil.keys():
                                st.session_state.pagamenti_da_aggiungere_lil[n] = name

                    if f'needs_aggiungi_check_{name}' in st.session_state and st.session_state[f'needs_aggiungi_check_{name}']:
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

                                    st.session_state[f'needs_aggiungi_check_{name}'] = False
                                    st.session_state[f'success_{name}'] = True
                                    st.session_state[f'success_aggiunto_{name}'] = True
                                    ## Salva lo stato corrente in un file di backup
                                    #auto_save_on_change()
                        
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
                                    unique_key = f"add_pagamenti_{name}_{index}"
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

                                            st.session_state[f'needs_aggiungi_check_{name}'] = False
                                            st.session_state[f'success_{name}'] = True
                                            st.session_state[f'success_aggiunto_{name}'] = True

                                            st.session_state.metodo_pagamento = None
                                            selected_rows = []
                                            ## Salva lo stato corrente in un file di backup
                                            #auto_save_on_change()

                    if f'success_aggiunto_{name}' in st.session_state and st.session_state[f'success_aggiunto_{name}']:
                        st.success("Aggiunto con successo!")
                        for n in st.session_state.numeri_pagamenti:
                            if n not in st.session_state.pagamenti_da_aggiungere_lil.keys():
                                st.session_state.pagamenti_da_aggiungere_lil[n] = name
                        if to_modify:
                            orders_count += 1
                # ///////////// FINE CHUNK 9 //////////////
    
        # ///////////// CHUNK 10 //////////////                    
    else:
        st.subheader("Nessun ordine di LIL Milan deve essere controllato")
    # ///////////// FINE CHUNK 10 //////////////
    ## FINE LIL MILAN ORDERS


    #AGEE
    # Probabilmente identico a Lil fare una funzione unica per replicarlo?
    if len(agee_df) > 0:
        st.write("")
        st.subheader("Ordini da controllare AGEE")

        agee_df_sorted = agee_df.sort_values(by=["CHECK", "Name"])
            
        names_check = agee_df_sorted[agee_df_sorted['Name'].notna()]['Name'].unique()    
        st.write(f"{len(names_check)} ordini su {names_count_agee}")
            
        for name in names_check:
            with st.container():
                st.markdown("---")  # Visual separator
                st.subheader(f"Ordine: {name}")

                name_df = agee_df[agee_df['Name'] == name]
                check = name_df["CHECK"].values[0]
                metodo = name_df["Payment Method"].values[0]
                st.session_state.numeri_pagamenti = []
                #aggiunto dopo
                pagamenti =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] != "VERO")].copy()

                if check == "FALSO":
                    
                    if "Qromo" in metodo:# or "Satispay" in metodo:
                        st.write(f"Non è stato possibile determinare con certezza il pagamento corrispondente all'ordine {name}")

                    else:
                        st.write(f"Il totale non coincide con l'importo effettivamente incassato. Modificare i valori delle colonne opportune.")                        
                        st.write(f"Importo effettivamente incassato: **{name_df['Importo Pagato'].values[0]}**")

                
                elif check == "NON TROVATO":
                    st.write(f"Non è stato trovato un pagamento relativo all'ordine. Modificare i valori delle colonne opportune.")                            
                    st.write(f"Importo effettivamente incassato: **0**")

                #ggiunto dopo
                elif check.startswith("VALUTA"):
                    st.write(f"Il pagamento non è stato fatto in EURO, confermare l'importo effettivamente incassato.")
                    st.write(f"Importo pagato in **{check.split('_')[1]}**: **{name_df['Importo Pagato'].values[0]}**")

                st.dataframe(name_df[COLUMNS_TO_SHOW], use_container_width=True)

                # Check for required fields before showing the form
                nan, double_payment_method = missing_fields(agee_df, name, EXCLUDE_STRINGS)
                # missing_fields_str = [str(field) for field in nan]

                cambiare_metodo = False
                            
                if nan:
                    #cambiato dopo
                    base_warning = f"Attenzione: I seguenti campi mancano ed è necessario inserirli per le analisi: {', '.join(nan)}"
                    st.warning(base_warning)

                    # elif check == "NON TROVATO":
                    #     base_warning = f"Attenzione: I seguenti campi mancano e nel caso in cui l'ordine sia da includere, è necessario inserirli per le analisi: {', '.join(nan)}"
                    #     st.warning(base_warning)

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

                if double_payment_method:
                    base_warning = f"Attenzione: Payment Method va modificato, e va scelto un unico metodo di pagamento effettivamente usato"
                    st.warning(base_warning)

                if "Qromo" in metodo:# or "Satispay" in metodo:
                    #cambiato dopo
                    # Get possibili_pagamenti more cleanly
                    # possibili_pagamenti = name_df['possibili_pagamenti'].iloc[0]
                    # possibili_pagamenti = [] if possibili_pagamenti is None or (isinstance(possibili_pagamenti, float) and np.isnan(possibili_pagamenti)) else possibili_pagamenti

                    # # # Filter pagamenti DataFrame
                    # filtered_rows_same_date = pagamenti[pagamenti['Numero Pagamento'].isin(possibili_pagamenti)]

                    totale = name_df["Total"].values[0]
                    paid_at = str(name_df["Paid at"].values[0])[:10]
                    # Combine conditions explicitly
                    filtered_rows = pagamenti[(pagamenti["Importo Pagato"] <= totale)] 
                    
                    # Fix the condition using any() for Series comparison
                    satispay_mask = (filtered_rows["Metodo"] == "Satispay") & (filtered_rows["Numero Pagamento"] == "0")
                    qromo_mask = filtered_rows["Metodo"] == "Qromo"
                    filtered_rows = filtered_rows[satispay_mask | qromo_mask].sort_values(by="Data", ascending = False)
                    
                    if not filtered_rows.empty:
                        st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                        selected_rows = []
                        importi_pagati = []

                        for index, row in filtered_rows.iterrows():
                            unique_key = f"{name}_{index}"
                            #cambiato dopo
                            if str(row["Data"]).startswith(paid_at):
                                # Format the label with bold text
                                label = f"**{row['Importo Pagato']}€ pagati alle {row['Data']}**"
                            else:
                                # Regular label
                                label = f"{row['Importo Pagato']}€ pagati alle {row['Data']}"
                            if st.checkbox(label, key=unique_key):
                                selected_rows.append(row)
                                importi_pagati.append(row["Importo Pagato"])
                                st.session_state.numeri_pagamenti.append(row["Numero Pagamento"])

                                st.session_state.metodo_pagamento = row["Metodo"]

                                # proceed = True
       
                        # Handle selected payments
                        if len(selected_rows) > 0:
                            # Check for already assigned payments
                            for numero in st.session_state.numeri_pagamenti:
                                if numero in st.session_state.pagamenti_da_aggiungere_agee.keys():
                                    matching_name = st.session_state.pagamenti_da_aggiungere_agee[numero]
                                    if matching_name != name:
                                        st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")
                                else:
                                    if numero in st.session_state.pagamenti_da_aggiungere_lil.keys():
                                        matching_name_lil = st.session_state.pagamenti_da_aggiungere_lil[numero]
                                        st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name_lil} di LIL Milan")
                                    else:
                                        # Assign the payment to pagamenti_da_aggiungere if it hasn't been assigned
                                        st.session_state.pagamenti_da_aggiungere_agee[numero] = name
                            
                            # Display selected payments info
                            importo_pagato = sum(importi_pagati)
                            # st.write("Hai selezionato:")
                            # selected_df = pd.DataFrame(selected_rows)
                            # st.write(selected_df[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]])
                            st.write(f"Cambia il **Total** con **{importo_pagato:.2f}**")
                            
                            if metodo.replace("Gift Card", "").replace("+", "").replace(" ", "") != st.session_state.metodo_pagamento:  # Added .iloc[0]
                                st.write(f"Cambia il **Payment Method** con **{st.session_state.metodo_pagamento}**")
                                cambiare_metodo = True
                        else:
                            st.write("Non hai selezionato alcun pagamento.")
                            st.write("Cambia il **Total** con **0**")
                            importo_pagato = 0.0
                            selected_rows.append(0)
                    else:
                        selected_rows = []
                        st.session_state.numeri_pagamenti = [] #.append(name_df["Numero Pagamento"].values[0])
                        st.session_state.metodo_pagamento = None
                else:
                    selected_rows = []
                    st.session_state.numeri_pagamenti.append(name_df["Numero Pagamento"].values[0])
                    st.session_state.metodo_pagamento = None

                # Dropdown to select which columns to edit (multi-select)
                columns_to_edit = st.multiselect("Selezionare le colonne da modificare:", COLUMNS_TO_SHOW, key=f"multiselect_{name}")

                # Create a form for editing the selected columns
                with st.form(f"edit_row_form_{name}"):
                    st.write("Modifica dell'ordine:", name)

                    # Create a dictionary to store new values
                    new_values = {}
                    all_required_fields_filled = True

                    # Handle each selected column
                    for column in columns_to_edit:

                        if column.startswith('Lineitem'):
                            # For Lineitem columns, show input for each row
                            st.write(f"Modifica {column}:")
                            if column == "Lineitem quantity":
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    new_value  = st.number_input(f"Valore attuale per {column} - {row['Lineitem name']}: {current_value}",
                                                value=current_value if pd.notna(current_value) else 0,
                                                step = 1.0, 
                                                format="%.0f",  # Format to display an int
                                                key=input_key)
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value

                            elif column == "Lineitem price":
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    new_value  = st.number_input(f"Valore attuale per {column} - {row['Lineitem name']}: {current_value}",
                                                value=current_value if pd.notna(current_value) else 0,
                                                step = None, 
                                                format="%.2f",  # Format to display an int
                                                key=input_key)
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value

                            elif column == "Lineitem name": 
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    st.text_input(f"Valore attuale per {column} - {row['Lineitem sku']}: {current_value}",
                                        value=str(current_value),
                                        key=input_key
                                    )
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value
                
                            #aggiunto dopo
                            elif column == "Lineitem sku": 
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    st.text_input(
                                        f'Valore attuale per {column} - {row["Lineitem name"]}: {current_value}' if not pd.isna(current_value) else f'Inserire il valore di {column} per {row["Lineitem name"]}:',
                                        value=str(current_value) if not pd.isna(current_value) else "015790000000",
                                        key=input_key
                                    )
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value
                            
                            else: 
                                for idx, row in name_df.iterrows():
                                    current_value = row[column]
                                    input_key = f"{column}_{name}_{idx}"
                                    st.text_input(f"Valore attuale per {column} - {row['Lineitem name']}: {current_value}",
                                        value=str(current_value),
                                        key=input_key
                                    )
                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = new_value

                        else:
                            # Special handling for Location field
                            if column == "Location":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=["Firgun House", "LIL House"],
                                    index=0 if pd.isna(current_value) else 
                                        ["Firgun House", "LIL House"].index(current_value),
                                    key=input_key
                                )
                                

                            elif column == "Payment Method":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                
                                # Split the current payment method on '+' and clean the options
                                # if pd.notna(current_value):
                                #     if st.session_state.metodo_pagamento is None:
                                #         payment_options = [opt.strip() for opt in current_value.split('+')] 
                                #     else:
                                #         payment_options = [opt.strip() for opt in current_value.split('+')] + ([st.session_state.metodo_pagamento] 
                                #                                                                                if st.session_state.metodo_pagamento not in [opt.strip() 
                                #                                                                                                                             for opt in current_value.split('+')] else [])
                                # else:
                                #     payment_options = payments
                                    
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=PAYMENTS,
                                    index=0 if pd.isna(current_value) or not PAYMENTS else 0,
                                    key=input_key
                                )
                                

                            elif column == "Total":
                                if len(selected_rows) == 0:
                                    importo_pagato = float(name_df["Importo Pagato"].values[0])
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.number_input(f"Valore attuale per {column}: {current_value}",
                                    value = importo_pagato if pd.notna(importo_pagato) else 0.0,
                                    step = None, 
                                    format="%.2f",  # Format to display the float with 2 decimal places
                                    key=input_key)
                                
                                    
                            else:
                                # For other non-Lineitem columns
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.text_input(
                                    f"Valore attuale per {column}: {current_value}",
                                    value=str(current_value) if pd.notna(current_value) else "",
                                    key=input_key
                                )
                                
                            
                        # Apply the same value to all rows for non-Lineitem columns
                        for _, row in name_df.iterrows():
                            if row.original_index not in new_values:
                                new_values[row.original_index] = {
                                    'values': {},
                                }
                            new_values[row.original_index]['values'][column] = new_value
        

                    # Add a submit button
                    submit = st.form_submit_button(
                        "Conferma Modifiche",
                        disabled=not all_required_fields_filled
                    )

                # Store the submission state
                if submit and all_required_fields_filled:

                    if double_payment_method and "Payment Method" not in columns_to_edit:
                        st.error("È necessario compilare il campo Payment Method e scegliere un unico metodo di pagamento")
                        all_required_fields_to_continue = False

                    elif cambiare_metodo and "Payment Method" not in columns_to_edit:
                        st.error("È necessario compilare il campo Payment Method e cambiare il metodo affinchè coincida con il pagamento scelto")
                        all_required_fields_to_continue = False
                    
                    else:
                        row_nan_fields = [field for field in nan if pd.isna(row[field])] 
                        
                        if not row_nan_fields:
                            all_required_fields_to_continue = True
                                
                        for field in row_nan_fields:
                            if (field in new_values[row.original_index]['values'] and 
                                new_values[row.original_index]['values'][field].strip()) or (new_values[row.original_index]['values']["Total"] == 0 and field == "Paid at"):
                                all_required_fields_to_continue = True
                            else:
                                st.error(f"Il campo {field} è obbligatorio")
                                all_required_fields_to_continue = False

                        
                    if all_required_fields_to_continue:

                        if "Total" in columns_to_edit and new_value:
                            # new_total = float(new_value)
                            new_total = float(new_values[list(new_values.keys())[0]]['values']['Total'])
                            if len(selected_rows) == 0:
                                importo_pagato = float(name_df["Importo Pagato"].values[0])

                            #aggiunto dopo
                            if check.startswith("VALUTA"):
                                    importo_pagato = new_total
                                    numero_pagamento = name_df["Numero Pagamento"].values[0]
                                    st.session_state.pagamenti.loc[st.session_state.pagamenti['Numero Pagamento'] == numero_pagamento, 'Lordo'] = importo_pagato
                                    st.session_state.pagamenti.loc[st.session_state.pagamenti['Numero Pagamento'] == numero_pagamento, 'CHECK'] = "VERO"
                            
                            if new_total != importo_pagato:                                
                                st.session_state[f'needs_confirmation_{name}'] = True
                                st.session_state[f'new_values_{name}'] = new_values
                            else:
                                st.session_state[f'needs_confirmation_{name}'] = False
                                # Totals match, proceed with update
                                new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                
                                # After updating, check for payment method split if needed
                                if "Payment Method" in columns_to_edit:
                                    original_total = float(name_df["Total"].values[0])
                                    original_payment_method = name_df["Payment Method"].values[0]
                                    
                                    if (new_total == importo_pagato and 
                                        new_total != original_total and 
                                        "+" in original_payment_method and 
                                        "Gift Card" not in original_payment_method):
                                        
                                        payment_key = f"Payment Method_{name}_0"
                                        if payment_key in st.session_state:
                                            new_payment_method = st.session_state[payment_key]
                                            
                                            if new_payment_method and "+" not in new_payment_method:
                                                difference = original_total - new_total
                                                st.session_state[f'needs_aggiungi_check_{name}'] = True
                                                st.session_state[f'additional_values_add_{name}'] = {
                                                    'difference': difference,
                                                    'numero': name_df["Numero Pagamento"].values[0],
                                                    'old_payment_method': original_payment_method
                                                }

                                st.session_state[f'success_{name}'] = True
                        else:
                            # No total change, proceed with update
                            new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            st.session_state[f'success_{name}'] = True

                    ## Salva lo stato corrente in un file di backup
                    #auto_save_on_change()
            
                # Show confirmation form if needed
                if f'needs_confirmation_{name}' in st.session_state and st.session_state[f'needs_confirmation_{name}']:
                    st.warning("Il totale inserito non corrisponde all'importo effettivamente pagato. Salvare comunque le modifiche?")

                    with st.form(f"confirm_form_{name}"):
                        confirm_submit = st.form_submit_button("Salvare le modifiche")
                        
                        if confirm_submit:
                            new_values = st.session_state[f'new_values_{name}']
                            new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            st.session_state[f'needs_confirmation_{name}'] = False
                            # st.success("Modifiche salvate con successo!")
                            st.session_state[f'success_{name}'] = True
                            ## Salva lo stato corrente in un file di backup
                            #auto_save_on_change()

                # Show success message if it's in the session state
                if f'success_{name}' in st.session_state and st.session_state[f'success_{name}']:
                    st.success("Modifiche salvate con successo!")
                    orders_count += 1
                    to_modify = False
                    for n in st.session_state.numeri_pagamenti:
                        if n not in st.session_state.pagamenti_da_aggiungere_agee.keys():
                            st.session_state.pagamenti_da_aggiungere_agee[n] = name

                if f'needs_aggiungi_check_{name}' in st.session_state and st.session_state[f'needs_aggiungi_check_{name}']:
                    diff_values = st.session_state[f'additional_values_add_{name}']['difference']
                    old_payment_method = st.session_state[f'additional_values_add_{name}']['old_payment_method']
                    numero_pagamento = st.session_state[f'additional_values_add_{name}']['numero']
                    
                    if "Cash" in old_payment_method:
                        st.warning(f"Mancano {diff_values:.2f} euro per quest'ordine. Aggiungere una riga in cui {diff_values:.2f} euro sono stati pagati con Cash? Altrimenti saltare questo step e andare avanti.")

                        with st.form(f"add_row_cash_{name}"): 
                            # Submit button after all other form elements
                            confirm_submit = st.form_submit_button("Aggiungere")
                            
                            if confirm_submit:
                                new_result = add_row(st.session_state.processed_data, importi_pagati, st.session_state.metodo_pagamento, name, last_index_agee)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                last_index_agee += 1

                                st.session_state[f'needs_aggiungi_check_{name}'] = False
                                st.session_state[f'success_{name}'] = True
                                st.session_state[f'success_aggiunto_{name}'] = True
                                ## Salva lo stato corrente in un file di backup
                                #auto_save_on_change()
                    
                    else:
                        payments_used = list(map(str.strip, old_payment_method.split('+')))
                        st.warning(f"Mancano {diff_values:.2f}€ per quest'ordine: aggiungere altri pagamenti? Scegliere tra i seguenti, altrimenti saltare questo step e andare avanti.")
                        pagamenti_to_show = pagamenti[(pagamenti['CHECK'] != "VERO") 
                                                      & (pagamenti["Importo Pagato"] <= diff_values) 
                                                      & (pagamenti["Metodo"].isin(payments_used))
                                                      & (pagamenti["Numero Pagamento"] != numero_pagamento)]
                        pagamenti_to_show = pagamenti_to_show.sort_values(by = "Importo Pagato", ascending = False)

                        if not pagamenti_to_show.empty:
                            st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                            selected_rows = []
                            importi_pagati = []
                            metodi = []

                            for index, row in pagamenti_to_show.iterrows():
                                unique_key = f"add_pagamenti_{name}_{index}"
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
                                    if numero in st.session_state.pagamenti_da_aggiungere_agee.keys():
                                        matching_name = st.session_state.pagamenti_da_aggiungere_agee[numero]
                                        if matching_name != name:
                                            st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")
                                    else:
                                        if numero in st.session_state.pagamenti_da_aggiungere_lil.keys():
                                            matching_name_lil = st.session_state.pagamenti_da_aggiungere_lil[numero]
                                            st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name_lil} di LIL Milan")
                                        else:
                                            # Assign the payment to pagamenti_da_aggiungere if it hasn't been assigned
                                            st.session_state.pagamenti_da_aggiungere_agee[numero] = name
                                            
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

                                        st.session_state[f'needs_aggiungi_check_{name}'] = False
                                        st.session_state[f'success_{name}'] = True
                                        st.session_state[f'success_aggiunto_{name}'] = True

                                        st.session_state.metodo_pagamento = None
                                        selected_rows = []
                                        ## Salva lo stato corrente in un file di backup
                                        #auto_save_on_change()

                if f'success_aggiunto_{name}' in st.session_state and st.session_state[f'success_aggiunto_{name}']:
                    st.success("Aggiunto con successo!")
                    for n in st.session_state.numeri_pagamenti:
                        if n not in st.session_state.pagamenti_da_aggiungere_agee.keys():
                            st.session_state.pagamenti_da_aggiungere_agee[n] = name
                    if to_modify:
                        orders_count += 1
                
                            
    else:
        st.subheader("Nessun ordine di AGEE deve essere controllato")


    # # Save button with download option
    # if st.button("Salvare le modifiche finora apportate"):
    #     data = save_phase_state("ordini")
    #     st.download_button(
    #         label="Download le modifiche",
    #         data=data,
    #         file_name="salvataggio_modifiche.pkl",
    #         mime="application/octet-stream",
    #     )
################### pagamenti

    proceed_pagamenti = orders_count >= len(lil_df.Name.unique()) + len(agee_df.Name.unique()) 

    if proceed_pagamenti:  # Or your specific condition for moving to the next section
        section_placeholder.empty()  # Clears all contents of the placeholder
        # Proceed to the next section
        # st.write("Moving to the next section...")

        colonne_essenziali_pagamenti =  ['Name', 'Paid at', 'Lineitem quantity', 'Lineitem sku', "Shipping Country", 'Location', "Brand"]  
        
        pagamenti = aggiungi_pagamenti(st.session_state.pagamenti, st.session_state.pagamenti_da_aggiungere_lil, st.session_state.pagamenti_da_aggiungere_agee)
        st.session_state.pagamenti = pagamenti

        p =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] == "NON TROVATO")].copy()
        last_index_pag = p['original_index'].max()
        name_pagamenti = p["original_index"].unique()

        all_orders = st.session_state.processed_data["Name"].unique()
        names_count_pagamenti = len(st.session_state.pagamenti)
        count_pagamenti = 0
        
        #PAGAMENTI
        if len(p) > 0: 
            st.write("")
            st.subheader("Pagamenti da controllare")
                
            names_check = len(p)
            st.write(f"{names_check} pagamenti su {names_count_pagamenti}")
            
            for _, row in p.iterrows():
                idx = row["original_index"]
                check = row["CHECK"]
                metodo = row['Metodo']
                importo_pagato = row['Importo Pagato']                    

                with st.container():
                    st.markdown("---")
                    st.subheader(f"Pagamento con {metodo} di {importo_pagato}")

                    # Display current payment info
                    st.write("Pagamenti non collegati direttamente ad alcun ordine:")
                    if metodo == "PayPal Express Checkout":
                        colonne_pag = ["Metodo", "Data", "Nome", "Indirizzo email mittente", "Numero Pagamento", "Importo Pagato"]
                    else:
                        colonne_pag = ["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]

                    st.dataframe(pd.DataFrame([row])[colonne_pag],
                                use_container_width=True)

                    # Create unique keys for each payment's inputs
                    
                    choice_key = f"include_choice_{idx}"
                    total_quantity_key = f"total_quantities{idx}"
                    
                    order_num_key = f"order_num_{idx}"
                    paid_at_key = f"paid_at_{idx}"
                    country_key = f"country_{idx}" 
                    location_key = f"location_{idx}"
                    brand_key = f"brand_{idx}"
                    
                    # Radio buttons for including payment
                    include_choice = st.radio("Pagamento da includere negli ordini?",
                                            options=["No", "Si"],
                                            key=choice_key)

                    # Show order number and location input if "Si" is selected
                    
                    if include_choice == "Si":
                        new_values = [None, None, None, None, None, None, None, None, None, None]  # Initialize list to hold order number, date, quantities, sku, country and location
                        st.write("Inserire le seguenti informazioni")

                        #Name
                        if metodo == "Shopify Payments":
                            order_num = row["Numero Pagamento"]
                        else:
                            order = st.text_input("Inserire il numero di ordine relativo al pagamento (senza #)",
                                                    value = str(),
                                                    key=order_num_key)
                            order_num = "#"+str(order)

                        new_values[0] = order_num
                                            
                        #Paid at
                        if pd.isna(row["Data"]):
                            paid_at = st.text_input("Inserire la data dell'ordine relativo al pagamento nel formato yyyy-mm-dd",
                                                    value = str(),
                                                    key=paid_at_key)
                        else:
                            paid_at = row["Data"]
                        
                        new_values[1] = paid_at

                        #Total
                        new_values[2] = row["Importo Pagato"]

                        #Sku and Quantity:
                        total_quantity =  st.number_input("Quanti items diversi vanno inclusi?",
                                                            min_value=1,  # minimum allowed value
                                                            value=1,      # default value
                                                            step=1,       # increment by whole numbers
                                                            key=total_quantity_key)
                        
                        all_skus = []
                        all_names = []
                        all_quantities = []
                        all_included = []

                        for i in range(total_quantity):
                            name_key = f"name_{idx}_{i}" 
                            sku_key = f"sku_{idx}_{i}" 
                            quantity_key = f"quantity_{idx}_{i}"
                            include_key = f"include_{idx}_{i}"  # Unique key for the include checkbox

                            sku = st.text_input(
                                f"Inserire lo sku dell'item {i+1}",
                                value=str("015790000000"),
                                key=sku_key
                            )
                            
                            quantity_items = st.number_input(
                                f"Inserire la quantità dell'item {i+1}",
                                value=1,      # default value
                                step=1,       # increment by whole numbers
                                key=quantity_key
                            )
                            
                            name_items = st.text_input(
                                f"Inserire il name dell'item {i+1}",
                                value=str(),
                                key=name_key
                            )
                            
                            # # Checkbox for inclusion
                            # include_in_analysis = st.checkbox(
                            #     "Item da includere nelle analisi di unità vendute",
                            #     value=True,  # Checked by default
                            #     key=include_key
                            # )
                            
                            # Save the state of inclusion
                            if sku:  # Only check if a value was entered
                                if len(sku) == 12 and sku.isdigit():    
                                    all_skus.append(sku)
                                    all_quantities.append(quantity_items)
                                    all_names.append(name_items)

                                    # if not include_in_analysis:
                                    #     if sku not in st.session_state.sku_da_escludere:
                                    #         st.session_state.sku_da_escludere.append(sku)
                                else:
                                    st.error("Lo SKU inserito deve contenere 12 cifre. Ricontrollare")
                                    all_required_fields_filled = False

                        new_values[3] = all_skus
                        new_values[4] = all_quantities
                        new_values[5] = all_names

                        #Shipping Country
                        selected_country = st.text_input("Inserire il codice dello Shipping Country", 
                                                        value = "IT", 
                                                        key=country_key)

                        if selected_country:
                            try:
                                # Validation: ensure it's exactly 2 uppercase letters
                                if len(selected_country) == 2 and selected_country.isalpha():
                                    new_values[6] = selected_country.upper()
                            except ValueError:
                                st.error("Il codice del paese deve essere esattamente di 2 lettere.")
                                all_required_fields_filled = False

                        #Payment Method
                        new_values[7] = metodo  # Save selected location
                        
                        #Location
                        locations = ["LIL House", "Firgun House", "LIL House London"]
                        selected_location = st.selectbox("Seleziona la Location dell'ordine relativo al pagamento:", locations, key=location_key)

                        new_values[8] = selected_location  # Save selected location

                        #Brand
                        brand = ["LIL", "AGEE"]
                        selected_brand = st.selectbox("Seleziona il Brand dell'ordine relativo al pagamento:", brand, key=brand_key)

                        new_values[9] = selected_brand  # Save selected location

                    else:
                        new_values = [None, None, None, None, None, None, None, None, None, None]  # Initialize list to hold order number, date, quantities, sku, country and location

                            
                        # Add a submit button
                    submit = st.button(
                        "Conferma Modifiche",
                        key=f"confirm_changes_button_{idx}",
                        disabled=not all_required_fields_filled
                    )


                    # Save changes button
                    if submit and all_required_fields_filled:
                        if any(x is not None for x in new_values):
                            # Create a dictionary mapping positions to their field names
                            required_fields = {
                                1: "Data",
                                3: "Sku",
                                5: "Shipping Country",
                                7: "Location",
                                8: "Brand"
                            }
                            
                            # Check which required fields are None
                            missing_fields_pagamenti = []
                            for pos, field_name in required_fields.items():
                                if pos >= len(new_values):
                                    missing_fields_pagamenti.append(field_name)
                                elif pos == 3:  # Special check for Sku list
                                    # Check if new_values[pos] is None or if all strings in the list are empty
                                    if new_values[pos] is None or (isinstance(new_values[pos], list) and all(not str(sku).strip() for sku in new_values[pos])):
                                        missing_fields_pagamenti.append(field_name)
                                elif new_values[pos] is None:
                                    missing_fields_pagamenti.append(field_name)
                            
                            # If any required fields are missing, raise error with specific fields
                            if missing_fields_pagamenti:
                                error_message = "Mancano le informazioni per: " + ", ".join(missing_fields_pagamenti)
                                st.error(error_message)
                                all_required_fields_filled = False

                            nome_usato, totale_usato = get_nomi(st.session_state.processed_data, order_num)

                            if nome_usato:
                                st.session_state[f'ordine_esistente_tutto_totale_{idx}'] = True
                                st.session_state[f'useful_data_{idx}'] = {
                                                    'ordine': order_num,
                                                    'importo': totale_usato, 
                                                    "new_values": new_values
                                                }
                            else:
                                # No order match, proceed with update
                                new_result, new_pagamenti = update_df(st.session_state.processed_data, new_values, idx, st.session_state.pagamenti)
                                st.session_state.processed_data = new_result
                                st.session_state.pagamenti = new_pagamenti
                                st.session_state.saved_updates.add(idx)
                                st.session_state[f'success_{idx}'] = True
                        
                        else:
                                # No order match, proceed with update
                                new_result, new_pagamenti = update_df(st.session_state.processed_data, new_values, idx, st.session_state.pagamenti)
                                st.session_state.processed_data = new_result
                                st.session_state.pagamenti = new_pagamenti
                                st.session_state.saved_updates.add(idx)
                                st.session_state[f'success_{idx}'] = True
                        
                        ## Salva lo stato corrente in un file di backup
                        #auto_save_on_change()

                if f'ordine_esistente_tutto_totale_{idx}' in st.session_state and st.session_state[f'ordine_esistente_tutto_totale_{idx}']:
                    ordine = st.session_state[f'useful_data_{idx}']["ordine"]
                    importo = st.session_state[f'useful_data_{idx}']["importo"]
                    valori =  st.session_state[f'useful_data_{idx}']["new_values"]
                    totale_pagamento =  valori[2]
                    st.warning(f"L'ordine {ordine} è già stato assegnato a un pagamento. Aggiungere questo pagamento al totale attuale di {importo}€ dell'ordine?")
                    st.warning(f"Il totale finale sarebbe di {importo + totale_pagamento}€")

                    with st.form(f"aggiungere_{idx}"):
                        confirm_submit = st.form_submit_button("Aggiungere")
                        
                        if confirm_submit:
                            new_result, new_pagamenti = update_df(st.session_state.processed_data, valori, idx, st.session_state.pagamenti)
                            st.session_state.processed_data = new_result
                            st.session_state.pagamenti = new_pagamenti
                            st.session_state.saved_updates.add(idx)
                            st.session_state[f'ordine_esistente_tutto_totale_{idx}'] = False
                            st.session_state[f'success_{idx}'] = True
                            ## Salva lo stato corrente in un file di backup
                            #auto_save_on_change()

                # Show success message if it's in the session state
                if f'success_{idx}' in st.session_state and st.session_state[f'success_{idx}']:
                    st.success("Modifiche salvate con successo!")
                    count_pagamenti += 1
                    
        else:
            st.subheader("Nessun pagamento deve essere controllato")

                        
####EXCEL            
        proceed_excel = count_pagamenti >= len(p) 

        if proceed_excel:
            
            excel_filename = st.text_input("Inserire il nome da dare al file Excel (senza .xlsx):", value="output_file")
        
            # Add disabled state to the Generate Excel button
            if st.button("Genera Excel", key="generate_excel_button"): #, disabled=st.session_state.excel_generated):
                if excel_filename:
                    full_filename = f"{excel_filename}.xlsx"
                    with st.spinner('Creazione del file Excel in corso...'):
                        excel_file = generate_excel(st.session_state.processed_data, st.session_state.pagamenti, full_filename)
                    
                    st.success("File Excel generato con successo!")
                    st.session_state.excel_generated = True  # Set the flag to disable the button

                    # Provide a download link for the Excel file
                    with open(excel_file, "rb") as f:
                        st.download_button(
                            label="Download Excel",
                            data=f,
                            file_name=full_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.error("Per favore, inserire un nome valido per il file Excel.")