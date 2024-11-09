#FILE CON FUNZIONI CHIAMATE DIRETTAMENTE DA STREAMLIT


import pandas as pd

from scripts.ordini import Ordini
from scripts.runner import MatcherRunner

from matchers.matcher_bonifico import BonificoMatcher
from matchers.matcher_qromo import QromoMatcher
from matchers.matcher_paypal import PaypalMatcher
from matchers.matcher_satispay import SatispayMatcher
from matchers.matcher_scalapay import ScalapayMatcher
from matchers.matcher_shopify import ShopifyMatcher

from utils.columns_state import ColumnsState
from utils.exceptions import DateMismatchError
from utils.functions import reformat_date, find_header_row

def check_files(file, name, mese, anno):

    date_column = {"Ordini LIL": "Paid at",
                   "Ordini AGEE": "Paid at",
                   "Bonifici": "Data",
                   "Paypal": "Data",
                   "Qromo": "Data",
                   "Satispay": "payment_date",
                   "Scalapay": "Data acquisto/rimborso",
                   "Shopify AGEE": "Transaction Date",
                   "Shopify LIL": "Transaction Date"}

    expected_date =  f"{str(anno)}-{str(mese):02}"
    f_file = file.get(name, {}).get("file")
    
    if f_file: 
        if name == "Bonifici":
            f = find_header_row(f_file, "Importo")
        else:
            f = pd.read_csv(f_file, dtype={date_column[name]: "string"}) #, encoding="ISO-8859-1")
        
        f[date_column[name]] = f[date_column[name]].apply(reformat_date)
        f_filtered = f[f[date_column[name]].str[:7] == expected_date].copy()
        if len(f_filtered) == 0:
            found_dates = sorted(f[date_column[name]].str[:7].unique())
            raise DateMismatchError(
                message=f"Nel file di {name} non sono stati trovati dati per il periodo {expected_date}",
                details=(f"Date disponibili nel file: {', '.join(found_dates)}\n"
                        "Selezionare un periodo presente nel file o caricare un file del periodo corretto."))
        return True
    
        
def run(file_o, file_p, mese, anno):
    #ordini
    print("ordini iniziati")
    ordini_processor = Ordini(file_o, mese=mese, anno=anno)
    ordini, df_columns = ordini_processor.preprocess() 
    print("ordini finiti")

    ColumnsState.get_instance().set_df_columns(df_columns)

    try:
        #run matchers
        shopify_matcher = ShopifyMatcher(file_p, df_ordini=ordini)
        scalapay_matcher = ScalapayMatcher(file_p, df_ordini=ordini)
        satispay_matcher = SatispayMatcher(file_p, df_ordini=ordini)
        paypal_matcher = PaypalMatcher(file_p, df_ordini=ordini)
        qromo_matcher = QromoMatcher(file_p, df_ordini=ordini)
        bonifico_matcher = BonificoMatcher(file_p, df_ordini=ordini)

        # Create the matchers list
        matchers = [
            shopify_matcher,
            scalapay_matcher,
            satispay_matcher,
            paypal_matcher,
            qromo_matcher,
            bonifico_matcher
        ]

        runner = MatcherRunner(matchers, ordini)
        print("Runner created")
        
        result, pagamenti, pagamenti_columns = runner.run_all_matchers(mese, anno)
        ColumnsState.get_instance().set_pagamenti_columns(pagamenti_columns)
        
        return result, pagamenti
    
    except Exception as e:
        print(f"Error in run: {str(e)}")
        raise e


def missing_fields(df, nome):
    to_check = []
    to_change = []
    
    # Check for NaN values in specific columns
    if df[df["Name"] == nome]["Paid at"].isna().all():
        to_check.append("Paid at")
    if df[df["Name"] == nome]["Shipping Country"].isna().all():
        to_check.append("Shipping Country")
    if df[df["Name"] == nome]["Location"].isna().all():
        to_check.append("Location")
    if df[df["Name"] == nome]["Payment Method"].str.contains(r'\+').all() & (~df[df["Name"] == nome]["Payment Method"].str.contains("Gift Card").all()):
        to_change.append("Payment Method")
    
    return to_check, to_change


