##FILE DI INTERFACCIA STREAMLIT

import streamlit as st
import pandas as pd
import numpy as np

# Your original imports should work now
from model.scripts.call_streamlit import run, update_df, check_files, missing_fields, add_row, aggiungi_pagamenti 
from model.scripts.summary_excel import OrderSummary 
from model.utils.exceptions import DateMismatchError

DEBUG_MODE = True

def generate_excel(df_ordini_all, pp, filename):
    order_summary = OrderSummary(df_ordini_all, pp, filename)
    order_summary.create_files()
    return filename


def check_all_updates_saved(name_ordini, name_pagamenti = None):
   
    order_names = set(name_ordini)
    
    if name_pagamenti:
        payment_indices = set(name_pagamenti)
        all_required_updates = payment_indices.union(order_names)
    else:
        all_required_updates = order_names
    all_updates_completed = all_required_updates.issubset(st.session_state.saved_updates)
    
    if not all_updates_completed:
        missing_updates = all_required_updates - st.session_state.saved_updates
        st.warning(f"Mancano ancora {len(missing_updates)} elementi da controllare.")
    
    return all_updates_completed

def get_nomi(df, nome_ordine):
    st.write(nome_ordine)
    if nome_ordine in df["Name"].unique():
        return True, df[df["Name"] == nome_ordine]["Total"].values[0]
    else:
        return False, 0


st.set_page_config(layout="wide")

colonne = ["CHECK", 'Name', "Total", 'Shipping', 'Discount Code', 'Discount Amount', 'Paid at', 'Payment Method', 
            'Email', 'Financial Status', 'Currency', 
           'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price', "Lineitem sku", "Shipping Country", 'Refunded Amount', 'Outstanding Balance','Location',]   

colonne_to_drop = ["CHECK", 'Name', 'Shipping', 'Discount Code', 'Discount Amount', 'Paid at', 'Payment Method', 
            'Email', 'Financial Status', 'Currency', 
           'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price', "Shipping Country", 'Refunded Amount', 'Outstanding Balance','Location',]      

payments = ["Bonifico", "PayPal Express Checkout", "Qromo", "Satispay", "Scalapay", "Shopify Payments", "Gift Card", "Cash"]      

colonne_essenziali_pagamenti =  ['Name', 'Paid at', 'Lineitem quantity', 'Lineitem sku', "Shipping Country", 'Location']    

exclude_skus = ['15790000893', '15790000914', '15790001247', '15790001060', '15790001068', '15790001083', '15790001059', '15790000888', 
                        '15790000892', '15790000689', '15790001064', '15790000687', '15790000894', '15790000916', '15790000890', '15790001070', 
                        '15790001065', '15790001073', '15790000891', '15790001502', '']

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
if 'metodo_pagamento' not in st.session_state:
    st.session_state.metodo_pagamento = None
if 'df_columns' not in st.session_state:
    st.session_state.df_columns = None
if 'pagamenti_columns' not in st.session_state:
    st.session_state.pagamenti_columns = None
