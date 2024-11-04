##FILE DI INTERFACCIA STREAMLIT

import streamlit as st
import pandas as pd
import numpy as np

from scripts.call_streamlit import run, update_df
from scripts.summary_excel import OrderSummary
from utils.exceptions import DateMismatchError


def generate_excel(df_ordini_all, pp, filename):
    order_summary = OrderSummary(df_ordini_all, pp, filename)
    order_summary.create_files()
    return filename


def check_all_updates_saved():
    payment_indices = set(name_pagamenti)
    order_names = set(name_ordini)
    
    all_required_updates = payment_indices.union(order_names)
    all_updates_completed = all_required_updates.issubset(st.session_state.saved_updates)
    
    if not all_updates_completed:
        missing_updates = all_required_updates - st.session_state.saved_updates
        st.warning(f"Mancano ancora {len(missing_updates)} elementi da controllare.")
    
    return all_updates_completed

st.set_page_config(layout="wide")

colonne = ['Name', "Importo Pagato",  "Total", 'Shipping', 'Discount Code', 'Discount Amount', 'Paid at', 'Payment Method',
            # "note_interne", 
            'Email', 'Financial Status', 'Currency', 
           'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price', 'Refunded Amount', 'Outstanding Balance','Location',]               

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

# File upload boxes
st.subheader("Caricare almeno un file di ordini")
ordine_files = {
    "Ordini LIL": st.file_uploader("Caricare file Ordini LIL", type=["csv"], key="ordini_lil"),
    "Ordini AGEE": st.file_uploader("Caricare file Ordini AGEE", type=["csv"], key="ordini_agee"),
}

st.subheader("Caricare almeno un file di pagamenti")
other_files = {
    "Bonifici": st.file_uploader("Caricare file per Bonifici", type=["xlsx"]),
    "Paypal": st.file_uploader("Caricare file per Paypal", type=["csv"]),
    "Qromo": st.file_uploader("Caricare file per Qromo", type=["csv"]),
    "Satispay": st.file_uploader("Caricare file per Satispay", type=["csv"]),
    "Scalapay": st.file_uploader("Caricare file per Scalapay", type=["csv"]),
    "Shopify LIL": st.file_uploader("Caricare file per Shopify LIL", type=["csv"]),
    "Shopify AGEE": st.file_uploader("Caricare file per Shopify AGEE", type=["csv"]),
}

# Input for month and year
month = st.number_input("Inserisci il mese di interesse (1-12):", min_value=1, max_value=12, step=1, value=10)  # Default to October
year = st.number_input("Inserisci l'anno di interesse:", min_value=2010, max_value=2100, step=1, value=2024)  # Default to 2024

# When processing files - now with disabled state
process_button = st.button("Processare i file", disabled=st.session_state.files_processed)

if process_button:
    uploaded_ordini_files = {name: file for name, file in ordine_files.items() if file is not None}
    uploaded_other_files = {name: file for name, file in other_files.items() if file is not None}
    
    if not uploaded_ordini_files:
        st.error("Per favore, carica almeno un file di ordini.")
    elif not uploaded_other_files:
        st.error("Per favore, carica almeno un file di pagamenti.")
    else:
        try:
            with st.spinner('Elaborazione dei file in corso...'):
                result_df, pagamenti_df = run(uploaded_ordini_files, uploaded_other_files, month, year)
                st.session_state.processed_data = result_df
                st.session_state.pagamenti = pagamenti_df
                # st.session_state.files_processed = True  # Set the flag to disable the button
        except DateMismatchError as e:
            st.error(f"❌ {e.message}")
            if e.details:
                st.info(e.details)
      
