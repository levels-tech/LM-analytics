##FILE DI INTERFACCIA STREAMLIT

import streamlit as st
import pandas as pd
import numpy as np

from scripts.call_streamlit import run, update_df, check_files, missing_fields, add_row, aggiungi_pagamenti
from scripts.summary_excel import OrderSummary
from utils.exceptions import DateMismatchError


def generate_excel(df_ordini_all, pp, filename):
    order_summary = OrderSummary(df_ordini_all, pp, filename)
    order_summary.create_files()
    return filename


def check_all_updates_saved(name_ordini, name_pagamenti = None, pag = False):
    payment_indices = set(name_pagamenti)
    order_names = set(name_ordini)
    
    if pag == "yes":
        all_required_updates = payment_indices.union(order_names)
    else:
        all_required_updates = order_names
    all_updates_completed = all_required_updates.issubset(st.session_state.saved_updates)
    
    if not all_updates_completed:
        missing_updates = all_required_updates - st.session_state.saved_updates
        st.warning(f"Mancano ancora {len(missing_updates)} elementi da controllare.")
    
    return all_updates_completed



st.set_page_config(layout="wide")

colonne = ["CHECK", 'Name', "Total", 'Shipping', 'Discount Code', 'Discount Amount', 'Paid at', 'Payment Method', 
            'Email', 'Financial Status', 'Currency', 
           'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price', "Shipping Country", 'Refunded Amount', 'Outstanding Balance','Location',]   

colonne_to_drop = ["CHECK", 'Name', 'Shipping', 'Discount Code', 'Discount Amount', 'Paid at', 'Payment Method', 
            'Email', 'Financial Status', 'Currency', 
           'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price', "Shipping Country", 'Refunded Amount', 'Outstanding Balance','Location',]      

payments = ["Bonifico", "PayPal Express Checkout", "Qromo", "Satispay", "Scalapay", "Shopify Payments", "Gift Card", "Cash"]      

colonne_essenziali_pagamenti =  ['Name', "Total", 'Paid at', 'Lineitem quantity', 'Lineitem name', "Shipping Country", 'Location']      


# Initialize session state variables
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None
if 'pagamenti' not in st.session_state:
    st.session_state['pagamenti'] = None
if 'payment_responses' not in st.session_state or st.session_state['payment_responses'] is None:
    st.session_state['payment_responses'] = {}
if 'files_processed' not in st.session_state:
    st.session_state['files_processed'] = False
if 'excel_generated' not in st.session_state:
    st.session_state['excel_generated'] = False
if 'success_messages' not in st.session_state:
    st.session_state.success_messages = {}
if 'saved_updates' not in st.session_state:
    st.session_state.saved_updates = set()
if 'confirming' not in st.session_state:
    st.session_state.confirming = False


# Title of the page
st.title("Check Pagamenti LIL Milan e AGEE")

# Section for uploading order files
st.subheader("Caricare almeno un file di ordini")
ordine_files = {
    "Ordini LIL": {
        "file": st.file_uploader("Caricare file Ordini LIL", type=["csv"], key="ordini_lil"),
        "include": st.checkbox("File da includere", value=True, key="ordini_lil_include"),
    },
}
st.markdown("---")

ordine_files["Ordini AGEE"] = {
    "file": st.file_uploader("Caricare file Ordini AGEE", type=["csv"], key="ordini_agee"),
    "include": st.checkbox("File da includere", value=True, key="ordini_agee_include"),
}
st.markdown("---")

# Section for uploading payment files
st.subheader("Caricare almeno un file di pagamenti")

other_files = {
    "Bonifici": {
        "file": st.file_uploader("Caricare file per Bonifici", type=["xlsx"], key="bonifici"),
        "include": st.checkbox("File da includere", value=True, key="bonifici_include"),
    },
}
st.markdown("---")

other_files["Paypal"] = {
    "file": st.file_uploader("Caricare file per Paypal", type=["csv"], key="paypal"),
    "include": st.checkbox("File da includere", value=True, key="paypal_include"),
}
st.markdown("---")


other_files["Qromo"] = {
    "file": st.file_uploader("Caricare file per Qromo", type=["csv"], key="qromo"),
    "include": st.checkbox("File da includere", value=True, key="qromo_include"),
}
st.markdown("---")