def add_row(df, diff, payment, nome, last_index):
    """
    Add a new row to the dataframe based on an existing row for a given name,
    with updated Original_Index.
    
    Parameters:
    df (pandas.DataFrame): Input dataframe
    diff (float): New value for the Total column
    payment (str): New value for the Payment Method column
    nome (str): Name to match in the Name column
    last_index (int): Last used Original_Index value
    
    Returns:
    pandas.DataFrame: DataFrame with the new row added
    """
    # Find the first row matching the name
    template_row = df[df['Name'] == nome].iloc[0].copy()
    
    # Modify the specific columns
    template_row['Total'] = diff
    template_row['Payment Method'] = payment
    template_row['original_index'] = last_index + 1
    
    # Add the new row to the dataframe
    return pd.concat([df, pd.DataFrame([template_row])], ignore_index=True)


def update_df(df, new_value, nome, pagamenti = None):
    print("Entering update_df")  # Debug print to indicate the function is called
    
    colonne_solo_idx = ["Total", 'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price',]   

    # Get all row indices from new_value
    row_indices = list(new_value.keys())
    if not row_indices:
        return
    
    # Get the minimum index
    first_index = min(row_indices)
    
    # For each row index and its data
    for row_idx, row_data in new_value.items():
        # Update each column's value
        for column, value in row_data['values'].items():
            print(f"Row {row_idx}: Column '{column}' = '{value}'")
            if column in colonne_solo_idx:
                df.loc[row_idx, column] = value  # Update at the specific row index
                print(f"Updated index {row_idx}: {df.loc[row_idx]}")
            else:
                name_mask = df["Name"] == nome
                df.loc[name_mask, column] = value
                print(f"Updated {column}: {value}")
    
    # Check Payment Method for Gift Card + after all updates
    original_method = df.loc[first_index, "Payment Method"]
    # Check if it's a string before trying string operations
    if isinstance(original_method, str):
        if "Gift Card" in original_method and "+" in original_method:
            cleaned_method = original_method.replace("Gift Card", "").replace("+", "").strip()
            name_mask = df["Name"] == nome
            df.loc[name_mask, "Payment Method"] = cleaned_method
            print(f"Updated Payment Method: {cleaned_method}")

    return df, pagamenti
    
    
    
        
#             valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]

#             if valid_indices:  # Check if there are any valid indices
#                 first_valid_index = valid_indices[0]  # Get the first valid index
#                 df.loc[first_valid_index, "Total"] = new_value  # Update Total at that index
#                 print(f"Updated index {first_valid_index}: {df.loc[first_valid_index]}")

#                 # Clean and set the Payment Method for all rows in 'index'
#                 if nota == "Gift Card":
#                     original_method = df.loc[first_valid_index, "Payment Method"]
#                     cleaned_method = original_method.replace("Gift Card", "").replace("+", "").strip()
#                     df.loc[index, "Payment Method"] = cleaned_method
#                     print(f"Updated Payment Method for indices {index}: {cleaned_method}")
#             else:
#                 print("No valid index found where 'Total' is not NaN.")

#     elif nota == "Reso dubbio":
#         print("Processing Reso dubbio")

#         # Check if index and new_value have the same length
#         if len(index) != len(new_value):
#             raise ValueError("Index list and new value list must have the same length.")

#         # Update the DataFrame with the new quantities based on the provided indexes
#         gioielli_total = 0
#         for idx, new_quantity in zip(index, new_value):
#             initial_quantity = df.loc[idx, 'Lineitem quantity']
#             initial_price = df.loc[idx, 'Lineitem price']

#             if initial_price > 10:
#                 gioielli_total += initial_price * initial_quantity
#                 print(gioielli_total)

#             df.loc[idx, 'Lineitem quantity'] = new_quantity
#             print(f"Updated Lineitem quantity at index {idx} to {new_quantity}")  # Debug print

