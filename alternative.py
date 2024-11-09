#IN LILMILAN.PY DALLA RIGA 60 A 151
# 
import streamlit as st


# # Section for uploading order files
st.subheader("Caricare almeno un file di ordini")
ordine_files = {
    "Ordini LIL": {
        "file": st.file_uploader("Caricare file Ordini LIL", type=["csv"], key="ordini_lil"),
        # "include": st.checkbox("File da includere", value=True, key="ordini_lil_include"),
    },
    "Ordini AGEE": {
        "file": st.file_uploader("Caricare file Ordini AGEE", type=["csv"], key="ordini_agee"),
        # "include": st.checkbox("File da includere", value=True, key="ordini_agee_include"),
    },
}

# Section for uploading payment files
st.subheader("Caricare almeno un file di pagamenti")
other_files = {
    "Bonifici": {
        "file": st.file_uploader("Caricare file per Bonifici", type=["xlsx"], key="bonifici"),
        # "include": st.checkbox("File da includere", value=True, key="bonifici_include"),
    },
    "Paypal": {
        "file": st.file_uploader("Caricare file per Paypal", type=["csv"], key="paypal"),
        # "include": st.checkbox("File da includere", value=True, key="paypal_include"),
    },
    "Qromo": {
        "file": st.file_uploader("Caricare file per Qromo", type=["csv"], key="qromo"),
        # "include": st.checkbox("File da includere", value=True, key="qromo_include"),
    },
    "Satispay": {
        "file": st.file_uploader("Caricare file per Satispay", type=["csv"], key="satispay"),
        # "include": st.checkbox("File da includere", value=True, key="satispay_include"),
    },
    "Scalapay": {
        "file": st.file_uploader("Caricare file per Scalapay", type=["csv"], key="scalapay"),
        # "include": st.checkbox("File da includere", value=True, key="scalapay_include"),
    },
    "Shopify LIL": {
        "file": st.file_uploader("Caricare file per Shopify LIL", type=["csv"], key="shopify_lil"),
        # "include": st.checkbox("File da includere", value=True, key="shopify_lil_include"),
    },
    "Shopify AGEE": {
        "file": st.file_uploader("Caricare file per Shopify AGEE", type=["csv"], key="shopify_agee"),
        # "include": st.checkbox("File da includere", value=True, key="shopify_agee_include"),
    },
}


# Input for month and year
month = st.number_input("Inserisci il mese di interesse (1-12):", min_value=1, max_value=12, step=1, value=10)  # Default to October
year = st.number_input("Inserisci l'anno di interesse:", min_value=2010, max_value=2100, step=1, value=2024)  # Default to 2024

# Warning logic and continuation option
missing_files = []

# Check if at least one file is uploaded for "ordine_files" and "other_files" categories
at_least_one_ordini = any(content["file"] for content in ordine_files.values())
at_least_one_other = any(content["file"] for content in other_files.values())

# Identify missing files in selected categories
for label, content in {**ordine_files, **other_files}.items():
    if not content["file"]:
        missing_files.append(label)




##############################################
#linea 207 di lilmilan.py

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
    



######################
######LINEA 520

# #PAGAMENTI
    # if len(pagamenti) > 0: 
        
    #     st.write("")
    #     st.subheader("Pagamenti da controllare")
            
    #     names_check = len(pagamenti)
    #     st.write(f"{names_check} pagamenti su {names_count_pagamenti}")
        
    #     for _, row in pagamenti.iterrows():
               
    #         idx = row["index"]
    #         nota = row["note_interne"]

    #         with st.container():
    #             st.markdown("---")
    #             st.subheader(f"Pagamento con {row['Metodo']} di {row['Importo Pagato']}")

    #             # Display current payment info
    #             st.write("Pagamenti non collegati direttamente ad alcun ordine:")
    #             st.dataframe(pd.DataFrame([row])[["Metodo", "Data", "Numero Pagamento", "Importo Pagato"]],
    #                         use_container_width=True)

    #             # Create unique keys for each payment's inputs
    #             choice_key = f"include_choice_{idx}"
    #             order_num_key = f"order_num_{idx}"
    #             location_key = f"location_{idx}"
    #             country_key = f"country_{idx}" 

    #             # Radio buttons for including payment
    #             include_choice = st.radio("Pagamento da includere negli ordini?",
    #                                     options=["No", "Si"],
    #                                     key=choice_key)

    #             # Show order number and location input if "Si" is selected
    #             new_values = [None, None, None]  # Initialize list to hold order number and location
    #             if include_choice == "Si":
    #                 order_num = st.text_input("Inserire il numero di ordine relativo al pagamento (senza #)",
    #                                         key=order_num_key)
    #                 new_values[0] = order_num
                    
    #                 locations = ["LIL House", "Firgun House", "LIL House London", "Altro"]
    #                 selected_location = st.selectbox("Seleziona la Location dell'ordine relativo al pagamento:", locations, key=location_key)

    #                 # If "Other" is selected, provide a text input for custom entries
    #                 if selected_location == "Altro":
    #                     custom_location = st.text_input("Inserire la posizione:")
    #                     new_values[1] = custom_location  # Save custom location
    #                 else:
    #                     new_values[1] = selected_location  # Save selected location

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