if st.session_state.processed_data is not None and st.session_state.pagamenti is not None:    
    st.session_state.processed_data['index'] = st.session_state.processed_data.index 
    st.session_state.pagamenti['index'] = st.session_state.pagamenti.index 


    # Display LIL Milan results that need checking
    df_rilevante = st.session_state.processed_data[(st.session_state.processed_data["note_interne"] != "Non rilevante")].copy()
    df_rilevante_sorted = df_rilevante.sort_values(by=["note_interne", "Name"])
  
    names_count_lil = len(df_rilevante[df_rilevante["Brand"] == "LIL Milan"]["Name"].unique())
    names_count_agee = len(df_rilevante[df_rilevante["Brand"] == "AGEE"]["Name"].unique())
    names_count_pagamenti = len(st.session_state.pagamenti)

    lil_df = df_rilevante_sorted[(df_rilevante_sorted["CHECK"] != "VERO") & (df_rilevante_sorted["Brand"] == "LIL Milan")].copy()
    name_lil = lil_df["Name"].unique()

    agee_df = df_rilevante_sorted[(df_rilevante_sorted["CHECK"] != "VERO") & (df_rilevante_sorted["Brand"] == "AGEE")].copy()
    name_agee = agee_df["Name"].unique()

    name_ordini = np.concatenate([name_lil if len(name_lil) > 0 else np.array([]),
                                name_agee if len(name_agee) > 0 else np.array([])
                                ])

    pagamenti =  st.session_state.pagamenti[(st.session_state.pagamenti["CHECK"] == "NON TROVATO")].copy()
    name_pagamenti = pagamenti["index"].unique()

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
                nota = name_df["note_interne"].values[0] 

                if nota == "Gift Card" or nota == "Gift Card only":
                    if nota == "Gift Card":
                        st.write("Pagamento effettuato parzialmente con Gift Card:")
                        st.dataframe(name_df[colonne], use_container_width=True)

                        current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                        new_total = st.text_input(
                            "Controllare il valore della Gift Card e inserire il totale effettivo:",
                            value=str(current_total),
                            key=f"new_total_{name}")

                    else:
                        st.write("Pagamento effettuato interamente con Gift Card:")
                        st.dataframe(name_df[colonne], use_container_width=True)

                        current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                        new_total = st.text_input(
                            "Controllare il valore della Gift Card e porre il pagamento a 0:",
                            value=str(current_total),
                            key=f"new_total_{name}")
                    
                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        new_total_float = float(new_total) if new_total else 0.0

                        if new_total_float != importo_pagato:
                            st.session_state.confirming = True  # Set confirming flag
                        else:
                            index_list = name_df["index"].tolist()  # Get the indices of the rows
                            try:
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True
                            except ValueError as e:
                                st.error(str(e))  # Display the error message to the user
                            
                    if st.session_state.confirming:
                        index_list = name_df["index"].tolist()  # Get the indices of the rows
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        new_total_float = float(new_total) if new_total else 0.0
                        st.write(f"Il nuovo totale {new_total_float} non corrisponde all'importo pagato {importo_pagato}. Confermare comunque le modifiche? Altrimenti inserire l'importo corretto.")
                        if st.button("Conferma", key=f"confirm_button_{name}"):
                            try:
                                # Process the update
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result                          
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag

                                # Reset confirming state after confirmation
                                st.session_state.confirming = False
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Check and display the success message if set
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")
                        # del st.session_state.success_messages[name]

                elif nota == "Reso dubbio":
                    st.write("Reso dubbio:")
                    st.dataframe(name_df[colonne], use_container_width=True)

                    new_quantities = []  # To store the new quantities for each line item
                    index_list = []  # To hold the indexes of the relevant rows

                    for _, row in name_df.iterrows():
                        lineitem_name = row['Lineitem name']
                        current_quantity = row['Lineitem quantity'] if pd.notna(row['Lineitem quantity']) else 0  # Default to 0 if NaN
                        idx = row["index"]
                        
                        # Input for new quantity
                        new_quantity = st.text_input(
                            f"Inserire la quantità per l'elemento '{lineitem_name}':",
                            value=str(int(current_quantity)),
                            key=f"new_quantity_{idx}")

                        # Append the new quantity to the list and the index to index_list
                        new_quantities.append(int(new_quantity) if new_quantity.isdigit() else 0)
                        index_list.append(idx)

                    # The button here will appear after all quantity inputs
                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        try:
                            new_result, _ = update_df(st.session_state.processed_data, index_list, new_quantities, nota)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            st.session_state.success_messages[name] = True
                        except ValueError as e:
                            st.error(str(e))  # Display the error message to the user
                        
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")

        
                elif nota == "Pagamento non trovato":
                    st.write("Pagamento non trovato:")
                    st.dataframe(name_df[colonne], use_container_width=True)

                    # For quantity input (in case of "Reso dubbio")
                    current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                    new_total = st.text_input(
                        "Il pagamento non è stato trovato. Se l'ordine non è da considerare, cambiare il Total a 0.",
                        value=str(current_total),
                        key=f"new_total_{name}")

                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        # Convert new_total to float for comparison
                        new_total_float = float(new_total) if new_total else 0.0
                        index_list = name_df["index"].tolist()  # Get the indices of the rows

                        if new_total_float != 0:
                            st.session_state.confirming = True  # Set confirming flag
                        else:
                            try:
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Show confirmation only if we are in the confirming state
                    if st.session_state.confirming:
                        index_list = name_df["index"].tolist()  # Get the indices of the rows
                        new_total_float = float(new_total) if new_total else 0.0
                        st.write("Confermare il Total dell'ordine diverso da 0?")
                        if st.button("Conferma", key=f"confirm_button_{name}"):
                            try:
                                # Process the update
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result                          
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag

                                # Reset confirming state after confirmation
                                st.session_state.confirming = False
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Check and display the success message if set
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")
                        # del st.session_state.success_messages[name]

                        

                else:
                    st.write("Controllare l'ordine:")
                    st.dataframe(name_df[colonne], use_container_width=True)
                    
                    #Get current total and input for new total
                    current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                    new_total = st.text_input(
                        "Il pagamento non è stato trovato. Se l'ordine non è da considerare, cambiare il Total a 0.",
                        value=str(current_total),
                        key=f"new_total_{name}")

                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        # Convert new_total to float for comparison
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        new_total_float = float(new_total) if new_total else 0.0
                        index_list = name_df["index"].tolist()  # Get the indices of the rows

                        if new_total_float  != importo_pagato:
                            st.session_state.confirming = True  # Set confirming flag
                        else:
                            try:
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Show confirmation only if we are in the confirming state
                    if st.session_state.confirming:
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        index_list = name_df["index"].tolist()  # Get the indices of the rows
                        new_total_float = float(new_total) if new_total else 0.0
                        st.write(f"Il nuovo totale {new_total_float} non corrisponde all'importo pagato {importo_pagato}. Confermare comunque le modifiche? Altrimenti inserire l'importo corretto.")
                        if st.button("Conferma", key=f"confirm_button_{name}"):
                            try:
                                # Process the update
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result                          
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag

                                # Reset confirming state after confirmation
                                st.session_state.confirming = False
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Check and display the success message if set
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")
                        # del st.session_state.success_messages[name]                        
    else:
        st.subheader("Nessun ordine di LIL Milan deve essere controllato")

    #AGEE           
    if len(agee_df) > 0:
        st.write("")
        st.subheader("Ordini da controllare AGEE")
            
        names_check = agee_df[agee_df['Name'].notna()]['Name'].unique()
        st.write(f"{len(names_check)} ordini su {names_count_agee}")
            
        for name in names_check:

            with st.container():
                st.markdown("---")  # Visual separator
                st.subheader(f"Ordine: {name}")

                name_df = agee_df[agee_df['Name'] == name]
                nota = name_df["note_interne"].values[0] 

                if nota == "Gift Card" or nota == "Gift Card only":
                    if nota == "Gift Card":
                        st.write("Pagamento effettuato parzialmente con Gift Card:")
                        st.dataframe(name_df[colonne], use_container_width=True)

                        current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                        new_total = st.text_input(
                            "Controllare il valore della Gift Card e inserire il totale effettivo:",
                            value=str(current_total),
                            key=f"new_total_{name}")

                    else:
                        st.write("Pagamento effettuato interamente con Gift Card:")
                        st.dataframe(name_df[colonne], use_container_width=True)

                        current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                        new_total = st.text_input(
                            "Controllare il valore della Gift Card e porre il pagamento a 0:",
                            value=str(current_total),
                            key=f"new_total_{name}")
                    
                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        new_total_float = float(new_total) if new_total else 0.0

                        if new_total_float != importo_pagato:
                            st.session_state.confirming = True  # Set confirming flag
                        else:
                            index_list = name_df["index"].tolist()  # Get the indices of the rows
                            try:
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True
                            except ValueError as e:
                                st.error(str(e))  # Display the error message to the user
                            
                    if st.session_state.confirming:
                        index_list = name_df["index"].tolist()  # Get the indices of the rows
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        new_total_float = float(new_total) if new_total else 0.0
                        st.write(f"Il nuovo totale {new_total_float} non corrisponde all'importo pagato {importo_pagato}. Confermare comunque le modifiche? Altrimenti inserire l'importo corretto.")
                        if st.button("Conferma", key=f"confirm_button_{name}"):
                            try:
                                # Process the update
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result                          
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag

                                # Reset confirming state after confirmation
                                st.session_state.confirming = False
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Check and display the success message if set
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")
                        #del st.session_state.success_messages[name]

                elif nota == "Reso dubbio":
                    st.write("Reso dubbio:")
                    st.dataframe(name_df[colonne], use_container_width=True)

                    new_quantities = []  # To store the new quantities for each line item
                    index_list = []  # To hold the indexes of the relevant rows

                    for _, row in name_df.iterrows():
                        lineitem_name = row['Lineitem name']
                        current_quantity = row['Lineitem quantity'] if pd.notna(row['Lineitem quantity']) else 0  # Default to 0 if NaN
                        idx = row["index"]
                        
                        # Input for new quantity
                        new_quantity = st.text_input(
                            f"Inserire la quantità per l'elemento '{lineitem_name}':",
                            value=str(int(current_quantity)),
                            key=f"new_quantity_{idx}")

                        # Append the new quantity to the list and the index to index_list
                        new_quantities.append(int(new_quantity) if new_quantity.isdigit() else 0)
                        index_list.append(idx)

                    # The button here will appear after all quantity inputs
                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        try:
                            new_result, _ = update_df(st.session_state.processed_data, index_list, new_quantities, nota)
                            st.session_state.processed_data = new_result
                            st.session_state.saved_updates.add(name)
                            st.session_state.success_messages[name] = True
                        except ValueError as e:
                            st.error(str(e))  # Display the error message to the user
                        
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")

        
                elif nota == "Pagamento non trovato":
                    st.write("Pagamento non trovato:")
                    st.dataframe(name_df[colonne], use_container_width=True)

                    # For quantity input (in case of "Reso dubbio")
                    current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                    new_total = st.text_input(
                        "Il pagamento non è stato trovato. Se l'ordine non è da considerare, cambiare il Total a 0.",
                        value=str(current_total),
                        key=f"new_total_{name}")

                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        # Convert new_total to float for comparison
                        new_total_float = float(new_total) if new_total else 0.0
                        index_list = name_df["index"].tolist()  # Get the indices of the rows

                        if new_total_float != 0:
                            st.session_state.confirming = True  # Set confirming flag
                        else:
                            try:
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Show confirmation only if we are in the confirming state
                    if st.session_state.confirming:
                        index_list = name_df["index"].tolist()  # Get the indices of the rows
                        new_total_float = float(new_total) if new_total else 0.0
                        st.write("Confermare il Total dell'ordine diverso da 0?")
                        if st.button("Conferma", key=f"confirm_button_{name}"):
                            try:
                                # Process the update
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result                          
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag

                                # Reset confirming state after confirmation
                                st.session_state.confirming = False
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Check and display the success message if set
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")
                        # del st.session_state.success_messages[name]

                        

                else:
                    st.write("Controllare l'ordine:")
                    st.dataframe(name_df[colonne], use_container_width=True)
                    
                    #Get current total and input for new total
                    current_total = name_df['Total'].iloc[0] if len(name_df) > 0 else 0
                    new_total = st.text_input(
                        "Il pagamento non è stato trovato. Se l'ordine non è da considerare, cambiare il Total a 0.",
                        value=str(current_total),
                        key=f"new_total_{name}")

                    if st.button("Salva le modifiche", key=f"save_button_{name}"):
                        # Convert new_total to float for comparison
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        new_total_float = float(new_total) if new_total else 0.0
                        index_list = name_df["index"].tolist()  # Get the indices of the rows

                        if new_total_float  != importo_pagato:
                            st.session_state.confirming = True  # Set confirming flag
                        else:
                            try:
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Show confirmation only if we are in the confirming state
                    if st.session_state.confirming:
                        importo_pagato = (name_df['Importo Pagato'].iloc[0] if 'Importo Pagato' in name_df.columns and not name_df['Importo Pagato'].isna().all() else 0)
                        index_list = name_df["index"].tolist()  # Get the indices of the rows
                        new_total_float = float(new_total) if new_total else 0.0
                        st.write(f"Il nuovo totale {new_total_float} non corrisponde all'importo pagato {importo_pagato}. Confermare comunque le modifiche? Altrimenti inserire l'importo corretto.")
                        if st.button("Conferma", key=f"confirm_button_{name}"):
                            try:
                                # Process the update
                                new_result, _ = update_df(st.session_state.processed_data, index_list, new_total_float, nota)
                                st.session_state.processed_data = new_result                          
                                st.session_state.saved_updates.add(name)
                                st.session_state.success_messages[name] = True  # Set success message flag

                                # Reset confirming state after confirmation
                                st.session_state.confirming = False
                            except ValueError as e:
                                st.error(str(e))  # Display error message

                    # Check and display the success message if set
                    if st.session_state.success_messages.get(name, False):
                        st.success("Modifiche salvate con successo.")
                        # del st.session_state.success_messages[name]                        
    else:
        st.subheader("Nessun ordine di AGEE deve essere controllato")


    #PAGAMENTI
    if len(pagamenti) > 0: 
        
        st.write("")
        st.subheader("Pagamenti da controllare")
            
        names_check = len(pagamenti)
        st.write(f"{names_check} pagamenti su {names_count_pagamenti}")
        
        for _, row in pagamenti.iterrows():
               
            idx = row["index"]
            nota = row["note_interne"]

            with st.container():
                st.markdown("---")
                st.subheader(f"Pagamento con {row['Metodo']} di {row['Importo Pagato']}")

                # Display current payment info
                st.write("Pagamenti non collegati direttamente ad alcun ordine:")
                st.dataframe(pd.DataFrame([row])[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]],
                            use_container_width=True)

                # Create unique keys for each payment's inputs
                choice_key = f"include_choice_{idx}"
                order_num_key = f"order_num_{idx}"
                location_key = f"location_{idx}"
                country_key = f"country_{idx}" 

                # Radio buttons for including payment
                include_choice = st.radio("Pagamento da includere negli ordini?",
                                        options=["No", "Si"],
                                        key=choice_key)

                # Show order number and location input if "Si" is selected
                new_values = [None, None, None]  # Initialize list to hold order number and location
                if include_choice == "Si":
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

                    # Input for Shipping Country Code
                    selected_country = st.text_input("Inserire il codice dello Shipping Country (e.g. IT)", key=country_key)

                    if selected_country:
                        # Validation: ensure it's exactly 2 uppercase letters
                        if len(selected_country) == 2 and selected_country.isalpha():
                            new_values[2] = selected_country.upper()
                        else:
                            st.warning("Il codice del paese deve essere esattamente di 2 lettere.")

                    # Store values in session state
                    st.session_state.payment_responses[idx] = {
                        'include': include_choice == "Si",
                        'order_number': order_num,
                        'location': new_values[1],
                        'country': selected_country}

                # Save changes button
                if st.button("Salva le modifiche", key=f"save_button_{idx}"):
                    try:
                        new_result, new_pagamenti = update_df(st.session_state.processed_data, idx, new_values, nota, st.session_state.pagamenti)
                        st.session_state.processed_data = new_result
                        st.session_state.pagamenti = new_pagamenti
                        # st.success("Modifiche salvate con successo.")
                        st.session_state.saved_updates.add(idx)
                        st.session_state.success_messages[idx] = True
                        # st.session_state[f"updated_{idx}"] = True  # Set the flag to hide this row
                    except ValueError as e:
                        st.error(str(e))

                # Move success message display outside all conditionals
                if st.session_state.success_messages.get(idx, False):
                    st.success("Modifiche salvate con successo.")
    else:
        st.subheader("Nessun pagamento deve essere controllato")

    all_changes_complete = check_all_updates_saved()

    #Excel generation part
    if all_changes_complete:
        st.markdown("---")
        
        excel_filename = st.text_input("Inserire il nome da dare al file Excel (senza .xlsx):", value="output_file")
        
        # Add disabled state to the Generate Excel button
        if st.button("Genera Excel", disabled=st.session_state.excel_generated):
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