#         # Calculate the total
#         new_total = 0
#         new_gioielli_total = 0

#         # Ensure there are indices to avoid IndexError
#         if index:  # Check if index is not empty
#             # Filter the indices where Total is not NaN
#             valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]
        
#             if valid_indices:  # Check if there are any valid indices
#                 first_row = min(valid_indices)  # Get the first valid index

#                 # Sum total for all line items with the same "Name"
#                 for idx in index:
#                     print(idx)
#                     row = df.iloc[idx]
#                     print(row['Lineitem quantity'], row['Lineitem price'])
#                     new_total += row['Lineitem quantity'] * row['Lineitem price']
#                     print(new_total)

#                     if  row['Lineitem price'] > 10:
#                         new_gioielli_total +=  row['Lineitem price'] * row['Lineitem quantity']
#                         print(new_gioielli_total)

#                 # Adding Shipping and subtracting Discount from the first row
#                 shipping = df.loc[first_row, 'Shipping'] if pd.notna(df.loc[first_row, 'Shipping']) else 0
#                 discount = df.loc[first_row, 'Discount Amount'] if pd.notna(df.loc[first_row, 'Discount Amount']) else 0
#                 discount_rate =  discount / gioielli_total
                                
#                 new_total = new_total - (new_gioielli_total * discount_rate) + shipping
#                 print(discount_rate, new_total)

#                 # Compare the new total with "Importo Pagato"
#                 importo_pagato = df.loc[first_row, 'Importo Pagato'] if pd.notna(df.loc[first_row, 'Importo Pagato']) else 0
                
#                 if new_total != importo_pagato:                
#                     raise ValueError(f"Controllare le quantità, l'importo pagato {importo_pagato} non corrisponde con il totale calcolato {new_total}")
#                 else:
#                     df.loc[first_row, 'Total'] = new_total
#                     df.loc[index, 'Discount Amount'] = (new_gioielli_total * discount_rate)


#     elif nota == "Pagamento non trovato":
#         print("Processing Pagamento non trovato")

#         if index:  # Check if index is not empty
#             # Filter the indices where Total is not NaN
#             valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]

#             if valid_indices:  # Check if there are any valid indices
#                 first_valid_index = valid_indices[0]  # Get the first valid index
#                 df.loc[first_valid_index, "Total"] = new_value  # Update Total at that index
#                 print(f"Updated index {first_valid_index}: {df.loc[first_valid_index]}")

#             else:
#                 print("No valid index found where 'Total' is not NaN.")
#     # Always return both DataFrames
#     return df, pagamenti












# def update_df(df, index, new_value, nota, pagamenti = None):
#     print("Entering update_df")  # Debug print to indicate the function is called
    
#     if pagamenti is not None:
        
#         if new_value[0] is not None:
#             brand = "LIL Milan" if int(new_value[0]) > 30000 else "AGEE"
#             new_row = {
#                 "Name": "#" + str(new_value[0]),
#                 "Total": pagamenti.loc[index, "Importo Pagato"],
#                 "Paid at": pagamenti.loc[index, "Data"],
#                 "Shipping Country": new_value[2].strip(),
#                 "Location": str(new_value[1]),
#                 "Payment Method": pagamenti.loc[index, "Metodo"],
#                 "Brand": brand,
#                 "CHECK": "VERO"
#             }
#             df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
#             pagamenti.loc[index, "Brand"] = brand
#             print("New row added:", new_row)
        
#         else:
#             print(f"Dropping row at index {index}")
#             pagamenti.drop(index, inplace=True)
            
#     # Handle df updates based on nota
#     if nota == "Gift Card" or nota == "Gift Card only":
#         print("Processing Gift Card or Gift Card only")
#         if index:  # Check if index is not empty
#             # Filter the indices where Total is not NaN
#             valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]

