import pandas as pd

# Function to check and reformat
def reformat_date(date_str):
    if pd.notna(date_str):
        date_str = date_str.strip().replace("/", "-")[:10]
        # Check if the string starts the year
        if "-" in date_str[:4]: #"20-12-2024" returns True
            # Split and rearrange as "YYYY-MM-DD"
            return "-".join(date_str.split("-")[::-1])
    return date_str  # Return as-is if already starts with "202"




#function to skip useless rows in bonifici
def find_header_row(excel_file, column_name):

        df_sample = pd.read_excel(excel_file)  # Adjust number as needed
        header_row = 0

        dtype_dict = {"Data":str}

        # Find the row containing the known column name
        for idx, row in df_sample.iterrows():
            if column_name in row.values:
                header_row = idx + 1
                break

        df = pd.read_excel(excel_file, header=header_row, dtype=dtype_dict)
                
        return df


# PARTIALLY_REFUNDED handling
def check_partially_refunded(df_check, pagamenti=None):
    # Create mask for compare at price check
    
    resi = df_check[((df_check["Lineitem compare at price"] == 0) & (df_check["Lineitem price"] > 10))]["Name"].unique()
    resi_dubbi = df_check[(df_check["resi"] == "Dubbi")]["Name"].unique()

    if pagamenti is None:
        # Get names that meet conditions when pagamenti is None
        altro = df_check[((df_check["Outstanding Balance"] != 0) | (df_check["Refunded Amount"] != 0))
                         & (df_check["CHECK"] == "FALSO")
                         & (~df_check["Name"].isin(resi))]["Name"].unique()

        for name in altro:
            name_mask = df_check["Name"] == name
            
            if name_mask.any():
                amount = df_check.loc[name_mask, "Importo Pagato"].values[0] if not pd.isna(df_check.loc[name_mask, "Importo Pagato"].values[0]) else 0
                new_total = (df_check.loc[name_mask, "Subtotal"].values[0] + 
                            df_check.loc[name_mask, "Shipping"].values[0] - 
                            df_check.loc[name_mask, "Refunded Amount"].values[0] - 
                            df_check.loc[name_mask, "Outstanding Balance"].values[0])
                
                if abs(new_total - amount) <= 1 and new_total != 0:
                    df_check.loc[name_mask, "Total"] = amount
                    df_check.loc[name_mask, "CHECK"] = "VERO"
                
                elif abs(new_total - amount) <= 1 and new_total <= 1:
                    df_check.loc[name_mask, "Total"] = amount
                    df_check.loc[name_mask, "Lineitem quantity"] = 0
                    df_check.loc[name_mask, "CHECK"] = "VERO"
        
        return df_check, None

    else:
        # Get names that meet conditions when pagamenti is provided
        altro = df_check[(~df_check["Name"].isin(resi_dubbi))
                         & ((df_check["Outstanding Balance"] != 0) | (df_check["Refunded Amount"] != 0)) 
                         & ((df_check["CHECK"] == "FALSO") | (df_check["CHECK"] == "NON TROVATO") | (df_check["CHECK"] == "VALORE NAN"))]["Name"].unique()

        for name in altro:
            name_mask = df_check["Name"] == name
            
            if name_mask.any():
                amount = df_check.loc[name_mask, "Importo Pagato"].values[0] if not pd.isna(df_check.loc[name_mask, "Importo Pagato"].values[0]) else 0
                new_total = (df_check.loc[name_mask, "Subtotal"].values[0] + 
                            df_check.loc[name_mask, "Shipping"].values[0] - 
                            df_check.loc[name_mask, "Refunded Amount"].values[0] - 
                            df_check.loc[name_mask, "Outstanding Balance"].values[0])
                
                numero_pagamento = df_check.loc[name_mask, "Numero Pagamento"].values[0]
                numero_mask = pagamenti["Numero Pagamento"] == numero_pagamento

                if abs(new_total - amount) <= 1 and new_total != 0:
                    df_check.loc[name_mask, "Total"] = amount
                    df_check.loc[name_mask, "CHECK"] = "VERO"
                    pagamenti.loc[numero_mask, "CHECK"] = "VERO"
                    print(df_check.loc[name_mask, "Name"], df_check.loc[name_mask, "Total"], new_total)
                
                elif abs(new_total - amount) <= 1 and new_total <= 1:
                    df_check.loc[name_mask, "Total"] = amount
                    df_check.loc[name_mask, "Lineitem quantity"] = 0
                    df_check.loc[name_mask, "CHECK"] = "VERO"
                    pagamenti.loc[numero_mask, "CHECK"] = "VERO"
        
        return df_check, pagamenti

#check
def process_check_groups(group):
    if "VERO" in group["CHECK"].values:
        return group[group["CHECK"] == "VERO"]
    else:
        return group