other_files["Satispay"] = {
    "file": st.file_uploader("Caricare file per Satispay", type=["csv"], key="satispay"),
    "include": st.checkbox("File da includere", value=True, key="satispay_include"),
}
st.markdown("---")

other_files["Scalapay"] = {
    "file": st.file_uploader("Caricare file per Scalapay", type=["csv"], key="scalapay"),
    "include": st.checkbox("File da includere", value=True, key="scalapay_include"),
}
st.markdown("---")

other_files["Shopify AGEE"] = {
    "file": st.file_uploader("Caricare file per Shopify AGEE", type=["csv"], key="shopify_agee"),
    "include": st.checkbox("File da includere", value=True, key="shopify_agee_include"),
}
st.markdown("---")

other_files["Shopify LIL"] = {
    "file": st.file_uploader("Caricare file per Shopify LIL", type=["csv"], key="shopify_lil"),
    "include": st.checkbox("File da includere", value=True, key="shopify_lil_include"),
}
st.markdown("---")

# Input for month and year
month = st.number_input("Inserisci il mese di interesse (1-12):", min_value=1, max_value=12, step=1, value=10)  # Default to October
year = st.number_input("Inserisci l'anno di interesse:", min_value=2010, max_value=2100, step=1, value=2024)  # Default to 2024

# Warning logic and continuation option
missing_files = []

# Check if at least one file is uploaded for "ordine_files" and "other_files" categories
at_least_one_ordini = any(content["include"] and content["file"] for content in ordine_files.values())
at_least_one_other = any(content["include"] and content["file"] for content in other_files.values())

# Identify missing files in selected categories
for label, content in {**ordine_files, **other_files}.items():
    if content["include"] and not content["file"]:
        missing_files.append(label)

# Validation messages
proceed = True
if not at_least_one_ordini:
    st.error("Per favore, caricare almeno un file di ordini.")
    proceed = False
if not at_least_one_other:
    st.error("Per favore, caricare almeno un file di pagamenti.")
    proceed = False

if missing_files:
    st.warning(f"Attenzione! Mancano i file: {', '.join(missing_files)}")
    proceed = False

# Code to proceed with the next steps if proceed is True
if proceed:
    process_button = st.button("Processare i file", disabled=st.session_state.get("files_processed", False))

    if process_button:
        uploaded_ordini_files = {name: content["file"] for name, content in ordine_files.items() if content["file"] is not None and content["include"] is True}
        uploaded_other_files = {name: content["file"] for name, content in other_files.items() if content["file"] is not None and content["include"] is True}
        print(uploaded_ordini_files)
        try:
            with st.spinner('Elaborazione dei file in corso...'):
                # Check each uploaded and included order file
                for name, f_file in uploaded_ordini_files.items():
                    check_files(ordine_files, name, month, year)    
                for name, f_file in uploaded_other_files.items():
                    check_files(other_files, name, month, year)
                
                # check_files(ordine_files, name, month, year)     
                result_df, pagamenti_df = run(ordine_files, other_files, month, year)
                st.session_state.processed_data = result_df
                st.session_state.pagamenti = pagamenti_df
                # st.session_state.files_processed = True  # Set the flag to disable the button
        except DateMismatchError as e:
            st.error(f"❌ {e.message}")
            if e.details:
                st.info(e.details)
      