#             if valid_indices:  # Check if there are any valid indices
#                 first_valid_index = valid_indices[0]  # Get the first valid index
#                 df.loc[first_valid_index, "Total"] = new_value  # Update Total at that index
#                 print(f"Updated index {first_valid_index}: {df.loc[first_valid_index]}")

#                 # Clean and set the Payment Method for all rows in 'index'
#                 if nota == "Gift Card":
#                     original_method = df.loc[first_valid_index, "Payment Method"]
#                     cleaned_method = original_method.replace("Gift Card", "").replace("+", "").strip()
#                     df.loc[index, "Payment Method"] = cleaned_method
#                     print(f"Updated Payment Method for indices {index}: {cleaned_method}")
#             else:
#                 print("No valid index found where 'Total' is not NaN.")

#     elif nota == "Reso dubbio":
#         print("Processing Reso dubbio")

#         # Check if index and new_value have the same length
#         if len(index) != len(new_value):
#             raise ValueError("Index list and new value list must have the same length.")

#         # Update the DataFrame with the new quantities based on the provided indexes
#         gioielli_total = 0
#         for idx, new_quantity in zip(index, new_value):
#             initial_quantity = df.loc[idx, 'Lineitem quantity']
#             initial_price = df.loc[idx, 'Lineitem price']

#             if initial_price > 10:
#                 gioielli_total += initial_price * initial_quantity
#                 print(gioielli_total)

#             df.loc[idx, 'Lineitem quantity'] = new_quantity
#             print(f"Updated Lineitem quantity at index {idx} to {new_quantity}")  # Debug print

#         # Calculate the total
#         new_total = 0
#         new_gioielli_total = 0

#         # Ensure there are indices to avoid IndexError
#         if index:  # Check if index is not empty
#             # Filter the indices where Total is not NaN
#             valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]
        
#             if valid_indices:  # Check if there are any valid indices
#                 first_row = min(valid_indices)  # Get the first valid index

#                 # Sum total for all line items with the same "Name"
#                 for idx in index:
#                     print(idx)
#                     row = df.iloc[idx]
#                     print(row['Lineitem quantity'], row['Lineitem price'])
#                     new_total += row['Lineitem quantity'] * row['Lineitem price']
#                     print(new_total)

#                     if  row['Lineitem price'] > 10:
#                         new_gioielli_total +=  row['Lineitem price'] * row['Lineitem quantity']
#                         print(new_gioielli_total)

#                 # Adding Shipping and subtracting Discount from the first row
#                 shipping = df.loc[first_row, 'Shipping'] if pd.notna(df.loc[first_row, 'Shipping']) else 0
#                 discount = df.loc[first_row, 'Discount Amount'] if pd.notna(df.loc[first_row, 'Discount Amount']) else 0
#                 discount_rate =  discount / gioielli_total
                                
#                 new_total = new_total - (new_gioielli_total * discount_rate) + shipping
#                 print(discount_rate, new_total)

#                 # Compare the new total with "Importo Pagato"
#                 importo_pagato = df.loc[first_row, 'Importo Pagato'] if pd.notna(df.loc[first_row, 'Importo Pagato']) else 0
                
#                 if new_total != importo_pagato:                
#                     raise ValueError(f"Controllare le quantità, l'importo pagato {importo_pagato} non corrisponde con il totale calcolato {new_total}")
#                 else:
#                     df.loc[first_row, 'Total'] = new_total
#                     df.loc[index, 'Discount Amount'] = (new_gioielli_total * discount_rate)


#     elif nota == "Pagamento non trovato":
#         print("Processing Pagamento non trovato")

#         if index:  # Check if index is not empty
#             # Filter the indices where Total is not NaN
#             valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]

#             if valid_indices:  # Check if there are any valid indices
#                 first_valid_index = valid_indices[0]  # Get the first valid index
#                 df.loc[first_valid_index, "Total"] = new_value  # Update Total at that index
#                 print(f"Updated index {first_valid_index}: {df.loc[first_valid_index]}")

#             else:
#                 print("No valid index found where 'Total' is not NaN.")
#     # Always return both DataFrames
#     return df, pagamenti








