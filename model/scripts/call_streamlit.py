#FILE CON FUNZIONI CHIAMATE DIRETTAMENTE DA STREAMLIT

import streamlit as st
import pandas as pd

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


#####################################################################################

# CONTROLLA LE DATE DEI FILE DI INPUT

def check_files(file, name, mese, anno):
    """
    Verifies that a given file contains data corresponding to a specified month and year.

    Parameters:
    - file (dict): A dictionary where the key is the file name, and the value is another dictionary 
                   containing the actual file object under the key 'file'.
    - name (str): The name of the file type (e.g., "Ordini LIL", "Bonifici"), used to determine the column 
                  containing date information.
    - mese (int): The month of interest, specified as an integer (e.g., 1 for January, 12 for December).
    - anno (int): The year of interest, specified as a four-digit integer (e.g., 2025).

    Returns:
    - bool: Returns True if the file contains data for the specified month and year. 
            Raises a DateMismatchError if no data is found.

    Raises:
    - DateMismatchError: If the file does not contain data for the specified month and year.
    """

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
        

#####################################################################################

# PREPROCESS DI ORDINI, PAGAMENTI E MATCH
     
def run(file_o, file_p, mese, anno):
    """
    Processes orders and payments for a given month and year, and it matches them.
    
    Parameters:
        file_o (file): The input file containing order data.
        file_p (file): The input file containing payment data.
        mese (int): The month of interest (e.g., 1 for January).
        anno (int): The year of interest (e.g., 2025).
    
    Returns:
        tuple: A tuple containing:
            - result: The updated ordini file.
            - pagamenti: The updated payment file (with status of match).
    
    Raises:
        Exception: If any error occurs during the matching process.
    """
    
    #ordini
    ordini_processor = Ordini(file_o, mese=mese, anno=anno)
    ordini, df_columns = ordini_processor.preprocess() 

    st.session_state.df_columns = df_columns

    try:
        #run matchers
        shopify_matcher = ShopifyMatcher(file_p, df_ordini=ordini)
        scalapay_matcher = ScalapayMatcher(file_p, df_ordini=ordini)
        paypal_matcher = PaypalMatcher(file_p, df_ordini=ordini)
        qromo_matcher = QromoMatcher(file_p, df_ordini=ordini)
        satispay_matcher = SatispayMatcher(file_p, df_ordini=ordini)
        bonifico_matcher = BonificoMatcher(file_p, df_ordini=ordini)
        cash_matcher = CashMatcher(file_p, df_ordini=ordini)

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
        
        result, pagamenti, pagamenti_columns = runner.run_all_matchers(mese, anno)
        st.session_state.pagamenti_columns = pagamenti_columns

        return result, pagamenti
    
    except Exception as e:
        print(f"Error in run: {str(e)}")
        raise e


#####################################################################################

# CONTROLLA SE CI SONO MISSING FIELDS E DI CHE TIPO SONO

def missing_fields(df, nome, exclude):
    """
    Identifies missing or problematic fields.

    Parameters:
        df (DataFrame): The input DataFrame containing data to check.
        nome (str): The name to filter the DataFrame by, using the "Name" column.
        exclude (list): A list of substrings to exclude from checks for the "Lineitem sku" column.

    Returns:
        tuple: A tuple containing two lists:
            - to_check: A list of column names where data is missing or requires verification.
            - to_change: A list of column names where data may need correction.

    Notes:
        - This function is designed to handle checks on specific columns like "Paid at", 
          "Shipping Country", "Location", "Payment Method", and "Lineitem sku".
        - The `exclude` parameter is used to ignore rows with specific patterns in the "Lineitem name" column 
          when checking for missing values in "Lineitem sku".
    """
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
    if filtered_df["Payment Method"].str.contains(r'\+').all() & (~filtered_df["Payment Method"].str.contains("Gift Card").all()):
        to_change.append("Payment Method")
    if filtered_df["Payment Method"].str.count(r'\+').ge(2).all():
        to_change.append("Payment Method")
    if filtered_df["Lineitem sku"].isna().any():
        rows_with_nan_sku = filtered_df[filtered_df["Lineitem sku"].isna()]
        if ~rows_with_nan_sku['Lineitem name'].str.contains('|'.join(exclude), case=False, na=False).all():
            to_check.append("Lineitem sku")
     
    return to_check, to_change


