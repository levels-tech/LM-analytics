#FILE CON FUNZIONI CHIAMATE DIRETTAMENTE DA STREAMLIT

import streamlit as st
import pandas as pd

from model.scripts.ordini import Ordini
from model.scripts.runner import MatcherRunner

from model.matchers.matcher_bonifico import BonificoMatcher
from model.matchers.matcher_qromo import QromoMatcher
from model.matchers.matcher_paypal import PaypalMatcher
from model.matchers.matcher_satispay import SatispayMatcher
from model.matchers.matcher_scalapay import ScalapayMatcher
from model.matchers.matcher_shopify import ShopifyMatcher

from model.utils.exceptions import DateMismatchError
from model.utils.functions import reformat_date, find_header_row

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

    st.session_state.df_columns = df_columns

    try:
        #run matchers
        shopify_matcher = ShopifyMatcher(file_p, df_ordini=ordini)
        scalapay_matcher = ScalapayMatcher(file_p, df_ordini=ordini)
        paypal_matcher = PaypalMatcher(file_p, df_ordini=ordini)
        qromo_matcher = QromoMatcher(file_p, df_ordini=ordini)
        satispay_matcher = SatispayMatcher(file_p, df_ordini=ordini)
        bonifico_matcher = BonificoMatcher(file_p, df_ordini=ordini)

        # Create the matchers list
        matchers = [
            shopify_matcher,
            scalapay_matcher,
            qromo_matcher,
            satispay_matcher,
            paypal_matcher,
            bonifico_matcher
        ]

        runner = MatcherRunner(matchers, ordini)
        print("Runner created")
        
        result, pagamenti, pagamenti_columns = runner.run_all_matchers(mese, anno)
        st.session_state.pagamenti_columns = pagamenti_columns

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
    template_row['Lineitem quantity'] = 0
    template_row['original_index'] = last_index + 1
    
    # Add the new row to the dataframe
    return pd.concat([df, pd.DataFrame([template_row])], ignore_index=True)


def aggiungi_pagamenti(df, nuovi):
    print("Entering aggiungi pagamenti")  # Debug print to indicate the function is called
    
    for numero in nuovi.keys():
        df.loc[df["Numero Pagamento"] == numero, "CHECK"] = "VERO"

    # df = df.drop_duplicates(subset = ["Numero Pagamento"])
    
    df.loc[(df["CHECK"] == "FALSO"), "CHECK"] = "NON TROVATO"

    # df.to_excel("pagamenti.xlsx")
  
    return df


