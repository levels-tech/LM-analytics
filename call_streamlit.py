#FILE CON FUNZIONI CHIAMATE DIRETTAMENTE DA STREAMLIT


import pandas as pd

from ordini import Ordini

from runner import MatcherRunner

from matcher_bonifico import BonificoMatcher
from matcher_qromo import QromoMatcher
from matcher_paypal import PaypalMatcher
from matcher_satispay import SatispayMatcher
from matcher_scalapay import ScalapayMatcher
from matcher_shopify import ShopifyMatcher

from columns_state import ColumnsState


        
def run(uploaded_ordini_files, uploaded_other_files, mese, anno):    
    #ordini
    print("ordini iniziati")
    ordini_processor = Ordini(uploaded_ordini_files, mese=mese)
    ordini, df_columns = ordini_processor.preprocess()  # Store columns in instance variable
    print("ordini finiti")

    ColumnsState.get_instance().set_df_columns(df_columns)

    try:
        #run matchers
        shopify_matcher = ShopifyMatcher(uploaded_other_files, df_ordini=ordini)
        scalapay_matcher = ScalapayMatcher(uploaded_other_files, df_ordini=ordini)
        satispay_matcher = SatispayMatcher(uploaded_other_files, df_ordini=ordini)
        paypal_matcher = PaypalMatcher(uploaded_other_files, df_ordini=ordini)
        qromo_matcher = QromoMatcher(uploaded_other_files, df_ordini=ordini)
        bonifico_matcher = BonificoMatcher(uploaded_other_files, df_ordini=ordini)

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
        print(pagamenti_columns)
        ColumnsState.get_instance().set_pagamenti_columns(pagamenti_columns)
        
        return result, pagamenti
    
    except Exception as e:
        print(f"Error in run: {str(e)}")
        raise e


def update_df(df, index, new_value, nota, pagamenti = None):
    print("Entering update_df")  # Debug print to indicate the function is called
    print(f"Parameters received: df: {df.shape}, index: {index}, new_value: {new_value}, nota: {nota}")
    
    if pagamenti is not None:
        print("Initial pagamenti:\n", pagamenti)
        
        if new_value[0] is not None:
            print("Adding a new row.")
            brand = "LIL Milan" if int(new_value[0]) > 30000 else "AGEE"
            new_row = {
                "Name": "#" + str(new_value[0]),
                "Total": pagamenti.loc[index, "Importo Pagato"],
                "Paid at": pagamenti.loc[index, "Data"],
                "Shipping Country": new_value[2].strip(),
                "Location": str(new_value[1]),
                "Payment Method": pagamenti.loc[index, "Metodo"],
                "Brand": brand,
                "CHECK": "VERO"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            pagamenti.loc[index, "Brand"] = brand
            print("New row added:", new_row)
        
        else:
            print(f"Dropping row at index {index}")
            pagamenti.drop(index, inplace=True)
            
    print("Updated pagamenti:\n", pagamenti)

    # Handle df updates based on nota
    if nota == "Gift Card" or nota == "Gift Card only":
        print("Processing Gift Card or Gift Card only")
        if index:  # Check if index is not empty
            # Filter the indices where Total is not NaN
            valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]

            if valid_indices:  # Check if there are any valid indices
                first_valid_index = valid_indices[0]  # Get the first valid index
                df.loc[first_valid_index, "Total"] = new_value  # Update Total at that index
                print(f"Updated index {first_valid_index}: {df.loc[first_valid_index]}")

                # Clean and set the Payment Method for all rows in 'index'
                if nota == "Gift Card":
                    original_method = df.loc[first_valid_index, "Payment Method"]
                    cleaned_method = original_method.replace("Gift Card", "").replace("+", "").strip()
                    df.loc[index, "Payment Method"] = cleaned_method
                    print(f"Updated Payment Method for indices {index}: {cleaned_method}")
            else:
                print("No valid index found where 'Total' is not NaN.")

    elif nota == "Reso dubbio":
        print("Processing Reso dubbio")
        print(f"Index before processing: {index}")  # Debug print
        print(f"New value before processing: {new_value}")  # Debug print

        # Check if index and new_value have the same length
        if len(index) != len(new_value):
            raise ValueError("Index list and new value list must have the same length.")

        # Update the DataFrame with the new quantities based on the provided indexes
        for idx, new_quantity in zip(index, new_value):
            df.loc[idx, 'Lineitem quantity'] = new_quantity
            print(f"Updated Lineitem quantity at index {idx} to {new_quantity}")  # Debug print

        # Calculate the total
        total = 0

        # Ensure there are indices to avoid IndexError
        if index:  # Check if index is not empty
            # Filter the indices where Total is not NaN
            valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]
            print(valid_indices)

            if valid_indices:  # Check if there are any valid indices
                first_row = min(valid_indices)  # Get the first valid index
                print(f"First row for total calculation: {first_row}")  # Debug print

                # Sum total for all line items with the same "Name"
                for idx in index:
                    row = df.iloc[idx]
                    total += row['Lineitem quantity'] * row['Lineitem price']
                    print(f"Current total after adding index {idx}: {total}")  # Debug print

                # Adding Shipping and subtracting Discount from the first row
                shipping = df.loc[first_row, 'Shipping'] if pd.notna(df.loc[first_row, 'Shipping']) else 0
                discount = df.loc[first_row, 'Discount Amount'] if pd.notna(df.loc[first_row, 'Discount Amount']) else 0
                total += shipping - discount
                print(f"Total after adding Shipping and subtracting Discount: {total}")  # Debug print

                # Compare the new total with "Importo Pagato"
                importo_pagato = df.loc[first_row, 'Importo Pagato'] if pd.notna(df.loc[first_row, 'Importo Pagato']) else 0
                print(f"Importo Pagato: {importo_pagato}")  # Debug print
                
                if total != importo_pagato:
                    raise ValueError(f"Controllare le quantità, l'importo pagato {importo_pagato} non corrisponde con il totale calcolato {total}")
                else:
                    df.loc[first_row, 'Total'] = total


    elif nota == "Pagamento non trovato":
        print("Processing Pagamento non trovato")

        if index:  # Check if index is not empty
            # Filter the indices where Total is not NaN
            valid_indices = [i for i in index if pd.notna(df.loc[i, "Total"])]

            if valid_indices:  # Check if there are any valid indices
                first_valid_index = valid_indices[0]  # Get the first valid index
                df.loc[first_valid_index, "Total"] = new_value  # Update Total at that index
                print(f"Updated index {first_valid_index}: {df.loc[first_valid_index]}")

            else:
                print("No valid index found where 'Total' is not NaN.")
    # Always return both DataFrames
    return df, pagamenti








