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

#check
def process_check_groups(group):
    if "VERO" in group["CHECK"].values:
        return group[group["CHECK"] == "VERO"]
    else:
        return group