def update_df(df, new_value, nome, pagamenti = None):
    print("Entering update_df")  # Debug print to indicate the function is called
    
    colonne_solo_idx = ["Total", 'Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price',]   

    if pagamenti is None:
        # Get all row indices from new_value
        row_indices = list(new_value.keys())
        if not row_indices:
            return
        
        # Get the minimum index
        first_index = min(row_indices)
        
        name_mask = df["Name"] == nome
        # df.loc[name_mask, "CHECK"] = "VERO"  # Update at the specific row index

        # For each row index and its data
        for row_idx, row_data in new_value.items():
            # Update each column's value
            for column, value in row_data['values'].items():
                print(f"Row {row_idx}: Column '{column}' = '{value}'")
                if column in colonne_solo_idx:
                    df.loc[row_idx, column] = value  # Update at the specific row index
                    print(f"Updated index {row_idx}: {df.loc[row_idx]}")
                else:
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

    else:

        if new_value is None or (isinstance(new_value, list) and all(x is None for x in new_value)):
            print(f"Dropping row at index {nome}")
            pagamenti.drop(nome, inplace=True)
        
        else:

            new_rows = []

            name = new_value[0]
            data = new_value[1]
            totale = new_value[2]
            skus = new_value[3]
            quantities = new_value[4]
            items_name = new_value[5]
            country = new_value[6]
            metodo = new_value[7]
            location = new_value[8]
            brand = new_value[9]

            if name in df["Name"].unique(): #esiste già lo stesso ordine

                rows_esistenti = df[df["Name"] == name] 
            
                # data_pagamenti = rows_esistenti["Paid at"].values[0]
                totale_pagamenti = rows_esistenti["Total"].values[0]
                skus_pagamenti = rows_esistenti["Lineitem sku"].tolist()
                quantities_pagamenti = rows_esistenti["Lineitem quantity"].tolist()
                # country_pagamenti = rows_esistenti["Shipping Country"].values[0]
                metodo_pagamenti = rows_esistenti["Payment Method"].values[0]
                # location_pagamenti = rows_esistenti["Location"].values[0]
                brand_pagamenti = rows_esistenti["Brand"].values[0]

                if metodo == metodo_pagamenti:  
                   # Get the indices of existing rows
                    existing_indices = df[df["Name"] == name].index
                    df.loc[existing_indices[0], "Total"] = float(totale_pagamenti) + float(totale)

                    # Handle matching SKUs
                    matched_skus = set()
                    for i, sku in enumerate(skus):
                        matching_positions = [j for j, s_p in enumerate(skus_pagamenti) if str(s_p) == str(sku)]
                        
                        if matching_positions:
                            matched_skus.add(sku)
                            for pos in matching_positions:
                                if float(quantities_pagamenti[pos]) == 0:
                                    df.loc[existing_indices[pos], "Lineitem quantity"] = int(quantities[i])
                                    break

                    # Add new rows for unmatched SKUs
                    for i, sku in enumerate(skus):
                        if sku not in matched_skus:
                            new_row = {
                                "Name": str(name),
                                "Paid at": str(data),
                                "Total": float('nan'),
                                "Lineitem quantity": int(quantities[i]),
                                "Lineitem name": str(items_name[i]),
                                "Lineitem sku": str(sku),
                                "Shipping Country": str(country).strip(),
                                "Location": str(location),
                                "Payment Method": str(metodo),
                                "Brand": "Ordini " + str(brand_pagamenti),
                                "CHECK": "VERO",
                            }
                            new_rows.append(new_row)
                        
                        if new_rows:
                            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True) 
                            pagamenti.loc[nome, "Brand"] = "Ordini "+str(brand)

                else:
                    # Different payment method - create new rows based on SKU matching
                    first_row = True
                    
                    for i, sku in enumerate(skus):
                        matching_positions = [j for j, s_p in enumerate(skus_pagamenti) if str(s_p) == str(sku)]
                        
                        if matching_positions:
                            for pos in matching_positions:
                                new_quantity = 0 if float(quantities_pagamenti[pos]) != 0 else int(quantities[i])
                                
                                new_row = {
                                    "Name": str(name),
                                    "Paid at": str(data),
                                    "Total": float(totale) if first_row else float('nan'),
                                    "Lineitem name": str(items_name[i]),
                                    "Lineitem quantity": new_quantity,
                                    "Lineitem sku": str(sku),
                                    "Shipping Country": str(country).strip(),
                                    "Location": str(location),
                                    "Payment Method": str(metodo),
                                    "Brand": "Ordini " + str(brand_pagamenti),
                                    "CHECK": "VERO",
                                }
                                new_rows.append(new_row)
                                first_row = False
                                break
                    
                    if new_rows:
                        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True) 
                        pagamenti.loc[nome, "Brand"] = "Ordini "+str(brand)

            else: #non esiste già lo stesso ordine
                st.write(len(skus))
                for i in range(len(skus)):
                    new_row = {
                        "Name": str(name),
                        "Paid at": str(data),
                        "Total": float(totale) if i == 0 else float('nan'), 
                        "Lineitem name": str(items_name[i]),
                        "Lineitem quantity": int(quantities[i]),
                        "Lineitem sku": str(skus[i]),
                        "Shipping Country": str(country).strip(),
                        "Location": str(location),
                        "Payment Method": str(metodo),
                        "Brand": "Ordini "+str(brand),
                        "CHECK": "VERO",
                    }
                    new_rows.append(new_row)
                
                # st.write(pd.DataFrame(new_rows))
                    
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True) 
                # st.write(pd.DataFrame(df[df["Name"] == name]))
                pagamenti.loc[nome, "Brand"] = "Ordini "+str(brand)
                print("New row added:", new_rows)          

    return df, pagamenti
    