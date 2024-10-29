import streamlit as st
from classes import Ordini, ShopifyMatcher, ScalapayMatcher, SatispayMatcher, PaypalMatcher, QromoMatcher, BonificoMatcher, MatcherRunner, run  

if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None

# Title of the page
st.title("Check Pagamenti LIL Milan")

# File upload boxes
st.subheader("Carica almeno un file di 'Ordini'")
ordine_files = {
    "Ordini LIL": st.file_uploader("Caricare file Ordini LIL", type=["csv", "xlsx"], key="ordini_lil"),
    "Ordini AGEE": st.file_uploader("Caricare file Ordini AGEE", type=["csv", "xlsx"], key="ordini_agee"),
}

st.subheader("Carica almeno un file di pagamenti")
other_files = {
    "Bonifici": st.file_uploader("Caricare file per Bonifici", type=["csv", "xlsx"]),
    "Paypal": st.file_uploader("Caricare file per Paypal", type=["csv", "xlsx"]),
    "Qromo": st.file_uploader("Caricare file per Qromo", type=["csv", "xlsx"]),
    "Satispay": st.file_uploader("Caricare file per Satispay", type=["csv", "xlsx"]),
    "Scalapay": st.file_uploader("Caricare file per Scalapay", type=["csv", "xlsx"]),
    "Shopify LIL": st.file_uploader("Caricare file per Shopify LIL", type=["csv", "xlsx"]),
    "Shopify AGEE": st.file_uploader("Caricare file per Shopify AGEE", type=["csv", "xlsx"]),
}

# Input for month and year
month = st.number_input("Inserisci il mese di interesse (1-12):", min_value=9, max_value=12, step=1)
year = st.number_input("Inserisci l'anno di interesse:", min_value=2024, max_value=2100, step=1)

# When processing files
if st.button("Processare i file"):
    st.write("Button clicked")
    uploaded_ordini_files = {name: file for name, file in ordine_files.items() if file is not None}
    uploaded_other_files = {name: file for name, file in other_files.items() if file is not None}
    
    st.write("Uploaded files:", 
             "\nOrdini:", list(uploaded_ordini_files.keys()),
             "\nOthers:", list(uploaded_other_files.keys()))

    # Ensure at least one file in each category is uploaded
    if not uploaded_ordini_files:
        st.error("Per favore, carica almeno un file di Ordini.")
    elif not uploaded_other_files:
        st.error("Per favore, carica almeno un file di pagamenti.")
    else:
        try:
            with st.spinner('Elaborazione dei file in corso...'):
                st.write("Starting processing...")
                try:
                    st.write("About to call run function")
                    st.write("Type of uploaded_ordini_files:", type(uploaded_ordini_files))
                    st.write("Content of uploaded_ordini_files:", uploaded_ordini_files)
                    st.write("Type of uploaded_other_files:", type(uploaded_other_files))
                    st.write("Content of uploaded_other_files:", uploaded_other_files)
                    st.write("month:", month)
                    st.write("year:", year)

                    result_df = run(uploaded_ordini_files, uploaded_other_files, month, year)
                    st.write("Run function completed")
                except Exception as inner_e:
                    st.error(f"Error calling run function: {str(inner_e)}")
                    st.error(f"Type of error: {type(inner_e)}")
                    import traceback
                    st.error(f"Traceback: {traceback.format_exc()}")
                    raise inner_e


                # # Run the processing function only once
                # result_df = run(uploaded_ordini_files, uploaded_other_files, month, year)
                # st.write("Processing complete. Type of result:", type(result_df))
                # if isinstance(result_df, pd.DataFrame):
                #     st.write("Shape of result:", result_df.shape)
                
                # st.session_state['processed_data'] = result_df
                # st.success('Elaborazione completata!')
                
        except Exception as e:
            st.error(f"Si è verificato un errore durante l'elaborazione: {str(e)}")

# When displaying results
if 'processed_data' in st.session_state and st.session_state['processed_data'] is not None:
    st.write("Found processed data in session state")
    result_df = st.session_state['processed_data']
    st.write("Type of result_df:", type(result_df))
    
    # Display LIL Milan results
    mask = (result_df["CHECK"] != "VERO") & (result_df["Brand"] == "LIL Milan")
    st.write("Number of True values in mask:", mask.sum())
    
    lil_df = result_df[mask].copy()
    st.write("Shape of lil_df:", lil_df.shape)