if st.session_state.processed_data is not None and st.session_state.pagamenti is not None:    
    st.session_state.processed_data['original_index'] = st.session_state.processed_data.index.astype(int)
    st.session_state.pagamenti['original_index'] = st.session_state.pagamenti.index.astype(int)

    # Display LIL Milan results that need checking
    df_rilevante = st.session_state.processed_data[(st.session_state.processed_data["CHECK"] != "ESCLUSO")].copy()
    df_rilevante_sorted = df_rilevante.sort_values(by=["CHECK", "Name"])
  
    print(df_rilevante.Brand.value_counts())
    names_count_lil = len(df_rilevante[df_rilevante["Brand"] == "Ordini LIL"]["Name"].unique())
    names_count_agee = len(df_rilevante[df_rilevante["Brand"] == "Ordini AGEE"]["Name"].unique())
    names_count_pagamenti = len(st.session_state.pagamenti)

    lil_df = df_rilevante_sorted[(df_rilevante_sorted["CHECK"] != "VERO") & (df_rilevante_sorted["Brand"] == "Ordini LIL")].copy()
    lil_df = lil_df.drop_duplicates(subset=colonne_to_drop)
    last_index_lil = lil_df['original_index'].max()
    name_lil = lil_df["Name"].unique()

    agee_df = df_rilevante_sorted[(df_rilevante_sorted["CHECK"] != "VERO") & (df_rilevante_sorted["Brand"] == "Ordini AGEE")].copy()
    agee_df = agee_df.drop_duplicates(subset=colonne_to_drop)
    last_index_agee = agee_df['original_index'].max()
    name_agee = agee_df["Name"].unique()

    name_ordini = np.concatenate([name_lil if len(name_lil) > 0 else np.array([]),
                                name_agee if len(name_agee) > 0 else np.array([])
                                ])
    
    pagamenti_da_aggiungere = {}

    pagamenti =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] != "VERO")].copy()

    #LIL MILAN
    if len(lil_df) > 0:
        st.write("")
        st.subheader("Ordini da controllare LIL Milan")
            
        names_check = lil_df[lil_df['Name'].notna()]['Name'].unique()
        st.write(f"{len(names_check)} ordini su {names_count_lil}")
            
        for name in names_check:
            with st.container():
                st.markdown("---")  # Visual separator
                st.subheader(f"Ordine: {name}")

                name_df = lil_df[lil_df['Name'] == name]
                check = name_df["CHECK"].values[0]
                metodo = name_df["Payment Method"].values[0]

                if check == "FALSO":
                    
                    if "Qromo" in metodo or "Satispay" in metodo:
                        st.write(f"Non è stato possibile determinare con certezza il pagamento corrispondente all'ordine {name}")
                        # st.write(f"Scegliere tra i pagamenti dello stesso giorno senza corrispondenza quello o quelli da associare. Altrimenti mettere il Total dell'ordine pari a 0.")

                    else:
                        st.write(f"Il totale non coincide con l'importo effettivamente incassato. Modificare i valori delle colonne opportune.")
                        st.write(f"Importo effettivamente incassato: {name_df['Importo Pagato'].values[0]}")
                
                elif check == "NON TROVATO":
                    st.write(f"Non è stato trovato un pagamento relativo all'ordine. Modificare i valori delle colonne opportune.")
                    st.write(f"Importo effettivamente incassato: 0")

                st.dataframe(name_df[colonne], use_container_width=True)

                # Check for required fields before showing the form
                nan, double_payment_method = missing_fields(lil_df, name)
                # missing_fields_str = [str(field) for field in nan]
                            
                if nan:
                    if check == "FALSO":
                        base_warning = f"Attenzione: I seguenti campi mancano ed è necessario inserirli per le analisi: {', '.join(nan)}"
                        st.warning(base_warning)

                    elif check == "NON TROVATO":
                        base_warning = f"Attenzione: I seguenti campi mancano e nel caso in cui l'ordine sia da includere, è necessario inserirli per le analisi: {', '.join(nan)}"
                        st.warning(base_warning)

                    # Show specific requirements for each missing field
                    for field in nan:
                        if field == "Paid at":
                            st.warning("Inserire la data di pagamento nella forma yyyy-mm-dd")
                        elif field == "Shipping Country":
                            st.warning("Inserire il codice a 2 lettere del paese (e.g. IT)")

                if double_payment_method:
                    base_warning = f"Attenzione: Scegliere il metodo di pagamento effettivamente usato in Payment Method:"
                    st.warning(base_warning)


                if "Qromo" in metodo or "Satispay" in metodo:
                    # Step 1: Extract the first list from 'possibili_pagamenti' in df
                    # Check if the first element is NaN, else assign its value directly
                    # Get the first element of 'possibili_pagamenti' column
                    possibili_pagamenti = name_df['possibili_pagamenti'].iloc[0]

                    # If possibili_pagamenti is NaN or empty, assign an empty list
                    possibili_pagamenti = [] if possibili_pagamenti is None or (isinstance(possibili_pagamenti, float) and np.isnan(possibili_pagamenti)) else possibili_pagamenti

                    # st.write(possibili_pagamenti)
                    # possibili_pagamenti = possibili_pagamenti if pd.notna(possibili_pagamenti) else []

                    # Step 2: Filter df_pagamenti based on matching 'Numero Pagamento' values
                    filtered_rows = pagamenti[pagamenti['Numero Pagamento'].isin(possibili_pagamenti)]

                    st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                    selected_rows = []
                    for index, row in filtered_rows.iterrows():
                        unique_key = f"{name}_{index}"
                        if st.checkbox(f"{row['Importo Pagato']}€ pagati alle {row['Data']}", key=unique_key):
                            selected_rows.append(row)
                    
                            # Get the key associated with row["Numero Pagamento"], if it exists
                            matching_key = None
                            for key, value in pagamenti_da_aggiungere.items():
                                if value == row["Numero Pagamento"]:
                                    matching_key = key
                                    break
                                
                            # if row in selected_rows:
                                # If a match is found, display a warning with the matching key
                            if matching_key:
                                st.warning(f"Il pagamento scelto è già stato assegnato all'ordine {matching_key}")
                            else:
                                pagamenti_da_aggiungere[name] = row["Numero Pagamento"]
                                importo_pagato = row['Importo Pagato']

                    # Show selected rows
                    if selected_rows:
                        selected_df = pd.DataFrame(selected_rows)
                        st.write("Hai selezionato:")
                        st.write(selected_df[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]])
                        st.write(f"Cambia il Total a: {selected_df['Importo Pagato'].iloc[0]}")
                    else:
                        st.write("Non hai selezionato alcun pagamento.")
                        st.write("Cambia il Total a 0.")
                        importo_pagato = 0
                        selected_rows.append(0)

                else:
                    selected_rows = []

                # Dropdown to select which columns to edit (multi-select)
                columns_to_edit = st.multiselect("Selezionare le colonne da modificare:", colonne, key=f"multiselect_{name}")

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
                            for idx, row in name_df.iterrows():
                                current_value = row[column]
                                input_key = f"{column}_{name}_{idx}"
                                new_value = st.text_input(
                                    f"Riga {idx + 1} - {row['Lineitem name']}: {current_value}",
                                    value=str(current_value),
                                    key=input_key
                                )
                                if row.original_index not in new_values:
                                    new_values[row.original_index] = {
                                        'values': {},
                                    }
                                new_values[row.original_index]['values'][column] = new_value

                            st.write("---")
                            pass
                        else:
                            # Special handling for Location field
                            if column == "Location":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=["Firgun House", "LIL House London", "LIL House"],
                                    index=0 if pd.isna(current_value) else 
                                        ["Firgun House", "LIL House London", "LIL House"].index(current_value),
                                    key=input_key
                                )
                                
                                # # Check if required field is filled
                                # if column in nan and not new_value:
                                #     if check == "FALSO":
                                #         all_required_fields_filled = False
                                #         st.error(f"Il campo {column} è obbligatorio")
                                #     elif check == "NON TROVATO":
                                #         st.session_state[f'non_trovato{name}'] = True


                            elif column == "Payment Method":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                
                                # Split the current payment method on '+' and clean the options
                                if pd.notna(current_value):
                                    payment_options = [opt.strip() for opt in current_value.split('+')]
                                else:
                                    payment_options = payments
                                    
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=payment_options,
                                    index=0 if pd.isna(current_value) or not payment_options else 0,
                                    key=input_key
                                )
                                
                                # # Check if required field is filled
                                # if column in nan and not new_value:
                                #     if check == "FALSO":
                                #         all_required_fields_filled = False
                                #         st.error(f"Il campo {column} è obbligatorio")
                                #     elif check == "NON TROVATO":
                                #         st.session_state[f'non_trovato{name}'] = True

                            elif column == "Total":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.text_input(
                                    f"Valore attuale per {column}: {current_value}",
                                    value=str(current_value) if pd.notna(current_value) else "",
                                    key=input_key
                                )
                                
                                # Check if the new total matches Importo Pagato
                                if new_value.strip():  # Only check if a value was entered
                                    try:
                                        new_total = float(new_value)
                                        if len(selected_rows) == 0:
                                            importo_pagato = float(name_df["Importo Pagato"].values[0])
                                        # if new_total != importo_pagato:
                                        #     st.warning("Il totale inserito non corrisponde all'importo effettivamente pagato. Salvare comunque le modifiche?")
                                            # confirm_save = st.button("Salvare le modifiche", key=f"confirm_total_{name}")
                                            # if not confirm_save:
                                            #     all_required_fields_filled = False
                                    except ValueError:
                                        st.error("Il valore inserito per Total non è un valido. Inserire un numero.")
                                        all_required_fields_filled = False
                                    
                            else:
                                # For other non-Lineitem columns
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.text_input(
                                    f"Valore attuale per {column}: {current_value}",
                                    value=str(current_value) if pd.notna(current_value) else "",
                                    key=input_key
                                )
                                
                                # if column in nan and not new_value:
                                #     if check == "FALSO":
                                        
                                #     elif check == "NON TROVATO":
                                #         st.session_state[f'non_trovato{name}'] = True
                            
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

                    row_nan_fields = [field for field in nan if pd.isna(row[field])]
                    if not row_nan_fields:
                        all_required_fields_to_continue = True
                            
                    for field in row_nan_fields:
                        if (field in new_values[row.original_index]['values'] and 
                            new_values[row.original_index]['values'][field].strip()):
                            all_required_fields_to_continue = True
                        else:
                            st.error(f"Il campo {field} è obbligatorio")
                            all_required_fields_to_continue = False

                        
                    if all_required_fields_to_continue:

                        if "Total" in columns_to_edit and new_value.strip():
                            # new_total = float(new_value)
                            new_total = float(new_values[list(new_values.keys())[0]]['values']['Total'])
                            if len(selected_rows) == 0:
                                importo_pagato = float(name_df["Importo Pagato"].values[0])
                            st.write(new_total, importo_pagato)
                            
                            if new_total != importo_pagato:
                                print("here!")
                                # Store the state and values for later confirmation
                                st.session_state[f'needs_confirmation_{name}'] = True
                                st.session_state[f'new_values_{name}'] = new_values
                                st.write(new_total, importo_pagato)
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
                                                st.session_state[f'new_values_{name}'] = {
                                                    'difference': difference,
                                                    'payment_method': new_payment_method
                                                }

                                else:
                                    new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                                    st.session_state.processed_data = new_result
                                    st.session_state.saved_updates.add(name)
                                    st.session_state[f'success_{name}'] = True
                        else:
                            # No total change, proceed with update
                            new_result, _ = update_df(st.session_state.processed_data, new_values, name)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            st.session_state[f'success_{name}'] = True

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

                if f'needs_aggiungi_check_{name}' in st.session_state and st.session_state[f'needs_aggiungi_check_{name}']:
                    diff_values = st.session_state[f'new_values_{name}']['difference']
                    new_payment_method = st.session_state[f'new_values_{name}']['payment_method']
                    st.warning(f"Mancano {diff_values:.2f} euro per quest'ordine. Aggiungere una riga in cui {diff_values:.2f} euro sono stati pagati con un altro metodo di pagamento?")
                    
                    with st.form(f"add_row_form_{name}"):
                        available_payments = [p for p in payments if p != new_payment_method]
                        additional_payment = st.selectbox(
                            "Scegliere il metodo di pagamento per l'importo rimanente:",
                            options=available_payments,
                            key=f"additional_payment_{name}"
                        )
                        
                        # Submit button after all other form elements
                        confirm_submit = st.form_submit_button("Salvare le modifiche")
                        
                        if confirm_submit:
                            print("yes")
                            new_result = add_row(st.session_state.processed_data, diff_values, additional_payment, name, last_index_lil)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            print(new_result.tail(5))
                            last_index_lil += 1

                            st.session_state[f'needs_aggiungi_check_{name}'] = False
                            # st.success("Modifiche salvate con successo!")
                            st.session_state[f'success_{name}'] = True


                # Show success message if it's in the session state
                if f'success_{name}' in st.session_state and st.session_state[f'success_{name}']:
                    st.success("Modifiche salvate con successo!")
    else:
        st.subheader("Nessun ordine di LIL Milan deve essere controllato")


    # order_changes_complete = check_all_updates_saved(name_ordini, pag = False)
    # #Excel generation part
    # if order_changes_complete:
    pagamenti = aggiungi_pagamenti(st.session_state.pagamenti, pagamenti_da_aggiungere)
        
    p =  pagamenti[(pagamenti["CHECK"] == "NON TROVATO")].copy()
    # pagamenti =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] == "NON TROVATO")].copy()
    # pagamenti = pagamenti.drop_duplicates(subset=colonne)
    last_index_pag = p['original_index'].max()
    name_pagamenti = p["original_index"].unique()

               
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
                quantity_key = f"quantity_items{idx}"
                
                location_key = f"location_{idx}"
                order_num_key = f"order_num_{idx}"
                country_key = f"country_{idx}" 

                # Radio buttons for including payment
                include_choice = st.radio("Pagamento da includere negli ordini?",
                                        options=["No", "Si"],
                                        key=choice_key)

                # Show order number and location input if "Si" is selected
                new_values = [None, None, None]  # Initialize list to hold order number and location
                if include_choice == "Si":
                    quantity_items =  st.number_input("Quanti items diversi vanno inclusi?",
                                                        min_value=1,  # minimum allowed value
                                                        value=1,      # default value
                                                        step=1,       # increment by whole numbers
                                                        key=quantity_key)
                                                                        
                    # Dropdown to select which columns to edit (multi-select)
                    columns_to_edit = st.multiselect("Selezionare le colonne da aggiungere:", colonne, key=f"multiselect_{idx}")

                    # Create a form for editing the selected columns
                    with st.form(f"edit_row_form_{idx}"):
                        st.write(f"Aggiunta pagamento con {metodo} di {importo_pagato}")

                        # Create a dictionary to store new values
                        new_values = {}
                        all_required_fields_filled = True

                        # Handle each selected column
                        for column in columns_to_edit:
                            if column.startswith('Lineitem'):
                                # For Lineitem columns, show input for each row
                                st.write(f"Modifica {column}:")
                                lineitem_values = []

                                for i in range(quantity_items):
                                    new_value = st.text_input(
                                        f"Inserire il valore per il primo item:",
                                        value=str(),
                                        key=quantity_key
                                    )
                                    lineitem_values.append(new_value) 

                                    if row.original_index not in new_values:
                                        new_values[row.original_index] = {
                                            'values': {},
                                        }
                                    new_values[row.original_index]['values'][column] = lineitem_values

                                st.write("---")

