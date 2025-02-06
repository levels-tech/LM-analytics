##FILE DI INTERFACCIA STREAMLIT

import streamlit as st
import pandas as pd
import numpy as np
import pickle

# Your original imports should work now
from UI.orders_section.orders_pagination_handler import handle_paginated_section
from model.scripts.call_streamlit import run, update_df, check_files, missing_fields, add_row, aggiorna_pagamenti, generate_excel, validate_payment_fields
from model.scripts.pagination_pagamenti import handle_paginated_payments
from model.utils.exceptions import DateMismatchError
from UI.state_manager import SessionStateManager, auto_save_on_change
from UI.payment_manager import PaymentManager
from UI.orders_section.order_widgets import OrderWidgets
from UI.orders_section.order_section_manager import MethodHandler, ModifyOrderSelector, OrderDisplay, UpdateHandler, initialize_brand, validate_current_order


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

def get_order_total(df, nome_ordine):
    if nome_ordine in df["Name"].unique():
        return True, df[df["Name"] == nome_ordine]["Total"].values[0]
    else:
        return False, 0

def render_navigation(lil_df, agee_df):
    """Renders the navigation buttons for different sections"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Go to LIL Orders",
                    disabled=st.session_state.current_section == 'lil-orders', 
                    use_container_width=True):
            st.session_state.current_section = 'lil-orders'
            st.rerun()
            
    with col2:
        if st.button("Go to AGEE Orders", 
                    disabled=st.session_state.current_section == 'agee-orders',
                    use_container_width=True):
            st.session_state.current_section = 'agee-orders'
            st.rerun()
            
    with col3:
        # Only enable payments button if all orders are processed
        orders_completed = st.session_state.orders_count >= len(lil_df.Name.unique()) + len(agee_df.Name.unique()) 
        
        if st.button("Go to Payments Section", 
                    disabled= (not orders_completed) or (st.session_state.current_section == 'payments'),
                    use_container_width=True):
            st.session_state.current_section = 'payments'
            st.rerun()
    
    st.markdown("---")

def render_section_header():
    """Renders the header for the current section"""
    if st.session_state.current_section == 'lil-orders':
        st.subheader("LIL Milan Orders Section")
    elif st.session_state.current_section == 'agee-orders':
        st.subheader("AGEE Orders Section")
    elif st.session_state.current_section == 'payments':
        st.subheader("Payments Section")

st.set_page_config(layout="wide")

COLUMNS_TO_SHOW = ['Name', "Total", 'Shipping', 'Discount Code', 'Discount Amount', 'Paid at', 'Payment Method', 'Email', 'Financial Status', 'Currency', 
                   'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price', "Lineitem sku", "Shipping Country", 'Refunded Amount', 'Outstanding Balance', 'Location']   

PAYMENTS = ["Bonifico", "PayPal Express Checkout", "Qromo", "Satispay", "Scalapay", "Shopify Payments", "Gift Card", "Cash"]      

EXCLUDE_STRINGS = ["Luxury Pack", "Engraving", "E-gift", "Repair", "Whatever Tote", "Piercing Party", "LIL Bag"]
LOCATIONS_LIL = ["LIL House", "Firgun House", "LIL House London"]
LOCATIONS_AGEE = ["LIL House", "Firgun House"]


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
if 'pagamenti_unmatched' not in st.session_state:
    st.session_state.pagamenti_unmatched = {}
if 'restored_from_state' not in st.session_state:
    st.session_state.restored_from_state = False
if 'files_processed' not in st.session_state:
    st.session_state.files_processed = False
if 'orders_count' not in st.session_state:
    st.session_state.orders_count = 0
if 'current_section' not in st.session_state:
    st.session_state.current_section = 'lil-orders'



############ INPUT PAGE ###############

# Title of the page
st.title("Check di Pagamenti LIL Milan e AGEE")

# Create a container
upload_container = st.container()

# Wrap all the code inside the container
with upload_container:

    if not (st.session_state.restored_from_state or st.session_state.files_processed):           ## Se abbiamo fatto il restore dello stato non mostriamo la sezione di caricamento e ripristina stato
    
        # Sezione per il caricamento dello stato
        st.subheader("Riparti da dove hai lasciato")
        state_col1, state_col2 = st.columns(2)
        
        with state_col1:
            uploaded_state = st.file_uploader("Carica un file di stato salvato", type=['pkl'], key="widget_state_upload")
            state_manager = SessionStateManager()
            if uploaded_state is not None:
                state_data = state_manager.load_state_from_bytes(uploaded_state.read())
                restore_disabled = state_data is None
            else:
                state_data = state_manager.load_last_state()
                restore_disabled = state_data is None

        with state_col2:        
            st.write("")
            st.write("")  
            st.write("")  
            if st.button("Ripristina stato", disabled=restore_disabled, use_container_width=True):
                if state_data is not None:
                    for key in state_data:
                        st.session_state[key] = state_data[key]
                    st.session_state.restored_from_state = True  # Settiamo il flag
                    st.rerun()

    
        st.markdown("---")
        # Section for uploading order files
        st.subheader("Caricare almeno un file di ordini")
        order_files = {
            "Ordini LIL": {
                "file": st.file_uploader("Caricare file Ordini LIL", type=["csv"], key="widget_ordini_lil"),
                "include": st.checkbox("File da includere", value=True, key="widget_ordini_lil_include"),
            },
        }
        st.markdown("---")

        order_files["Ordini AGEE"] = {
            "file": st.file_uploader("Caricare file Ordini AGEE", type=["csv"], key="widget_ordini_agee"),
            "include": st.checkbox("File da includere", value=True, key="widget_ordini_agee_include"),
        }
        st.markdown("---")

        # Section for uploading payment files
        st.subheader("Caricare almeno un file di pagamenti")

        payment_files = {
            "Bonifici": {
                "file": st.file_uploader("Caricare file per Bonifici", type=["xlsx"], key="widget_bonifici"),
                "include": st.checkbox("File da includere", value=True, key="widget_bonifici_include"),
            },
        }
        st.markdown("---")

        payment_files["Paypal"] = {
            "file": st.file_uploader("Caricare file per Paypal", type=["csv"], key="widget_paypal"),
            "include": st.checkbox("File da includere", value=True, key="widget_paypal_include"),
        }
        st.markdown("---")


        payment_files["Qromo"] = {
            "file": st.file_uploader("Caricare file per Qromo", type=["csv"], key="widget_qromo"),
            "include": st.checkbox("File da includere", value=True, key="widget_qromo_include"),
        }
        st.markdown("---")

        payment_files["Satispay"] = {
            "file": st.file_uploader("Caricare file per Satispay", type=["csv"], key="widget_satispay"),
            "include": st.checkbox("File da includere", value=True, key="widget_satispay_include"),
        }
        st.markdown("---")

        payment_files["Scalapay"] = {
            "file": st.file_uploader("Caricare file per Scalapay", type=["csv"], key="widget_scalapay"),
            "include": st.checkbox("File da includere", value=True, key="widget_scalapay_include"),
        }
        st.markdown("---")

        payment_files["Shopify AGEE"] = {
            "file": st.file_uploader("Caricare file per Shopify AGEE", type=["csv"], key="widget_shopify_agee"),
            "include": st.checkbox("File da includere", value=True, key="widget_shopify_agee_include"),
        }
        st.markdown("---")

        payment_files["Shopify LIL"] = {
            "file": st.file_uploader("Caricare file per Shopify LIL", type=["csv"], key="widget_shopify_lil"),
            "include": st.checkbox("File da includere", value=True, key="widget_shopify_lil_include"),
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
        

        
        process_button = st.button("Processare i file", key="widget_process_files_button", 
                                    disabled=st.session_state.get("files_processed", False) or st.session_state.get("files_processed", False))
        

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
                    st.session_state.files_processed = True  # Set the flag to disable the button
                    st.rerun()
            except DateMismatchError as e:
                st.error(f"❌ {e.message}")
                if e.details:
                    st.info(e.details)
        
    else:
        # Se abbiamo ripristinato da uno stato o già processato i files, mostriamo solo il pulsante di download
        if st.button("Scarica stato corrente"):
            state_manager = SessionStateManager()
            state_bytes = state_manager.get_state_as_bytes()
            if state_bytes:
                st.download_button(
                    label="Download",
                    data=state_bytes,
                    file_name="saved_state.pkl",
                    mime="application/octet-stream"
                )


############### FINE PAGINA DI INPUT ###############

if st.session_state.processed_data is not None and st.session_state.pagamenti is not None:

    st.session_state.processed_data['original_index'] = st.session_state.processed_data.index.astype(int)
    st.session_state.pagamenti['original_index'] = st.session_state.pagamenti.index.astype(int)


    # Initialize brand df and other variables
    lil_df, last_index_lil, names_count_lil = initialize_brand(st.session_state.processed_data, "Ordini LIL", COLUMNS_TO_SHOW)
    agee_df, last_index_agee, unique_O_count_agee = initialize_brand(st.session_state.processed_data, "Ordini AGEE", COLUMNS_TO_SHOW)


    # Render navigation
    render_navigation(lil_df, agee_df)
    render_section_header()
    
    ############################################# LIL MILAN ORDERS SECTION #############################################

    # ///////////// CHUNK 1 //////////////
    # INIZIALIZZA IL DF E STAMPA GLI ORDINI DA CONTROLLARE
    
    if st.session_state.current_section == 'lil-orders':
        if len(lil_df) > 0:
            # st.write("")
            # st.subheader("Ordini da controllare LIL Milan")

            # Evita di fare il sorting e il filtering ad ogni ricarica
            # Se non c'è in variabile di stato ordina e calcola gli order id da coqntrollare altrimenti li carica da variabile di stato
            # TODO: si può ottimizzare il sorting e magari salvare in state variable
            lil_df_sorted = lil_df.sort_values(by=["CHECK", "Name"])
            unique_O_ID_Lil_da_ricontrollare = lil_df_sorted[lil_df_sorted['Name'].notna()]['Name'].unique()
            
            
            # st.write(f"{len(unique_O_ID_Lil_da_ricontrollare)} ordini su {names_count_lil}")
            st.session_state.pagamenti_unmatched =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] != "VERO")].copy() 

            lil_orders_dr_df = pd.DataFrame({'Name': unique_O_ID_Lil_da_ricontrollare})


            # Handle pagination for LIL orders
            lil_paginated_orders = handle_paginated_section(
                lil_orders_dr_df,
                names_count_lil,
                'lil',
                "Ordini da controllare LIL Milan"
            )

            # ///////////// FINE CHUNK 1 //////////////
            # ///////////// CHUNK 2 //////////////
            # ITERA SU TUTTI GLI ORDINI DA CONTROLLARE ESTRAPOLA 
            for name in lil_paginated_orders['Name']:
                name_df = lil_df[lil_df['Name'] == name]
                st.session_state.numeri_pagamenti = []          # Serve a salvare i pagamenti associati all'ordine | Resettiamo ad ogni nuovo ordine
                
                with st.container():
                    order_display = OrderDisplay()

                    # Mostra messaggi di warning in base alla tipologia di ordine (FALSO, NON TROVATO, LONDON, VALUTA)
                    check, metodo = order_display.show_order_header(name, name_df)

                    # Stampa il df dell'ordine corrente
                    order_display.show_order_data(name_df, COLUMNS_TO_SHOW)

                    # ///////////// FINE CHUNK 4 //////////////
                    # ///////////// CHUNK 5 //////////////
                    # CONTROLLA CHE L'ORDINE ABBIA TUTTI I CAMPI NECESSARI CON VALORI E MOSTRA I WARNING IN CASO DI MANCANZA
                    # INOLTRE CONTROLLA SE CI SONO METODI DI PAGAMENTO MULTIPLI E MOSTRA I WARNING IN CASO DI DOPPIO/TRIPLO PAGAMENTO

                    nan, double_payment_method = validate_current_order(lil_df, name, EXCLUDE_STRINGS)

                    st.session_state['cambiare_metodo'] = False
                    # ///////////// FINE CHUNK 5 //////////////
                    # ///////////// CHUNK 6 //////////////
                    # GESTISCE IL CASO DI ORDINI PAGATI CON QROMO (O SATISPAY OFFLINE) (SINGOLI O MULTIPLI CHE SIANO)

                    method_handler = MethodHandler(st.session_state.pagamenti_unmatched, name_df, name)
                    selected_rows, importo_pagato = method_handler.handle_method(metodo)

                    # ///////////// FINE CHUNK 7 //////////////
                    # ///////////// CHUNK 8 //////////////
                    # CREA GLI ELEMENTI PER LA MODIFICA DEI CAMPI E I RISPETTIVI SPAZI DI INSERIMENTO A SECONDA DELLA TIPOLOGIA
                    modify_order_selector = ModifyOrderSelector(name, name_df, PAYMENTS, importo_pagato, 
                                                                selected_rows, LOCATIONS_LIL, COLUMNS_TO_SHOW)

                    columns_to_edit = modify_order_selector.display_multiselect()

                    submit, new_values = modify_order_selector.editing_form(columns_to_edit)

                    section_placeholder = st.empty()

                    # ///////////// FINE CHUNK 8 //////////////
                    # ///////////// CHUNK 9 //////////////
                    # GESTISCE LE MODIFICHE FATTE E FA I CONTROLLI NECESSARI CHE CI SIA TUTTO PER PROSEGUIRE E AGGIORNARE IL DF POI AGGIORNA IL DF

                    ## Controlla se ci sono pagamenti doppi e non permette di procedere se non sono stati selezionati pagamenti
                    ## Se st.session_state['cambiare_metodo'] è True, controlla che il metodo di pagamento sia stato cambiato
                    ## In sostanza chiede di aggiornare Payment Method nelle due condizioni sopra segnate
                    ## Verifica che tutti i campi obbligatori che contenevano valori nulli siano stati compilati con dei nuovi valori
                    ## Gestisce tutte le verifiche derivanti dalle modifiche fatte e fa gli aggiornamenti di DF e di stato
                    ## In caso di discrepanza tra totale atteso e inserito chiede conferma
                    ## In caso di rimanenze di totale pagate con cash propone l'aggiunta di un riga con il rimanente in cash e chiede conferma
                    ## In caso di rimanenze di totale pagate con altro metodo di pagamento mostra checkbox coi pagamenti e ne fa selezionare altri, può essere ignorato
                    ## Aggiorna il DF e le variabili di stato
                    with section_placeholder.container():
                        
                        # Store the submission state

                        update_handler = UpdateHandler(name, name_df, new_values, st.session_state.orders_count, columns_to_edit, double_payment_method)
                        if submit:
                            update_handler.update_submitted(nan, selected_rows, check, importo_pagato, st.session_state.pagamenti_unmatched)                                

                        if f'needs_confirmation_{name}' in st.session_state and st.session_state[f'needs_confirmation_{name}']:
                            update_handler.needs_confirmation()
                        
                        if f'success_{name}' in st.session_state and st.session_state[f'success_{name}']:
                            update_handler.show_success()
                        
                        if f'needs_aggiungi_check_{name}' in st.session_state and st.session_state[f'needs_aggiungi_check_{name}']:
                            update_handler.needs_double_check()
                        
                        if f'success_aggiunto_{name}' in st.session_state and st.session_state[f'success_aggiunto_{name}']:
                            update_handler.double_check_success()

                        st.session_state.orders_count = update_handler.get_orders_count()
                    # ///////////// FINE CHUNK 9 //////////////


            # ///////////// CHUNK 10 //////////////                    
        else:
            section_placeholder = None
            st.subheader("Nessun ordine di LIL Milan deve essere controllato")
        # ///////////// FINE CHUNK 10 //////////////
        ## FINE LIL MILAN ORDERS

    ############################################# AGEE ORDERS SECTION #############################################
    elif st.session_state.current_section == 'agee-orders':
        if len(agee_df) > 0:
            # st.write("")
            # st.subheader("Ordini da controllare AGEE")

            agee_df_sorted = agee_df.sort_values(by=["CHECK", "Name"])
                
            num_O_Agee_da_ricontrollare = agee_df_sorted[agee_df_sorted['Name'].notna()]['Name'].unique()    
            # st.write(f"{len(num_O_Agee_da_ricontrollare)} ordini su {unique_O_count_agee}")

            # Create a DataFrame with unique orders
            agee_orders_dr_df = pd.DataFrame({'Name': num_O_Agee_da_ricontrollare})
            
            # Handle pagination for AGEE orders
            agee_paginated_orders = handle_paginated_section(
                agee_orders_dr_df,
                unique_O_count_agee,
                'agee',
                "Ordini da controllare AGEE"
            )

            for name in agee_paginated_orders["Name"]:
                name_df = agee_df[agee_df['Name'] == name]
                st.session_state.numeri_pagamenti = []

                with st.container():
                    order_display_agee = OrderDisplay()

                    # Mostra messaggi di warning in base alla tipologia di ordine (FALSO, NON TROVATO, LONDON, VALUTA)
                    check, metodo = order_display_agee.show_order_header(name, name_df)

                    # Stampa il df dell'ordine corrente
                    order_display_agee.show_order_data(name_df, COLUMNS_TO_SHOW)
                    
                    nan, double_payment_method = validate_current_order(agee_df, name, EXCLUDE_STRINGS)

                    st.session_state['cambiare_metodo'] = False

                    
                    method_handler_agee = MethodHandler(st.session_state.pagamenti_unmatched, name_df, name)
                    selected_rows, importo_pagato = method_handler_agee.handle_method(metodo)

                    modify_order_selector_agee = ModifyOrderSelector(name, name_df, PAYMENTS, importo_pagato, 
                                                                selected_rows, LOCATIONS_AGEE, COLUMNS_TO_SHOW)

                    columns_to_edit = modify_order_selector_agee.display_multiselect()

                    submit, new_values = modify_order_selector_agee.editing_form(columns_to_edit)
                    
                    update_handler_agee = UpdateHandler(name, name_df, new_values, st.session_state.orders_count, columns_to_edit, double_payment_method)
                    if submit:
                        update_handler_agee.update_submitted(nan, selected_rows, check, importo_pagato, st.session_state.pagamenti_unmatched)                                

                    if f'needs_confirmation_{name}' in st.session_state and st.session_state[f'needs_confirmation_{name}']:
                        update_handler_agee.needs_confirmation()
                    
                    if f'success_{name}' in st.session_state and st.session_state[f'success_{name}']:
                        update_handler_agee.show_success()
                    
                    if f'needs_aggiungi_check_{name}' in st.session_state and st.session_state[f'needs_aggiungi_check_{name}']:
                        update_handler_agee.needs_double_check()
                    
                    if f'success_aggiunto_{name}' in st.session_state and st.session_state[f'success_aggiunto_{name}']:
                        update_handler_agee.double_check_success()

                    st.session_state.orders_count = update_handler_agee.get_orders_count()                
                                
        else:
            st.subheader("Nessun ordine di AGEE deve essere controllato")

    ############################################# PAYMENT SECTION #############################################
    elif st.session_state.current_section == 'payments':

        proceed_pagamenti = st.session_state.orders_count >= len(lil_df.Name.unique()) + len(agee_df.Name.unique()) 

        if proceed_pagamenti: 
            # if section_placeholder is not None:
            #     section_placeholder.empty()  # Clears all contents of the placeholder

            # Inizializza il payment manager
            payment_manager = PaymentManager()

            colonne_essenziali_pagamenti =  ['Name', 'Paid at', 'Lineitem quantity', 'Lineitem sku', "Shipping Country", 'Location', "Brand"]  
            
            ## Se ho già fatto l'operazione di aggiornare i pagamenti, non la rifaccio
            ## Aggiorno il df di pagamenti così da rimuovere dal controllo quelli già associati in fase di Ordini
            ## Così facendo i pagamenti la lista di pagamenti da ricontrollare e quindi i pagamenti mostrati saranno sempre gli stessi.
            if 'aggiorna_pagamenti_done' not in st.session_state:
                st.session_state.pagamenti = aggiorna_pagamenti(st.session_state.pagamenti, st.session_state.pagamenti_da_aggiungere_lil, st.session_state.pagamenti_da_aggiungere_agee)
                st.session_state.aggiorna_pagamenti_done = True

            # Inizializza i pagamenti da controllare
            payment_manager.initialize_payments_to_check(st.session_state.pagamenti)
            
            # Ottieni tutti i pagamenti da controllare con il loro stato
            all_payments = payment_manager.get_payments_to_display()
            num_pagamenti_totale = len(st.session_state.pagamenti)
            count_pagamenti_controllati = payment_manager.get_processed_count()

            #PAGAMENTI
            if len(all_payments) > 0: 
                
                st.write("")
                st.subheader("Pagamenti da controllare")
                
                num_pagamenti_da_ricontrollare = len(all_payments)
                st.write(f"{num_pagamenti_da_ricontrollare} pagamenti su {num_pagamenti_totale}")
                
                # Mostra barra di progresso
                total_to_check = payment_manager.get_total_payments()
                current_progress = payment_manager.get_processed_count() / total_to_check if total_to_check > 0 else 0
                st.progress(current_progress)

                # Ottiene i pagamenti paginati per la pagina corrente
                paginated_payments = handle_paginated_payments(
                    all_payments,
                    num_pagamenti_totale
                )

                # Itera solo sui pagamenti della pagina corrente
                for _, pagamento in paginated_payments.iterrows():
                    all_required_fields_filled = True                       ## Flag per verificare che tutti i parametri necessari sono inseriti
                    idx = pagamento["original_index"]
                    metodo = pagamento['Metodo']
                    importo_pagato = pagamento['Importo Pagato']                    

                    with st.container():
                        st.markdown("---")

                        st.subheader(f"Pagamento con {metodo} di {importo_pagato}")

                        # Display current payment info
                        st.write("Pagamenti non collegati direttamente ad alcun ordine:")
                        if metodo == "PayPal Express Checkout":
                            colonne_pag = ["Metodo", "Data", "Nome", "Indirizzo email mittente", "Numero Pagamento", "Importo Pagato"]
                        else:
                            colonne_pag = ["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]


                        ## Mostra il Dataframe del pagamento
                        st.dataframe(pd.DataFrame([pagamento])[colonne_pag],
                                    use_container_width=True)

                        # Ottieni eventuali modifiche in sospeso per questo pagamento
                        pending_update = payment_manager.get_pending_update(idx)
                        
                        # Choice for including payment con default basato su pending_update
                        has_values = pending_update and any(x is not None for x in pending_update)
                        default_include = 1 if has_values else 0
                        include_choice = st.radio(
                            "Pagamento da includere negli ordini?",
                            options=["No", "Si"],
                            index=default_include,
                            key=f"widget_include_choice_{idx}"
                        )

                        # Handles the creation of the form for all the values
                        # Handles No case for payment exclusion
                        if include_choice == "Si":
                            new_values = [None] * 10                                  
                            st.write("Inserire le seguenti informazioni")


                            #Name
                            if metodo == "Shopify Payments":
                                order_num = pagamento["Numero Pagamento"]
                            else:
                                default_order = pending_update[0] if pending_update else ""
                                order = st.text_input(
                                    "Inserire il numero di ordine relativo al pagamento (senza #)",
                                    value=default_order.replace("#", "") if default_order else "",
                                    key=f"widget_order_num_{idx}"
                                )
                                order_num = "#" + str(order)
                            new_values[0] = order_num


                            #Paid at
                            if pd.isna(pagamento["Data"]):
                                default_date = pending_update[1] if pending_update else ""
                                paid_at = st.text_input(
                                    "Inserire la data dell'ordine relativo al pagamento nel formato yyyy-mm-dd",
                                    value=default_date,
                                    key=f"widget_paid_at_{idx}"
                                )
                            else:
                                paid_at = pagamento["Data"]
                            new_values[1] = paid_at


                            #Total
                            new_values[2] = pagamento["Importo Pagato"]


                            #Items:
                            default_quantity = len(pending_update[3]) if pending_update and pending_update[3] else 1
                            total_items_quantity = st.number_input(
                                "Quanti items diversi vanno inclusi?",
                                value=default_quantity,
                                step=1,
                                key=f"widget_total_quantities{idx}"
                            )
                            
                            if total_items_quantity <= 0:
                                st.error("Il numero di items deve essere maggiore di 0")
                                all_required_fields_filled = False

                            all_skus = []
                            all_quantities = []
                            all_lineitems_names = []

                            for i in range(max(total_items_quantity, 1)):
                                default_sku = pending_update[3][i] if pending_update and pending_update[3] and i < len(pending_update[3]) else "015790000000"
                                default_quantity = pending_update[4][i] if pending_update and pending_update[4] and i < len(pending_update[4]) else 1
                                default_name = pending_update[5][i] if pending_update and pending_update[5] and i < len(pending_update[5]) else ""

                                sku = st.text_input(
                                    f"Inserire lo sku dell'item {i+1}",
                                    value=default_sku,
                                    key=f"widget_sku_{idx}_{i}"
                                )
                                
                                quantity_items = st.number_input(
                                    f"Inserire la quantità dell'item {i+1}",
                                    value=default_quantity,
                                    step=1,
                                    key=f"widget_quantity_{idx}_{i}"
                                )
                                
                                name_items = st.text_input(
                                    f"Inserire il name dell'item {i+1}",
                                    value=default_name,
                                    key=f"widget_name_{idx}_{i}"
                                )
                                
                                all_skus.append(sku)
                                all_quantities.append(quantity_items)
                                all_lineitems_names.append(name_items)

                            new_values[3] = all_skus
                            new_values[4] = all_quantities
                            new_values[5] = all_lineitems_names

                            default_country = pending_update[6] if pending_update else "IT"
                            selected_country = st.text_input(
                                "Inserire il codice dello Shipping Country", 
                                value=default_country,
                                key=f"widget_country_{idx}"
                            )
                            new_values[6] = selected_country.upper() if selected_country else None

                            # if selected_country:
                            #     try:
                            #         # Validation: ensure it's exactly 2 uppercase letters
                            #         if len(selected_country) == 2 and selected_country.isalpha():
                            #             new_values[6] = selected_country.upper()
                            #     except ValueError:
                            #         st.error("Il codice del paese deve essere esattamente di 2 lettere.")
                            #         all_required_fields_filled = False


                            #Payment Method
                            new_values[7] = metodo  # Save the relative Payment Method
                            

                            #Location
                            locations = ["LIL House", "Firgun House", "LIL House London"]
                            default_location_idx = locations.index(pending_update[8]) if pending_update and pending_update[8] in locations else 0
                            selected_location = st.selectbox(
                                "Seleziona la Location dell'ordine relativo al pagamento:",
                                options=locations,
                                index=default_location_idx,
                                key=f"widget_location_{idx}"
                            )
                            new_values[8] = selected_location

                            # Brand
                            brands = ["LIL", "AGEE"]
                            default_brand_idx = brands.index(pending_update[9]) if pending_update and pending_update[9] in brands else 0
                            selected_brand = st.selectbox(
                                "Seleziona il Brand dell'ordine relativo al pagamento:",
                                options=brands,
                                index=default_brand_idx,
                                key=f"widget_brand_{idx}"
                            )
                            new_values[9] = selected_brand

                        else:
                            new_values = [None] * 10

                                
                            # Add a submit button
                        submit = st.button(
                            "Conferma Modifiche",
                            key=f"confirm_changes_button_{idx}",
                            disabled=not all_required_fields_filled
                        )


                        # Save changes button
                        # 2: Importo Pagato         | Non lo controlliamo perché c'è sempre - lo prendiamo direttamente dalla riga del pagamento
                        # 7: Metodo di Pagamento    | Non lo controlliamo perché c'è sempre - lo prendiamo direttamente dalla riga del pagamento
                        if submit:
                            if any(x is not None for x in new_values):
                                
                                all_required_fields_filled, missing_fields_pagamenti = validate_payment_fields(new_values, total_items_quantity)
                                
                                # If any required fields are missing, raise error with specific fields
                                if not all_required_fields_filled:
                                    error_message = "Informazioni non valide per: " + ", ".join(missing_fields_pagamenti)
                                    st.error(error_message)
                                
                                else:
                                    ## TODO: Gestire meglio questo controllo di pagamento associato all'ordine. Magari è un ordine a cui non è associato alcun pagamento
                                    ## Creare una lista di pagamenti associati all'ordine e controllare da li se l'ordine ha già pagamenti associati
                                    ## TODO: AAAAA Anche dentro update_df viene fatto così.
                                    is_order_name_used, current_total = get_order_total(st.session_state.processed_data, order_num)

                                    if is_order_name_used:
                                        st.session_state[f'is_order_name_used{idx}'] = True
                                        st.session_state[f'useful_data_{idx}'] = {
                                                            'ordine': order_num,
                                                            'importo': current_total, 
                                                            "new_values": new_values
                                                        }
                                    else:
                                        # Not matched to existing order, updates the payment
                                        payment_manager.add_pending_update(idx, new_values)
                                        payment_manager.mark_payment_completed(idx)
                                        st.session_state[f'success_{idx}'] = True
                            
                            else:
                                    # All values None - drops the payment
                                    payment_manager.add_pending_update(idx, new_values)
                                    payment_manager.mark_payment_completed(idx)
                                    st.session_state[f'success_{idx}'] = True
                            
                            ## Salva lo stato corrente in un file di backup
                            auto_save_on_change()

                    if f'is_order_name_used{idx}' in st.session_state and st.session_state[f'is_order_name_used{idx}']:
                        ordine = st.session_state[f'useful_data_{idx}']["ordine"]
                        importo = st.session_state[f'useful_data_{idx}']["importo"]
                        valori =  st.session_state[f'useful_data_{idx}']["new_values"]
                        totale_pagamento =  valori[2]
                        st.warning(f"L'ordine {ordine} è già stato assegnato a un pagamento. Aggiungere questo pagamento al totale attuale di {importo}€ dell'ordine?")
                        st.warning(f"Il totale finale sarebbe di {importo + totale_pagamento}€")

                        with st.form(f"aggiungere_{idx}"):
                            confirm_submit = st.form_submit_button("Aggiungere")
                            
                            if confirm_submit:
                                payment_manager.add_pending_update(idx, new_values)
                                payment_manager.mark_payment_completed(idx)
                                st.session_state[f'success_{idx}'] = True
                                st.rerun()
                                auto_save_on_change()

                    # Show success message if it's in the session state
                    if f'success_{idx}' in st.session_state and st.session_state[f'success_{idx}']:
                        st.success("Modifiche salvate con successo!")
                        count_pagamenti_controllati += 1
                        
            else:
                st.subheader("Nessun pagamento deve essere controllato")

                            
    ####EXCEL            
            proceed_excel = payment_manager.should_proceed_to_excel()

            if proceed_excel:
                    
                excel_filename = st.text_input("Inserire il nome da dare al file Excel (senza .xlsx):", value="output_file")
            
                # Add disabled state to the Generate Excel button
                if st.button("Genera Excel", key="widget_generate_excel_button"): #, disabled=st.session_state.excel_generated):

                    if excel_filename:
                        full_filename = f"{excel_filename}.xlsx"

                        with st.spinner('Applicazione modifiche e generazione Excel in corso...'):
                            # Prima applica tutte le modifiche pendenti
                            new_main_df, new_payments_df = payment_manager.apply_all_updates(
                                st.session_state.processed_data,
                                st.session_state.pagamenti
                            )
                            
                            # Aggiorna i DataFrame principali
                            st.session_state.processed_data = new_main_df
                            st.session_state.pagamenti = new_payments_df
                            
                            # Resetta lo stato del manager
                            payment_manager.reset_state()
                            
                            # Ora genera l'Excel con i dati aggiornati
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