#####################################################################################

# AGGIUNGI UNA RIGA AL DATAFRAME DI ORDINI

def add_row(df, diff, payment, nome, last_index):
    """
    Add a new row to the dataframe based on an existing row for a given name.
    
    Parameters:
        df (pandas.DataFrame): Input dataframe
        diff (list): New value(s) for the Total column
        payment (list): New value(s) for the Payment Method column
        nome (str): Name to match in the Name column
        last_index (int): Last used Original_Index value in the dataframe
    
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


#####################################################################################

# AGGIUNGI UNA RIGA AL DATAFRAME DI ORDINI

def aggiungi_pagamenti(df, nuovi_lil, nuovi_agee):
    """
    Updates the status of the match of payments.

    Parameters:
        df (DataFrame): The DataFrame containing payment data with columns "Numero Pagamento" and "CHECK."
        nuovi_lil (dict): A dictionary of newly matched payments for "Ordini LIL" with payment numbers as keys.
        nuovi_agee (dict): A dictionary of newly matched payments for "Ordini AGEE" with payment numbers as keys.

    Returns:
        DataFrame: The updated DataFrame with the following changes:
            - Rows matching `nuovi_lil` have "CHECK" set to "VERO" and "Brand" set to "Ordini LIL."
            - Rows matching `nuovi_agee` have "CHECK" set to "VERO" and "Brand" set to "Ordini AGEE."
            - Rows where "CHECK" remains "FALSO" are updated to "NON TROVATO."
    """
    
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



#####################################################################################

# AGGIORNA SIA IL DF DI ORDINI SIA IL DF DI PAGAMENTI (QUANDO NECESSARIO) DOPO OGNI CONTROLLO DELL'UTENTE

def update_df(df, new_value, nome, pagamenti = None):

    """
    Updates the order and payament (if needed) DataFrames based on the information provided.

    Parameters:
        df (pd.DataFrame): The orders DataFrame to update.
        new_value (dict or list): 
            - When `pagamenti` is None: A dictionary where keys are row indices, and values are dictionaries 
              specifying column-value pairs to update for those rows.
            - When `pagamenti` is provided: A list with specific information to add or update rows.
        nome (int or str): Identifier for the row(s) or order being updated in `df`.
        pagamenti (pd.DataFrame, optional): 
            payment DataFrame to update. Default is None.

    Returns:
        tuple:
            - pd.DataFrame: The updated primary DataFrame (`df`).
            - pd.DataFrame or None: The updated `pagamenti` DataFrame if it was provided, or None otherwise.

    Notes:
        - If `pagamenti` is None, the function focuses on updating specific rows and columns in `df`.
        - If `pagamenti` is provided, it handles more complex operations, such as adding new rows based on 
          `new_value` or dropping rows identified by `nome`.
    """
   
    #se bisogna aggiornare solo ordini: no pagamenti

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
                if column in colonne_solo_idx:
                    df.loc[row_idx, column] = value  # Update at the specific row index
                elif column == "Total":
                    df.loc[first_index, column] = value
                else:
                    df.loc[name_mask, column] = value
                
        # Check Payment Method for Gift Card + after all updates
        original_method = df.loc[first_index, "Payment Method"]
        if isinstance(original_method, str):
            if "Gift Card" in original_method and "+" in original_method:
                cleaned_method = original_method.replace("Gift Card", "").replace("+", "").strip()
                name_mask = df["Name"] == nome
                df.loc[name_mask, "Payment Method"] = cleaned_method

    #se bisogna aggiornare sia ordini sia pagamenti
    
    else:

        #se il pagamento non è da includere
        if new_value is None or (isinstance(new_value, list) and all(x is None for x in new_value)):
            pagamenti.drop(nome, inplace=True)
        
        #se il pagamento è da includere
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
            
                totale_ordine = rows_esistenti["Total"].values[0]
                skus_ordine = rows_esistenti["Lineitem sku"].tolist()
                quantities_ordine = rows_esistenti["Lineitem quantity"].tolist()
                metodo_ordine = rows_esistenti["Payment Method"].values[0]
                refund_ordine = rows_esistenti["Refunded Amount"].values[0]
                brand_ordine = rows_esistenti["Brand"].values[0]

                if metodo == metodo_ordine:  #il metodo di pagamento aggiunto è uguale a quello esistente
                    existing_indices = df[df["Name"] == name].index

                    df.loc[existing_indices[0], "Total"] = float(totale_ordine) + float(totale)

                    pagamenti.loc[pagamenti["original_index"] == nome, "Brand"] = "Ordini "+str(brand)
                    pagamenti.loc[pagamenti["original_index"] == nome, "CHECK"] = "VERO"
                    pagamenti.loc[pagamenti["original_index"] == nome, "Name"] = str(name)

                    #SKUs che già esistono nell'ordine
                    matched_skus = set()
                    for i, sku in enumerate(skus):
                        matching_positions = [j for j, s_p in enumerate(skus_ordine) if str(s_p) == str(sku)]
                        
                        if matching_positions:
                            matched_skus.add(sku)
                            for pos in matching_positions:
                                if refund != 0:
                                    df.loc[existing_indices[pos], "Refunded Amount"] = refund_ordine + refund
                                if float(quantities_ordine[pos]) == 0:
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
                                "Brand": str(brand_ordine),
                                "CHECK": "VERO",
                            }
                            new_rows.append(new_row)
                        
                        if new_rows:
                            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True) 
                        
                else: #metodo di pagamento aggiunto è diverso da quello dell'ordine - create new rows 
                    first_row = True

                    pagamenti.loc[pagamenti["original_index"] == nome, "Brand"] = "Ordini "+str(brand)
                    pagamenti.loc[pagamenti["original_index"] == nome, "CHECK"] = "VERO"
                    pagamenti.loc[pagamenti["original_index"] == nome, "Name"] = str(name)
                    
                    for i, sku in enumerate(skus):
                        matching_positions = [j for j, s_p in enumerate(skus_ordine) if str(s_p) == str(sku)]
                        
                        if matching_positions: #se lo sku è già presente nell'ordine
                            for pos in matching_positions:
                                new_quantity = 0 if float(quantities_ordine[pos]) != 0 else int(quantities[i])
                                
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
                                    "Brand": "Ordini " + str(brand_ordine),
                                    "CHECK": "VERO",
                                }
                                new_rows.append(new_row)
                                first_row = False
                                break
                        
                        else:  # se lo sku non è già presente nell'ordine
                            new_row = {
                                "Name": str(name),
                                "Paid at": str(data),
                                "Total": float(totale) if first_row else float('nan'),
                                "Lineitem name": str(items_name[i]),
                                "Lineitem quantity": int(quantities[i]),
                                "Lineitem sku": str(sku),
                                "Shipping Country": str(country).strip(),
                                "Refunded Amount": float(refund),
                                "Location": str(location),
                                "Payment Method": str(metodo),
                                "Brand": "Ordini " + str(brand_ordine),
                                "CHECK": "VERO",
                            }
                            new_rows.append(new_row)
                            first_row = False

                    if new_rows:
                        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

            
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
                pagamenti.loc[nome, "CHECK"] = "VERO"
                pagamenti.loc[nome, "Name"] = str(name)         

    return df, pagamenti



####################################################################################

# GENERA L'EXCEL
 
def generate_excel(df_ordini_all, pag, filename):

    """
    Generates an Excel file summarizing order and payment data.

    Parameters:
    - df_ordini_all (DataFrame): A DataFrame containing all order data to be summarized.
    - pp (DataFrame): A DataFrame containing all payments summarized.
    - filename (str): The name of the output Excel file to be generated.

    Returns:
    - filename (str): The name of the generated Excel file.

    Description:
    This function uses the OrderSummary class to create Excel files that summarize the input order data 
    based on the provided parameters. It creates and saves the file under the specified filename.
    """

    order_summary = OrderSummary(df_ordini_all, pag, filename)
    order_summary.create_files()
    
    return filename