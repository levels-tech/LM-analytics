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
def check_partially_refunded(df_check, post_processing = False):

    # Create a mask to check if all rows with the same name have "Lineitem compare at price" not equal to 0
    all_compare_nonzero = df_check.groupby("Name")["Lineitem compare at price"].transform(lambda x: (x != 0).all())
    

    if post_processing == False:
        # Apply the mask to select rows based on all conditions
        altro = df_check[((df_check["Outstanding Balance"] != 0) | (df_check["Refunded Amount"] != 0)) & (df_check["CHECK"] == "FALSO") & all_compare_nonzero]["Name"].unique()

    else:
        altro = df_check[((df_check["Outstanding Balance"] != 0) | (df_check["Refunded Amount"] != 0)) 
                         & ((df_check["CHECK"] == "FALSO") | (df_check["CHECK"] == "FNON TROVATO"))
                         & (~(all_compare_nonzero & df_check["Total"] == (df_check["Subtotal"] + df_check["Shipping"])))
                         ]["Name"].unique()

    for name in altro:
        name_mask = df_check["Name"] == name
        
        if name_mask.any():  # Check if any rows match
            amount = df_check.loc[name_mask, "Importo Pagato"].values[0] if not pd.isna(df_check.loc[name_mask, "Importo Pagato"].values[0]) else 0
            new_total = df_check.loc[name_mask, "Subtotal"].values[0] + df_check.loc[name_mask, "Shipping"].values[0] - df_check.loc[name_mask, "Refunded Amount"].values[0] - df_check.loc[name_mask, "Outstanding Balance"].values[0]
            
            if abs(new_total - amount) <= 1 and new_total != 0:
                df_check.loc[name_mask, "Total"] = amount
                df_check.loc[name_mask, "CHECK"] = "VERO"
            
            elif abs(new_total - amount) <= 1 and new_total <= 1:
                df_check.loc[name_mask, "Total"] = amount
                df_check.loc[name_mask, "Lineitem quantity"] = 0
                df_check.loc[name_mask, "CHECK"] = "VERO"
            
    return df_check



#check
def process_check_groups(group):
    if "VERO" in group["CHECK"].values:
        return group[group["CHECK"] == "VERO"]
    else:
        return group