if 'sku_da_escludere' not in st.session_state:
    st.session_state.sku_da_escludere = exclude_skus

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
    process_button = st.button("Processare i file", key="process_files_button", disabled=st.session_state.get("files_processed", False))

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

    modified_count = 0

    #LIL MILAN
    if len(lil_df) > 0:
        st.write("")
        st.subheader("Ordini da controllare LIL Milan")

        lil_df_sorted = lil_df.sort_values(by=["CHECK", "Name"])
            
        names_check = lil_df_sorted[lil_df_sorted['Name'].notna()]['Name'].unique()
        st.write(f"{len(names_check)} ordini su {names_count_lil}")
            
        for name in names_check:
            with st.container():
                st.markdown("---")  # Visual separator
                st.subheader(f"Ordine: {name}")

                name_df = lil_df[lil_df['Name'] == name]
                check = name_df["CHECK"].values[0]
                metodo = name_df["Payment Method"].values[0]

                if check == "FALSO":
                    
                    if "Qromo" in metodo:# or "Satispay" in metodo:
                        st.write(f"Non è stato possibile determinare con certezza il pagamento corrispondente all'ordine {name}")
                        # st.write(f"Scegliere tra i pagamenti dello stesso giorno senza corrispondenza quello o quelli da associare. Altrimenti mettere il Total dell'ordine pari a 0.")

                    else:
                        st.write(f"Il totale non coincide con l'importo effettivamente incassato. Modificare i valori delle colonne opportune.")
                        
                        if name_df["Shipping Country"].values[0] == "GB":
                            st.write("Verificare se la Location è LIL House London")
                        
                        st.write(f"Importo effettivamente incassato: **{name_df['Importo Pagato'].values[0]}**")

                
                elif check == "NON TROVATO":
                    st.write(f"Non è stato trovato un pagamento relativo all'ordine. Modificare i valori delle colonne opportune.")

                    if name_df["Shipping Country"].values[0] == "GB":
                            st.write("Verificare se la Location è LIL House London")
                            
                    st.write(f"Importo effettivamente incassato: **0**")

                elif check == "LONDON":
                    st.write(f"Il total è corretto, verificare se l'ordine è di LIL House London.")
                    st.write(f"Location attuale: **{name_df['Location'].values[0]}**")

                st.dataframe(name_df[colonne], use_container_width=True)

                # Check for required fields before showing the form
                nan, double_payment_method = missing_fields(lil_df, name)
                # missing_fields_str = [str(field) for field in nan]

                cambiare_metodo = False
                            
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
                        elif field == "Location":
                            st.warning("Scegliere tra le locations proposte")

                if double_payment_method:
                    base_warning = f"Attenzione: Payment Method va modificato, e va scelto un unico metodo di pagamento effettivamente usato"
                    st.warning(base_warning)

                numeri_pagamenti = []
                if "Qromo" in metodo:# or "Satispay" in metodo:
                    # Get possibili_pagamenti more cleanly
                    possibili_pagamenti = name_df['possibili_pagamenti'].iloc[0]
                    possibili_pagamenti = [] if possibili_pagamenti is None or (isinstance(possibili_pagamenti, float) and np.isnan(possibili_pagamenti)) else possibili_pagamenti

                    # Filter pagamenti DataFrame
                    filtered_rows = pagamenti[pagamenti['Numero Pagamento'].isin(possibili_pagamenti)]
                    
                    # Fix the condition using any() for Series comparison
                    # st.write(filtered_rows)
                    satispay_mask = (filtered_rows["Metodo"] == "Satispay") & (filtered_rows["Numero Pagamento"] == "0")
                    qromo_mask = filtered_rows["Metodo"] == "Qromo"
                    filtered_rows = filtered_rows[satispay_mask | qromo_mask]

                    if not filtered_rows.empty:
                        st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                        selected_rows = []
                        importi_pagati = []

                        for index, row in filtered_rows.iterrows():
                            unique_key = f"{name}_{index}"
                            if st.checkbox(f"{row['Importo Pagato']}€ pagati alle {row['Data']}", key=unique_key):
                                selected_rows.append(row)
                                importi_pagati.append(row["Importo Pagato"])
                                numeri_pagamenti.append(row["Numero Pagamento"])

                                st.session_state.metodo_pagamento = row["Metodo"]
                                proceed = True

                        # Handle selected payments
                        if len(selected_rows) > 0:
                            # Check for already assigned payments
                            for numero in numeri_pagamenti:
                                matching_name = pagamenti_da_aggiungere.get(numero)

                                # If a match is found, show a warning for the corresponding payment
                                if matching_name:
                                    st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")
                                else:
                                    # Assign the payment to pagamenti_da_aggiungere if it hasn't been assigned
                                    pagamenti_da_aggiungere[numero] = name
                            
                            # Display selected payments info
                            importo_pagato = sum(importi_pagati)
                            st.write("Hai selezionato:")
                            selected_df = pd.DataFrame(selected_rows)
                            st.write(selected_df[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]])
                            st.write(f"Cambia il Total a: {importo_pagato}")
                            
                            if metodo.replace("Gift Card", "").replace("+", "").replace(" ", "") != st.session_state.metodo_pagamento:  # Added .iloc[0]
                                st.warning(f"Cambia il Payment Method con {st.session_state.metodo_pagamento}")
                                cambiare_metodo = True
                        else:
                            st.write("Non hai selezionato alcun pagamento.")
                            st.write("Cambia il Total a 0.")
                            importo_pagato = 0
                            selected_rows.append(0)
                    else:
                        selected_rows = []
                        numeri_pagamenti.append(name_df["Numero Pagamento"].values[0])
                        st.session_state.metodo_pagamento = None
                else:
                    selected_rows = []
                    numeri_pagamenti.append(name_df["Numero Pagamento"].values[0])
                    st.session_state.metodo_pagamento = None

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
                                    if st.session_state.metodo_pagamento is None:
                                        payment_options = [opt.strip() for opt in current_value.split('+')] 
                                    else:
                                        payment_options = [opt.strip() for opt in current_value.split('+')] + ([st.session_state.metodo_pagamento] 
                                                                                                               if st.session_state.metodo_pagamento not in [opt.strip() 
                                                                                                                                                            for opt in current_value.split('+')] else [])
                                else:
                                    payment_options = payments
                                    
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=payment_options,
                                    index=0 if pd.isna(current_value) or not payment_options else 0,
                                    key=input_key
                                )
                                

                            elif column == "Total":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.number_input(f"Valore attuale per {column}: {current_value}",
                                    value=current_value if pd.notna(current_value) else 0,
                                    step = None, 
                                    format="%.2f",  # Format to display the float with 2 decimal places
                                    key=input_key)
                                
                                # Check if the new total matches Importo Pagato
                                if new_value:  # Only check if a value was entered
                                    try:
                                        # new_value = float(new_value)
                                        if len(selected_rows) == 0:
                                            importo_pagato = float(name_df["Importo Pagato"].values[0])
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
                                new_values[row.original_index]['values'][field].strip()):
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
                    st.warning(f"Mancano {diff_values:.2f} euro per quest'ordine. Aggiungere una riga in cui {diff_values:.2f} euro sono stati pagati con un altro metodo di pagamento? Altrimenti saltare questo step e andare avanti.")

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
                    modified_count += 1
                    for n in numeri_pagamenti:
                        if n not in pagamenti_da_aggiungere.keys():
                            pagamenti_da_aggiungere[n] = name
                    
    else:
        st.subheader("Nessun ordine di LIL Milan deve essere controllato")


    #AGEE
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

                if check == "FALSO":
                    
                    if "Qromo" in metodo or "Satispay" in metodo:
                        st.write(f"Non è stato possibile determinare con certezza il pagamento corrispondente all'ordine {name}")
                        # st.write(f"Scegliere tra i pagamenti dello stesso giorno senza corrispondenza quello o quelli da associare. Altrimenti mettere il Total dell'ordine pari a 0.")

                    else:
                        st.write(f"Il totale non coincide con l'importo effettivamente incassato. Modificare i valori delle colonne opportune.")
                        st.write(f"Importo effettivamente incassato: **{name_df['Importo Pagato'].values[0]}**")
                
                elif check == "NON TROVATO":
                    st.write(f"Non è stato trovato un pagamento relativo all'ordine. Modificare i valori delle colonne opportune.")
                    st.write(f"Importo effettivamente incassato: **0**")

                st.dataframe(name_df[colonne], use_container_width=True)

                # Check for required fields before showing the form
                nan, double_payment_method = missing_fields(agee_df, name)
                # missing_fields_str = [str(field) for field in nan]

                cambiare_metodo = False
                            
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
                        elif field == "Location":
                            st.warning("Scegliere tra le locations proposte")

                if double_payment_method:
                    base_warning = f"Attenzione: Payment Method va modificato, e va scelto un unico metodo di pagamento effettivamente usato"
                    st.warning(base_warning)

                numeri_pagamenti = []
                if "Qromo" in metodo or "Satispay" in metodo:
                    # Get possibili_pagamenti more cleanly
                    possibili_pagamenti = name_df['possibili_pagamenti'].iloc[0]
                    possibili_pagamenti = [] if possibili_pagamenti is None or (isinstance(possibili_pagamenti, float) and np.isnan(possibili_pagamenti)) else possibili_pagamenti

                    # Filter pagamenti DataFrame
                    filtered_rows = pagamenti[pagamenti['Numero Pagamento'].isin(possibili_pagamenti)]
                    
                    # Fix the condition using any() for Series comparison
                    # st.write(filtered_rows)
                    satispay_mask = (filtered_rows["Metodo"] == "Satispay") & (filtered_rows["Numero Pagamento"] == "0")
                    qromo_mask = filtered_rows["Metodo"] == "Qromo"
                    filtered_rows = filtered_rows[satispay_mask | qromo_mask]

                    if not filtered_rows.empty:
                        st.write("Selezionare uno o più pagamenti corrispondenti all'ordine:")
                        selected_rows = []
                        importi_pagati = []

                        for index, row in filtered_rows.iterrows():
                            unique_key = f"{name}_{index}"
                            if st.checkbox(f"{row['Importo Pagato']}€ pagati alle {row['Data']}", key=unique_key):
                                selected_rows.append(row)
                                importi_pagati.append(row["Importo Pagato"])
                                numeri_pagamenti.append(row["Numero Pagamento"])

                                st.session_state.metodo_pagamento = row["Metodo"]
                                proceed = True

                        # Handle selected payments
                        if len(selected_rows) > 0:
                            # Check for already assigned payments
                            for numero in numeri_pagamenti:
                                matching_name = pagamenti_da_aggiungere.get(numero)

                                # If a match is found, show a warning for the corresponding payment
                                if matching_name:
                                    st.warning(f"Il pagamento {numero} è già stato assegnato all'ordine {matching_name}")
                                else:
                                    # Assign the payment to pagamenti_da_aggiungere if it hasn't been assigned
                                    pagamenti_da_aggiungere[numero] = name
                            
                            # Display selected payments info
                            importo_pagato = sum(importi_pagati)
                            st.write("Hai selezionato:")
                            selected_df = pd.DataFrame(selected_rows)
                            st.write(selected_df[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]])
                            st.write(f"Cambia il Total a: {importo_pagato}")
                            
                            if metodo.replace("Gift Card", "").replace("+", "").replace(" ", "") != st.session_state.metodo_pagamento:  # Added .iloc[0]
                                st.warning(f"Cambia il Payment Method con {st.session_state.metodo_pagamento}")
                                cambiare_metodo = True
                        else:
                            st.write("Non hai selezionato alcun pagamento.")
                            st.write("Cambia il Total a 0.")
                            importo_pagato = 0
                            selected_rows.append(0)
                    else:
                        selected_rows = []
                        numeri_pagamenti.append(name_df["Numero Pagamento"].values[0])
                else:
                    selected_rows = []
                    numeri_pagamenti.append(name_df["Numero Pagamento"].values[0])

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
                                if pd.notna(current_value):
                                    if st.session_state.metodo_pagamento is None:
                                        payment_options = [opt.strip() for opt in current_value.split('+')] 
                                    else:
                                        payment_options = [opt.strip() for opt in current_value.split('+')] + ([st.session_state.metodo_pagamento] 
                                                                                                               if st.session_state.metodo_pagamento not in [opt.strip() 
                                                                                                                                                            for opt in current_value.split('+')] else [])
                                else:
                                    payment_options = payments
                                    
                                new_value = st.selectbox(
                                    f"Selezionare {column}:",
                                    options=payment_options,
                                    index=0 if pd.isna(current_value) or not payment_options else 0,
                                    key=input_key
                                )
                                

                            elif column == "Total":
                                current_value = name_df[column].values[0]
                                input_key = f"{column}_{name}_0"
                                new_value = st.number_input(f"Valore attuale per {column}: {current_value}",
                                    value=current_value if pd.notna(current_value) else 0,
                                    step = None, 
                                    format="%.2f",  # Format to display the float with 2 decimal places
                                    key=input_key)
                                # Check if the new total matches Importo Pagato
                                if new_value: 
                                    st.write(new_value, current_value) # Only check if a value was entered
                                    try:
                                        # new_value = float(new_value)
                                        if len(selected_rows) == 0:
                                            importo_pagato = float(name_df["Importo Pagato"].values[0])
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
                                new_values[row.original_index]['values'][field].strip()):
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
                    st.warning(f"Mancano {diff_values:.2f} euro per quest'ordine. Aggiungere una riga in cui {diff_values:.2f} euro sono stati pagati con un altro metodo di pagamento? Altrimenti saltare questo step e andare avanti.")

                    with st.form(f"add_row_form_{name}"):
                        available_payments = [p for p in payments if p != new_payment_method]
                        additional_payment = st.selectbox(
                            "Scegliere il metodo di pagamento per l'importo rimanente:",
                            options=available_payments,
                            key=f"additional_payment_{name}"
                        )
                        
                        # Submit button after all other form elements
                        confirm_submit = st.form_submit_button("Salvare le modifiche", key = "salvare_modifiche_add")
                        
                        if confirm_submit:
                            new_result = add_row(st.session_state.processed_data, diff_values, additional_payment, name, last_index_agee)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            print(new_result.tail(5))
                            last_index_agee += 1

                            st.session_state[f'needs_aggiungi_check_{name}'] = False
                            # st.success("Modifiche salvate con successo!")
                            st.session_state[f'success_{name}'] = True


                # Show success message if it's in the session state
                if f'success_{name}' in st.session_state and st.session_state[f'success_{name}']:
                    st.success("Modifiche salvate con successo!")
                    modified_count += 1
                    for n in numeri_pagamenti:
                        if n not in pagamenti_da_aggiungere.keys():
                            pagamenti_da_aggiungere[n] = name
    else:
        st.subheader("Nessun ordine di AGEE deve essere controllato")