# # Check if files are uploaded and at least one Ordini file and one other file is provided 
# if st.button("Processare i file"):
#     uploaded_ordini_files = {name: file for name, file in ordine_files.items() if file is not None}
#     uploaded_other_files = {name: file for name, file in other_files.items() if file is not None}

#     # Ensure at least one file in each category is uploaded
#     if not uploaded_ordini_files:
#         st.error("Per favore, carica almeno un file di Ordini.")
#     elif not uploaded_other_files:
#         st.error("Per favore, carica almeno un file di pagamenti.")
#     else:
#         try:
#             with st.spinner('Elaborazione dei file in corso...'):
#                 # Run the processing function only once
#                 result_df = run(uploaded_ordini_files, uploaded_other_files, month, year)
#                 st.session_state.processed_data = result_df
#                 st.success('Elaborazione completata!')
                
#         except Exception as e:
#             st.error(f"Si è verificato un errore durante l'elaborazione: {str(e)}")
# # After initializing session state
# st.write("Session state initialized:", st.session_state)

# Display results if they exist in session state
# if st.session_state.processed_data is not None:
#     result_df = st.session_state.processed_data
    
#     # Display LIL Milan results
#     lil_df = result_df[(result_df["CHECK"] != "VERO") & (result_df["Brand"] == "LIL Milan")].copy()  # Use .copy() to avoid SettingWithCopyWarning
    
#     if len(lil_df) > 0:
#         st.subheader("Ordini da controllare LIL Milan")
        
#         # Get unique names
#         unique_names = lil_df['Name'].dropna().unique()  # Get non-NaN names
#         has_nan = lil_df['Name'].isna().sum()

#         st.write(f"{len(unique_names)} ordini  e {has_nan} pagamenti da controllare")
        
#         # Initialize session state for storing new total values if not exists
#         if 'new_totals' not in st.session_state:
#             st.session_state.new_totals = {}

#         # Create a tab view for better organization
#         tab1, tab2 = st.tabs(["Visualizza e Modifica", "Scarica Risultati"])
        
#         with tab1:
#             # Loop through each unique name
#             for name in unique_names:
#                 # Create an expander for each name
#                 with st.expander(f"Ordine: {name}"):
#                     # Get all rows for this name
#                     name_df = lil_df[lil_df['Name'] == name]
                    
#                     # Display the current rows
#                     st.write("Dati attuali:")
#                     st.dataframe(name_df, use_container_width=True)
                    
#                     # Get the current total
#                     current_total = name_df['Total'].iloc[0] if len(lil_df) > 0 else 0
                    
#                     # Create a unique key for this name's input
#                     input_key = f"new_total_{name}"
                    
#                     # Add number input for new total
#                     new_total = st.number_input(
#                         "Inserisci il nuovo valore per 'Total':",
#                         min_value=0.0,
#                         value=float(current_total),
#                         step=0.01,
#                         key=input_key
#                     )
                    
#                     # Store the new value in session state
#                     st.session_state.new_totals[name] = new_total
                    
#                     # Add a confirmation message if the value has been changed
#                     if new_total != current_total:
#                         st.info(f"Valore modificato da {current_total} a {new_total}")
        
#         with tab2:
#             if st.button("Salvare tutte le modifiche"):
#                 # Create a copy of the original dataframe
#                 updated_df = lil_df.copy()
                
#                 # Update the Total values
#                 for name, new_total in st.session_state.new_totals.items():
#                     updated_df.loc[updated_df['Name'] == name, 'Total'] = new_total
                
#                 # Update the session state with modified dataframe
#                 mask = (st.session_state.processed_data["CHECK"] != "VERO") & (st.session_state.processed_data["Brand"] == "LIL Milan")
#                 st.session_state.processed_data.loc[mask, 'Total'] = updated_df['Total']
                
#                 st.success("Modifiche salvate con successo!")

#     # Add a button to clear all results if needed
#     if st.button("Pulire tutti i risultati"):
#         st.session_state.processed_data = None
#         st.session_state.new_totals = {}
#         st.experimental_rerun()