#################################################################################### ARRIVATA FINO A QUI 

                                pass
                            else:
                                # Special handling for Location field
                                if column == "Location":
                                    input_key = f"{column}_{name}_0"
                                    new_value = st.selectbox(
                                        f"Selezionare {column}:",
                                        options=["Firgun House", "LIL House London", "LIL House"],
                                        index=0 if pd.isna(current_value) else 
                                            ["Firgun House", "LIL House London", "LIL House"].index(current_value),
                                        key=input_key
                                    )
                                    
                                    # # Check if required field is filled
                                    # if column in nan and not new_value:
                                    #     if check == "FALSO":
                                    #         all_required_fields_filled = False
                                    #         st.error(f"Il campo {column} è obbligatorio")
                                    #     elif check == "NON TROVATO":
                                    #         st.session_state[f'non_trovato{name}'] = True


                                elif column == "Payment Method":
                                    current_value = name_df[column].values[0]
                                    input_key = f"{column}_{name}_0"
                                    
                                    # Split the current payment method on '+' and clean the options
                                    if pd.notna(current_value):
                                        payment_options = [opt.strip() for opt in current_value.split('+')]
                                    else:
                                        payment_options = payments
                                        
                                    new_value = st.selectbox(
                                        f"Selezionare {column}:",
                                        options=payment_options,
                                        index=0 if pd.isna(current_value) or not payment_options else 0,
                                        key=input_key
                                    )
                                    
                                    # # Check if required field is filled
                                    # if column in nan and not new_value:
                                    #     if check == "FALSO":
                                    #         all_required_fields_filled = False
                                    #         st.error(f"Il campo {column} è obbligatorio")
                                    #     elif check == "NON TROVATO":
                                    #         st.session_state[f'non_trovato{name}'] = True

                                elif column == "Total":
                                    current_value = name_df[column].values[0]
                                    input_key = f"{column}_{name}_0"
                                    new_value = st.text_input(
                                        f"Valore attuale per {column}: {current_value}",
                                        value=str(current_value) if pd.notna(current_value) else "",
                                        key=input_key
                                    )
                                    
                                    # Check if the new total matches Importo Pagato
                                    if new_value.strip():  # Only check if a value was entered
                                        try:
                                            new_total = float(new_value)
                                            importo_pagato = float(name_df["Importo Pagato"].values[0])
                                            # if new_total != importo_pagato:
                                            #     st.warning("Il totale inserito non corrisponde all'importo effettivamente pagato. Salvare comunque le modifiche?")
                                                # confirm_save = st.button("Salvare le modifiche", key=f"confirm_total_{name}")
                                                # if not confirm_save:
                                                #     all_required_fields_filled = False
                                        except ValueError:
                                            st.error("Il valore inserito per Total non è un valido. Inserire un numero.")
                                            all_required_fields_filled = False
                                        
                                else:
                                    # For other non-Lineitem columns
                                    current_value = name_df[column].values[0]
                                    input_key = f"{column}_{name}_0"
                                    new_value = st.text_input(
                                        f"Valore attuale per {column}: {current_value}",
                                        value=str(current_value) if pd.notna(current_value) else "",
                                        key=input_key
                                    )
                                    
                                    # if column in nan and not new_value:
                                    #     if check == "FALSO":
                                            
                                    #     elif check == "NON TROVATO":
                                    #         st.session_state[f'non_trovato{name}'] = True
                                
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





                        if row.original_index not in new_values:
                            new_values[row.original_index] = {
                                'values': {},
                            }
                        new_values[row.original_index]['values'][column] = new_value
        


                    

                    order_num = st.text_input("Inserire il numero di ordine relativo al pagamento (senza #)",
                                            key=order_num_key)
                    new_values[0] = order_num
                    
                    locations = ["LIL House", "Firgun House", "LIL House London", "Altro"]
                    selected_location = st.selectbox("Seleziona la Location dell'ordine relativo al pagamento:", locations, key=location_key)

                    # If "Other" is selected, provide a text input for custom entries
                    if selected_location == "Altro":
                        custom_location = st.text_input("Inserire la posizione:")
                        new_values[1] = custom_location  # Save custom location
                    else:
                        new_values[1] = selected_location  # Save selected location

    #                 # Input for Shipping Country Code
    #                 selected_country = st.text_input("Inserire il codice dello Shipping Country (e.g. IT)", key=country_key)

    #                 if selected_country:
    #                     # Validation: ensure it's exactly 2 uppercase letters
    #                     if len(selected_country) == 2 and selected_country.isalpha():
    #                         new_values[2] = selected_country.upper()
    #                     else:
    #                         st.warning("Il codice del paese deve essere esattamente di 2 lettere.")

    #                 # Store values in session state
    #                 st.session_state.payment_responses[idx] = {
    #                     'include': include_choice == "Si",
    #                     'order_number': order_num,
    #                     'location': new_values[1],
    #                     'country': selected_country}

    #             # Save changes button
    #             if st.button("Salva le modifiche", key=f"save_button_{idx}"):
    #                 try:
    #                     new_result, new_pagamenti = update_df(st.session_state.processed_data, idx, new_values, nota, st.session_state.pagamenti)
    #                     st.session_state.processed_data = new_result
    #                     st.session_state.pagamenti = new_pagamenti
    #                     # st.success("Modifiche salvate con successo.")
    #                     st.session_state.saved_updates.add(idx)
    #                     st.session_state.success_messages[idx] = True
    #                     # st.session_state[f"updated_{idx}"] = True  # Set the flag to hide this row
    #                 except ValueError as e:
    #                     st.error(str(e))

    #             # Move success message display outside all conditionals
    #             if st.session_state.success_messages.get(idx, False):
    #                 st.success("Modifiche salvate con successo.")
    # else:
    #     st.subheader("Nessun pagamento deve essere controllato")

    # # all_changes_complete = check_all_updates_saved()

    # # #Excel generation part
    # # if all_changes_complete:
    # #     st.markdown("---")
        
    # excel_filename = st.text_input("Inserire il nome da dare al file Excel (senza .xlsx):", value="output_file")
    
    # # Add disabled state to the Generate Excel button
    # if st.button("Genera Excel", disabled=st.session_state.excel_generated):
    #     if excel_filename:
    #         full_filename = f"{excel_filename}.xlsx"
    #         with st.spinner('Creazione del file Excel in corso...'):
    #             excel_file = generate_excel(st.session_state.processed_data, st.session_state.pagamenti, full_filename)
            
    #         st.success("File Excel generato con successo!")
    #         st.session_state.excel_generated = True  # Set the flag to disable the button

    #         # Provide a download link for the Excel file
    #         with open(excel_file, "rb") as f:
    #             st.download_button(
    #                 label="Download Excel",
    #                 data=f,
    #                 file_name=full_filename,
    #                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    #             )
    #     else:
    #         st.error("Per favore, inserire un nome valido per il file Excel.")