################### pagamenti

    # ordini_finiti = st.button("Ordini Finiti", key = "ordini_finiti")
    st.write(modified_count, len(lil_df.Name.unique()) + len(agee_df.Name.unique()))
    can_proceed = modified_count == len(lil_df.Name.unique()) + len(agee_df.Name.unique()) 
    # can_proceed = modified_count >= 0 

    if can_proceed:

        st.write(pagamenti_da_aggiungere)

        colonne_essenziali_pagamenti =  ['Name', 'Paid at', 'Lineitem quantity', 'Lineitem sku', "Shipping Country", 'Location', "Brand"]  
        
        # order_changes_complete = check_all_updates_saved(name_ordini, pag = False)
        # #Excel generation part
        # if order_changes_complete:
        pagamenti = aggiungi_pagamenti(st.session_state.pagamenti, pagamenti_da_aggiungere)
        st.session_state.pagamenti = pagamenti
        print("BONIFICO URGENTE 6", len(st.session_state.pagamenti[st.session_state.pagamenti["Metodo"] == "Bonifico"]))
        print(st.session_state.pagamenti[st.session_state.pagamenti["Metodo"] == "Bonifico"])
            
        p =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] == "NON TROVATO")].copy()
        # pagamenti =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] == "NON TROVATO")].copy()
        # pagamenti = pagamenti.drop_duplicates(subset=colonne)
        last_index_pag = p['original_index'].max()
        name_pagamenti = p["original_index"].unique()

        all_orders = st.session_state.processed_data["Name"].unique()
        
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
                        # st.write("Inserire le seguqenti informazioni")# per ognuna di queste colonne: **{', '.join(colonne_essenziali_pagamenti)}**")
                                                                
                        st.write("Inserire le seguenti informazioni")

                        #Name
                        if metodo == "Shopify Payments":
                            # order_num = row["Numero Pagamento"].replace("#", "").strip()
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
                                value=str(),
                                key=sku_key
                            )
                            
                            quantity_items = st.number_input(
                                f"Inserire la quantità dell'item {i+1}",
                                min_value=0,  # minimum allowed value
                                value=1,      # default value
                                step=1,       # increment by whole numbers
                                key=quantity_key
                            )
                            
                            name_items = st.text_input(
                                f"Inserire il name dell'item {i+1}",
                                value=str(),
                                key=name_key
                            )
                            
                            # Checkbox for inclusion
                            include_in_analysis = st.checkbox(
                                "Item da includere nelle analisi di unità vendute",
                                value=True,  # Checked by default
                                key=include_key
                            )
                            
                            # Save the state of inclusion
                            if sku:  # Only check if a value was entered
                                if len(sku) == 12 and sku.isdigit():    
                                    all_skus.append(sku)
                                    all_quantities.append(quantity_items)
                                    all_names.append(name_items)

                                    if not include_in_analysis:
                                        if sku not in st.session_state.sku_da_escludere:
                                            st.session_state.sku_da_escludere.append(sku)
                                else:
                                    st.error("Lo SKU inserito deve contenere 12 cifre. Ricontrollare")
                                    all_required_fields_filled = False

                        new_values[3] = all_skus
                        new_values[4] = all_quantities
                        new_values[5] = all_names

                        #Shipping Country
                        selected_country = st.text_input("Inserire il codice dello Shipping Country (e.g. IT)", key=country_key)

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
                    # Store the submission state
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
                            # st.write(nome_usato, totale_usato)
                            # lista = sorted(st.session_state.processed_data["Name"].dropna().unique())
                            # st.write(lista)

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

                # Show success message if it's in the session state
                if f'success_{idx}' in st.session_state and st.session_state[f'success_{idx}']:
                    st.success("Modifiche salvate con successo!")
                    
        else:
            st.subheader("Nessun pagamento deve essere controllato")
                        

    # all_changes_complete = check_all_updates_saved(name_ordini)

    # #Excel generation part
    # if all_changes_complete:
    #     st.markdown("---")

    st.write(len(st.session_state.processed_data), len(st.session_state.pagamenti))
    print("BONIFICO URGENTE 6", len(st.session_state.pagamenti[st.session_state.pagamenti["Metodo"] == "Bonifico"]))
    print(st.session_state.pagamenti[st.session_state.pagamenti["Metodo"] == "Bonifico"])
        
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