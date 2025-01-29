#FILE CON FUNZIONI CHIAMATE DIRETTAMENTE DA STREAMLIT

import streamlit as st
import pandas as pd
import csv

from model.scripts.ordini import Ordini
from model.scripts.runner import MatcherRunner
from model.scripts.summary_excel import OrderSummary 

from model.matchers.matcher_bonifico import BonificoMatcher
from model.matchers.matcher_cash import CashMatcher
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

    expected_date = f"{anno}-{mese:02d}"  #f"{anno}-{str(mese).zfill(2)}"
    f_file = file.get(name, {}).get("file")
    
    if f_file: 
        if name == "Bonifici":
            f = find_header_row(f_file, "Importo")
        else:
            # Detect the delimiter
            try:
                f_file.seek(0)  # Reset file pointer
                f = pd.read_csv(f_file, delimiter=",", dtype={date_column[name]: "string"})
            except:
                f_file.seek(0)  # Reset file pointer again
                f = pd.read_csv(f_file, delimiter=";", dtype={date_column[name]: "string"})
        
        f[date_column[name]] = f[date_column[name]].apply(reformat_date)
        f_filtered = f[f[date_column[name]].str[:7] == expected_date].copy()
        if len(f_filtered) == 0:
            try:
                found_dates = sorted(f[date_column[name]].str[:7].unique())
                raise DateMismatchError(
                    message=f"Nel file di {name} non sono stati trovati dati per il periodo {expected_date}",
                    details=(f"Date disponibili nel file: {', '.join(found_dates)}\n"
                            "Selezionare un periodo presente nel file o caricare un file del periodo corretto."))
            except:
                raise DateMismatchError(
                    message=f"Nel file di {name} non sono stati trovati dati per il periodo {expected_date}",
                    details=(f"Selezionare un periodo presente nel file o caricare un file del periodo corretto."))
            # return False
        else:
            return True
        
    
        
def run(order_files, payment_files, month, year):
    #ordini
    print("ordini iniziati")
    ordini_processor = Ordini(order_files, mese=month, anno=year)
    ordini, df_columns = ordini_processor.preprocess() 
    print("ordini finiti")

    st.session_state.df_columns = df_columns

    try:
        #run matchers
        shopify_matcher = ShopifyMatcher(payment_files, df_ordini=ordini)
        scalapay_matcher = ScalapayMatcher(payment_files, df_ordini=ordini)
        paypal_matcher = PaypalMatcher(payment_files, df_ordini=ordini)
        qromo_matcher = QromoMatcher(payment_files, df_ordini=ordini)
        satispay_matcher = SatispayMatcher(payment_files, df_ordini=ordini)
        bonifico_matcher = BonificoMatcher(payment_files, df_ordini=ordini)
        cash_matcher = CashMatcher(payment_files, df_ordini=ordini)

        # Create the matchers list
        matchers = [
            shopify_matcher,
            scalapay_matcher,
            qromo_matcher,
            satispay_matcher,
            paypal_matcher,
            bonifico_matcher,
            cash_matcher
        ]

        runner = MatcherRunner(matchers, ordini)
        print("Runner created")
        
        result, pagamenti, pagamenti_columns = runner.run_all_matchers(month, year)
        # st.session_state.pagamenti_columns = pagamenti_columns

        return result, pagamenti
    
    except Exception as e:
        print(f"Error in run: {str(e)}")
        raise e


## Controlla che "Paid at", "Shipping Country", "Location" e "Lineitem sku" non siano NaN
## Controlla che "Payment Method" non contenga "+" 
def missing_fields(df, nome, exclude):
    to_check = []
    to_change = []
    filtered_df = df[df["Name"] == nome]
    
    # Check for NaN values in specific columns
    if filtered_df["Paid at"].isna().all():
        to_check.append("Paid at")
    if filtered_df["Shipping Country"].isna().all():
        to_check.append("Shipping Country")
    if filtered_df["Location"].isna().all():
        to_check.append("Location")

    # Check for "+" in Payment Method if it's not a Gift Card
    if filtered_df["Payment Method"].str.contains(r'\+').all() & (~filtered_df["Payment Method"].str.contains("Gift Card").all()):
        to_change.append("Payment Method")

    # Check for Payment Method containing multiple "+" signs
    if filtered_df["Payment Method"].str.count(r'\+').ge(2).all():
        to_change.append("Payment Method")
    
    # Check for NaN values in "Lineitem sku" if the item is not among the excluded items 
    if filtered_df["Lineitem sku"].isna().any():
        rows_with_nan_sku = filtered_df[filtered_df["Lineitem sku"].isna()]
        if ~rows_with_nan_sku['Lineitem name'].str.contains('|'.join(exclude), case=False, na=False).all():
            to_check.append("Lineitem sku")
     
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
    
    index = template_row["original_index"]
    original_method = template_row["Payment Method"]
    original_total = template_row["Total"]
    original_refund = template_row["Refunded Amount"]

    # Handle cases when payment and diff are lists
    if len(payment) > 1 and len(diff) > 1:
        # Create one row for each combination of payment and diff
        for pay, d in zip(payment, diff):
            if pay == original_method:
                df.loc[df['original_index'] == index, "Total"] = original_total + d
                if d < 0:
                    df.loc[df['original_index'] == index, "Refunded Amount"] = original_refund + abs(d)
            else:
                new_row = template_row.copy()
                new_row['Total'] = d
                new_row['Payment Method'] = pay
                new_row['Lineitem quantity'] = 0
                new_row['original_index'] = last_index + 1
                if d < 0:
                    new_row['Refunded Amount'] = abs(d)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                last_index += 1

    # Handle cases when diff is a list
    elif len(diff) > 1 and len(payment) == 1:
        # Sum diff elements and create one row
        if payment[0] == original_method:
            df.loc[df['original_index'] == index, "Total"] = original_total + sum(diff)
            if (diff < 0).any():  # Check if any value in diff is negative
                df.loc[df['original_index'] == index, "Refunded Amount"] = original_refund + abs(diff[diff < 0].sum())
        else:
            total_diff = sum(diff)
            template_row['Total'] = total_diff
            template_row['Payment Method'] = payment[0]  # Payment is a single value
            template_row['Lineitem quantity'] = 0
            template_row['original_index'] = last_index + 1
            if (diff < 0).any():  # Check if any value in diff is negative
                template_row["Refunded Amount"] = original_refund + abs(diff[diff < 0].sum())
            df = pd.concat([df, pd.DataFrame([template_row])], ignore_index=True)
            
    elif len(diff) == 1 and len(payment) == 1:
        # Both payment and diff are single values
        if payment[0] == original_method:
            # Locate the first row of the subset where 'Name' matches 'nome'
            df.loc[df['original_index'] == index, "Total"] = original_total + diff[0]
            if diff[0] < 0:  # Check if any value in diff is negative
                df.loc[df['original_index'] == index, "Refunded Amount"] = original_refund + abs(diff[0])
        else:
            template_row['Total'] = diff[0]
            template_row['Payment Method'] = payment[0]
            template_row['Lineitem quantity'] = 0
            template_row['original_index'] = last_index + 1
            if diff[0] < 0:  # Check if any value in diff is negative
                template_row["Refunded Amount"] = abs(diff[0])
            df = pd.concat([df, pd.DataFrame([template_row])], ignore_index=True)

    return df

def aggiungi_pagamenti(df, nuovi_lil, nuovi_agee):
    print("Entering aggiungi pagamenti")  # Debug print to indicate the function is called
    
    if nuovi_lil:
        for numero in nuovi_lil.keys():
            df.loc[df["Numero Pagamento"] == numero, "CHECK"] = "VERO"
            df.loc[df["Numero Pagamento"] == numero, "Brand"] = "Ordini LIL"

    if nuovi_agee:
        for numero in nuovi_agee.keys():
            df.loc[df["Numero Pagamento"] == numero, "CHECK"] = "VERO"
            df.loc[df["Numero Pagamento"] == numero, "Brand"] = "Ordini AGEE"
    
    df.loc[(df["CHECK"] == "FALSO"), "CHECK"] = "NON TROVATO"
  
    return df


def update_df(df, new_value, nome, pagamenti = None):
    print("Entering update_df")  # Debug print to indicate the function is called
    
    colonne_solo_idx = ['Lineitem quantity', 'Lineitem name', 'Lineitem price', 'Lineitem compare at price',]   

    if pagamenti is None:
        # Get all row indices from new_value
        row_indices = list(new_value.keys())
        if not row_indices:
            return
        
        # Get the minimum index
        first_index = min(row_indices)
        
        name_mask = df["Name"] == nome

        # For each row index and its data
        for row_idx, row_data in new_value.items():
            # Update each column's value
            for column, value in row_data['values'].items():
                print(f"Row {row_idx}: Column '{column}' = '{value}'")
                if column in colonne_solo_idx:
                    df.loc[row_idx, column] = value  # Update at the specific row index
                    print(f"Updated index {row_idx}: {df.loc[row_idx]}")
                elif column == "Total":
                    df.loc[first_index, column] = value
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
            refund = abs(totale) if totale < 0 else 0
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
                refund_pagamenti = rows_esistenti["Refunded Amount"].values[0]
                brand_pagamenti = rows_esistenti["Brand"].values[0]

                if metodo == metodo_pagamenti:  #il metodo di pagamento aggiunto è uguale a quello esistente
                    existing_indices = df[df["Name"] == name].index
                    df.loc[existing_indices[0], "Total"] = float(totale_pagamenti) + float(totale)
                    pagamenti.loc[pagamenti["original_index"] == nome, "Brand"] = "Ordini "+str(brand)

                    #SKUs che già esistono nell'ordine
                    matched_skus = set()
                    for i, sku in enumerate(skus):
                        matching_positions = [j for j, s_p in enumerate(skus_pagamenti) if str(s_p) == str(sku)]
                        
                        if matching_positions:
                            matched_skus.add(sku)
                            for pos in matching_positions:
                                if refund != 0:
                                    df.loc[existing_indices[pos], "Refunded Amount"] = refund_pagamenti + refund
                                if float(quantities_pagamenti[pos]) == 0:
                                    df.loc[existing_indices[pos], "Lineitem quantity"] = int(quantities[i])
                                    break

                    #SKUs che non esistono già nelll'ordine
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
                                "Refunded Amount": float(refund),
                                "Location": str(location),
                                "Payment Method": str(metodo),
                                "Brand": str(brand_pagamenti),
                                "CHECK": "VERO",
                            }
                            new_rows.append(new_row)
                        
                        if new_rows:
                            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True) 
                        
                else: #metodo di pagamento aggiunto è diverso da quello dell'ordine - create new rows based on SKU matching
                    first_row = True
                    pagamenti.loc[pagamenti["original_index"] == nome, "Brand"] = "Ordini "+str(brand)
                    
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
                                    "Refunded Amount": float(refund),
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
                        # pagamenti.loc[nome, "Brand"] = "Ordini "+str(brand)

            else: #non esiste già lo stesso ordine
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
                        "Refunded Amount": float(refund),
                        "Payment Method": str(metodo),
                        "Brand": "Ordini "+str(brand),
                        "CHECK": "VERO",
                    }
                    new_rows.append(new_row)
                    
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True) 
                pagamenti.loc[nome, "Brand"] = "Ordini "+str(brand)
                print("New row added:", new_rows)          

    return df, pagamenti
    
def generate_excel(df_ordini_all, pp, filename):
    order_summary = OrderSummary(df_ordini_all, pp, filename)
    order_summary.create_files()
    return filename