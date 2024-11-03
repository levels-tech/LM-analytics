#PAGAMENTI: PRENDE IN ENTRATA I VARI METODI DI PAGAMENTO, GLI ORDINI PULITI E TROVA I MATCH. 
#RESTITUISCE IL DF DEI MATCH CHE SERVE PER MOSTRARE I CASI DA CONTROLLARE, IL DF DEGLI ORDINI ULTERIORMENTE CONTROLLATI E IL DF DEI PAGAMENTI CON AGGIUNTA COLONNA CHECK

import pandas as pd
import numpy as np

class PaymentMatcher:
    payment_info_list = [] 

    def __init__(self, uploaded_files, df_ordini):
        self.uploaded_files = uploaded_files
        self.df_ordini = df_ordini

    #fare check per vero/falso/non trovato
    def check_values(self, row):
        total = row["Total"]
        amount = row["Importo Pagato"]

        if pd.isna(total) or pd.isna(amount):
            return "NON TROVATO"
        elif total == amount:
            return "VERO"
        else:
            return "FALSO"

    #Calcolare valore teorico della gift card
    def calculate_gift_card(self, row):
        if row["CHECK"] != "VERO" and "Gift Card" in str(row["Payment Method"]):
            return "Gift Card"
        else:
            return np.nan

    #cambiare valore a VERO per differenze di centesimi (e cambiare anche totale)
    def check_cents_diff(seld, df_check):
        for index, row in df_check.iterrows():
            if row["CHECK"] == "FALSO":
                diff = abs(row["Total"] - row["Importo Pagato"])
                if diff <= 0.05:
                    df_check.at[index, "Total"] = row["Importo Pagato"]
                    df_check.at[index, "CHECK"] = "VERO" 

                if diff <= 1 and df_check.at[index, "Total"] == 0:
                    df_check.at[index, "Importo Pagato"] = 0
                    df_check.at[index, "CHECK"] = "VERO" 


        return df_check

    #controlla se ci sono pagamenti non trovati    
    def check_non_trovato(self, df_check):
        nomi = df_check.loc[(df_check["CHECK"] == "NON TROVATO")]["Name"]
        
        if len(nomi) == 0:
            return df_check
        
        for name, group in df_check.groupby('Name'):
            if name in nomi.values:
                df_check.loc[group.index, "note_interne"] = "Pagamento non trovato"
        return df_check
    
    #controlla se il discount è giusto
    def check_resi(self, df_check):
        
        nomi = df_check.loc[(df_check["CHECK"] == "FALSO") & 
                        (df_check["note_interne"] != "Gift Card") & 
                        (df_check["Lineitem compare at price"] == 0)]["Name"]
    
        # If nomi is empty, return df_check unchanged
        if len(nomi) == 0:
            return df_check
        
        for name, group in df_check.groupby('Name'):
            if name in nomi.values:
                items_comprati_dopo = group[group['Lineitem compare at price'] == 0]
                primi_items = group[group['Lineitem compare at price'].isna()]
                primi_items_gioielli = primi_items[primi_items['Lineitem price'] > 10]

                total = group['Total'].values[0]
                shipping = group['Shipping'].values[0]
                discount = group['Discount Amount'].values[0]

                amount = group["Importo Pagato"].values[0]

                # Solo un oggetto è stato scambiato
                if len(items_comprati_dopo) == 1: 

                    item_comprato_dopo_price = items_comprati_dopo['Lineitem price'].values[0]
                    item_comprato_dopo_quantity = items_comprati_dopo['Lineitem quantity'].values[0]

                    if len(primi_items_gioielli) == 1 and item_comprato_dopo_price > 10:

                        item_restituito_price = primi_items_gioielli['Lineitem price'].values[0]
                        item_restituito_quantity = primi_items_gioielli['Lineitem quantity'].values[0]

                        check_discount = discount / (item_restituito_price * (item_restituito_quantity + item_comprato_dopo_quantity) + item_comprato_dopo_price * item_comprato_dopo_quantity) 
                        calculated_discount = check_discount * item_comprato_dopo_price * item_comprato_dopo_quantity

                        items_tenuti_prices = (
                            primi_items.loc[~primi_items.index.isin(primi_items_gioielli.index)]
                            .apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1)
                            .sum()) + (item_comprato_dopo_price * item_comprato_dopo_quantity)
                        
                        new_total = total + discount - calculated_discount
                        check_total = items_tenuti_prices + shipping - calculated_discount

                        if new_total == check_total and new_total == amount:
                            # Modify df_check instead of self.df_ordini
                            df_check.loc[group.index, 'Total'] = new_total
                            df_check.loc[group.index, 'Discount Amount'] = calculated_discount
                            df_check.loc[group.index, 'CHECK'] = "VERO"
                        else:
                            df_check.loc[group.index, 'note_interne'] = "Sconto dubbio"
                            

                    elif len(primi_items_gioielli) > 1 and item_comprato_dopo_price > 10:

                        matched_row = primi_items_gioielli[primi_items_gioielli['Lineitem price'] == item_comprato_dopo_price]

                        if len(matched_row) == 1:
                            item_restituito_price = matched_row['Lineitem price'].values[0]
                            item_restituito_quantity = matched_row['Lineitem quantity'].values[0]

                            check_discount = discount / (item_restituito_price * (item_restituito_quantity + item_comprato_dopo_quantity) + item_comprato_dopo_price * item_comprato_dopo_quantity) 
                            calculated_discount = check_discount * item_comprato_dopo_price * item_comprato_dopo_quantity

                            items_tenuti_prices = (
                                primi_items.loc[~primi_items.index.isin(matched_row.index)]
                                .apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1)
                                .sum()) + (item_comprato_dopo_price * item_comprato_dopo_quantity)
                            
                            new_total = total + discount - calculated_discount
                            check_total = items_tenuti_prices + shipping - calculated_discount

                            if new_total == check_total and new_total == amount:
                                df_check.loc[group.index, 'Total'] = new_total
                                df_check.loc[group.index, 'Discount Amount'] = calculated_discount
                                df_check.loc[group.index, 'CHECK'] = "VERO"
                            else:
                                df_check.loc[group.index, 'note_interne'] = "Sconto dubbio"

                    else:
                        df_check.loc[group.index, 'note_interne'] = "Reso dubbio"
                            
                #più oggeti sono stati scambiati
                elif len(items_comprati_dopo) == 2:
                    
                    #più oggetti consecutivamente
                    if len(primi_items_gioielli) == 1: #si assume che avvengano due resi consecutivi

                        ultimo_item_tenuto = items_comprati_dopo.iloc[-1] #si assume siano in ordine
                        ultimo_item_tenuto_price = ultimo_item_tenuto['Lineitem price']
                        ultimo_item_tenuto_quantity = ultimo_item_tenuto['Lineitem quantity']

                        item_aggiunto_e_reso = items_comprati_dopo.loc[items_comprati_dopo.index != ultimo_item_tenuto.name]
                
                        item_restituito_price = primi_items_gioielli['Lineitem price'].values[0]
                        item_restituito_quantity = primi_items_gioielli['Lineitem quantity'].values[0]
                        
                        primi_items = pd.concat([primi_items, item_aggiunto_e_reso])
                        tutti_gioielli_tranne_ultimo = primi_items[primi_items['Lineitem price'] > 10]

                        check_discount = discount / (tutti_gioielli_tranne_ultimo.apply(lambda row: row['Lineitem price'] * (row['Lineitem quantity'] + ultimo_item_tenuto_quantity), axis=1).sum()
                                                    + (ultimo_item_tenuto_price * ultimo_item_tenuto_quantity))
                        calculated_discount = check_discount * ultimo_item_tenuto_price * ultimo_item_tenuto_quantity

                        items_tenuti_prices = (primi_items.loc[~primi_items.index.isin(tutti_gioielli_tranne_ultimo.index)].apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1)
                                            .sum()) + (ultimo_item_tenuto_price * ultimo_item_tenuto_quantity) #primi items acquistati che non sono gioielli + item comprato dopo
                        
                        # items_restituiti_prices = (tutti_gioielli_tranne_ultimo.apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1).sum())
                    
                        new_total = total + discount - calculated_discount
                        check_total = items_tenuti_prices + shipping - calculated_discount

                        if new_total == check_total and new_total == amount:
                            df_check.loc[group.index, 'Total'] = new_total
                            df_check.loc[group.index, 'Discount Amount'] = calculated_discount
                            df_check.loc[group.index, 'CHECK'] = "VERO"
                        else:
                            df_check.loc[group.index, 'note_interne'] = "Sconto dubbio"

                    else:
                        df_check.loc[group.index, 'note_interne'] = "Reso dubbio"
                
                else:
                    df_check.loc[group.index, 'note_interne'] = "Reso dubbio"

        return df_check

    # PARTIALLY_REFUNDED handling
    def check_partially_refunded(self, df_check):
        
        # partially_refunded_names = df_check[(df_check["Financial Status"] == "partially_refunded") & (df_check["CHECK"] != "VERO")]["Name"].unique()
        # partially_paid_names = df_check[(df_check["Financial Status"] == "partially_paid") & (df_check["CHECK"] != "VERO")]["Name"].unique()
        # refunded_names = df_check[(df_check["Financial Status"] == "refunded") & (df_check["CHECK"] != "VERO")]["Name"].unique()
        altro = df_check[((df_check["Outstanding Balance"] != 0) | df_check["Refunded Amount"] != 0) & (df_check["CHECK"] != "VERO")]["Name"].unique()

        for name in altro:
            name_mask = df_check["Name"] == name
            if name_mask.any():  # Check if any rows match
                amount = df_check.loc[name_mask, "Importo Pagato"].values[0] if not pd.isna(df_check.loc[name_mask, "Importo Pagato"].values[0]) else 0
                new_total = df_check.loc[name_mask, "Subtotal"].values[0] + df_check.loc[name_mask, "Shipping"].values[0] - df_check.loc[name_mask, "Refunded Amount"].values[0] - df_check.loc[name_mask, "Outstanding Balance"].values[0]
                if new_total == amount and new_total != 0:
                    df_check.loc[name_mask, "Total"] = new_total
                    df_check.loc[name_mask, "CHECK"] = "VERO"
                elif new_total == amount and new_total == 0:
                    df_check.loc[name_mask, "Total"] = 0
                    df_check.loc[name_mask, "Lineitem quantity"] = 0
                    df_check.loc[name_mask, "CHECK"] = "VERO"
                elif abs(new_total - amount) <= 1 and new_total <= 1:
                    df_check.loc[name_mask, "Total"] = 0
                    df_check.loc[name_mask, "Lineitem quantity"] = 0
                    df_check.loc[name_mask, "CHECK"] = "VERO"
                    df_check.loc[name_mask, "Importo Pagato"] == 0
                else:
                    df_check.loc[name_mask, 'note_interne'] = "Rimborso dubbio"

        # #partially_refunded
        # for name in partially_refunded_names:
        #     name_mask = df_check["Name"] == name
        #     if name_mask.any():  # Check if any rows match
        #         amount = df_check.loc[name_mask, "Importo Pagato"].values[0]
        #         new_total = df_check.loc[name_mask, "Total"].values[0] - df_check.loc[name_mask, "Refunded Amount"].values[0]
        #         if new_total == amount:
        #             df_check.loc[name_mask, "Total"] = new_total
        #             df_check.loc[name_mask, "CHECK"] = "VERO"
        #         else:
        #             df_check.loc[name_mask, 'note_interne'] = "Rimborso dubbio"

        # #partially_paid
        # for name in partially_paid_names:
        #     name_mask = df_check["Name"] == name
        #     if name_mask.any():
        #         amount = df_check.loc[name_mask, "Importo Pagato"].values[0]
        #         new_total = df_check.loc[name_mask, "Total"].values[0] - df_check.loc[name_mask, "Outstanding Balance"].values[0]
        #         if new_total == amount:
        #             df_check.loc[name_mask, "Total"] = new_total
        #             df_check.loc[name_mask, "CHECK"] = "VERO"
        #         else:
        #             df_check.loc[name_mask, 'note_interne'] = "Pagamento parziale dubbio"
    
    
        # #refunded
        # for name in refunded_names:
        #     name_mask = df_check["Name"] == name
        #     if name_mask.any():
        #         total_value = df_check.loc[name_mask, "Total"].values[0]
        #         refunded_amount = df_check.loc[name_mask, "Refunded Amount"].values[0]
        #         if total_value != 0:
        #             diff = abs(total_value - refunded_amount)
        #             if diff == 0:
        #                 df_check.loc[name_mask, "Total"] = 0
        #                 df_check.loc[name_mask, "Lineitem quantity"] = 0
        #                 df_check.loc[name_mask, "CHECK"] = "VERO"
        #             elif diff <= 1:
        #                 df_check.loc[name_mask, "Total"] = 0
        #                 df_check.loc[name_mask, "Lineitem quantity"] = 0
        #                 df_check.loc[name_mask, "CHECK"] = "VERO"
        #                 df_check.loc[name_mask, "Importo Pagato"] == 0
        #             else:
        #                 df_check.loc[name_mask, 'note_interne'] = "Rimborso dubbio"    

                  
        
        return df_check
           
    #Controlla se ci sono stati più pagamenti con lo stesso numero di ordine
    def check_double_payments(self, df_check):
        # Step 1: Filter the DataFrame for 'FALSO' in 'CHECK'
        filtered_check = df_check[df_check['CHECK'] == 'FALSO']
        grouped = filtered_check.groupby('Name').filter(lambda x: x['Matched Reference'].nunique() > 1)

        aggregated = grouped.groupby(['Name', 'Matched Reference'], as_index=False).agg(
            Amount =("Importo Pagato", 'first'), 
            Total = ("Total", "first")  # Get the first 'Lordo' value for each unique reference
        )

        # Now, sum the unique Lordo values by Name
        final_aggregation = aggregated.groupby('Name').agg(
            Matched_References=('Matched Reference', 'unique'),
            Sum=("Amount", 'sum'),
            Total=('Total', 'first')  # Assuming 'Total' is a column in df
        ).reset_index()

        # Step 4: Check if the sum of Lordo equals Total and update CHECK in df
        for _, row in final_aggregation.iterrows():
            if row['Sum'] == row['Total']:
                # Update CHECK for all rows with this Name in df
                df_check.loc[df_check['Name'] == row['Name'], 'CHECK'] = 'VERO'

        return df_check
    
    #controlla valuta di paypal
    def check_valuta(self, df_check):

        get_valute = {
            "USD": 0.919548,
            "GBP": 1.172707,
            "CHF": 1.046209,
            "SEK": 0.087655,
            "DKK": 0.134034,
            "HUF": 0.002563,
            "CZK": 0.040004,
            "JPY": 0.006126,
            "NOK": 0.086106, 
            "PLN": 0.231678, 
            "TRY": 0.028939,
            "SGD": 0.68849, 
            "NZD": 0.560897, 
            "HKD": 0.117784,
            "CAD": 0.675812, 
            "AUD": 0.609449,
            "ILS": 0.247803, 
            "RON": 0.2011
        }

        df_check["Euro"] = 0.0 

        for index, row in df_check.iterrows():
            if row["CHECK"] == "FALSO" and row["Valuta"] != "EUR":
                row["Euro"] = row["Importo Pagato"] * get_valute[row["Valuta"]]
                row["note_interne"] = "Valuta non Euro"
                if (row["Total"] - 10) < row["Euro"] < (row["Total"] + 10):
                    df_check.at[index, "Importo Pagato"] = row["Euro"] 
                    df_check.at[index, "CHECK"] = "VERO" 
        df_check = df_check.drop("Euro", axis = 1)

        return df_check
    

    #applica tutti i check
    def apply_checks(self, df_check, valuta = False, qromo = False, satispay = False, double_payments = False, ordini_vecchi = False):
        df_check["CHECK"] = df_check.apply(lambda row: self.check_values(row), axis=1)
        df_check["note_interne"] = df_check.apply(lambda row: self.calculate_gift_card(row), axis=1)
        df_check = self.check_cents_diff(df_check)

        if qromo == True:
            filtered_df = df_check[df_check['CHECK'] != "NON TROVATO"]
            filtered_df['Time_difference'] = (pd.to_datetime(filtered_df['Data']).dt.tz_localize(None) - pd.to_datetime(filtered_df['Paid at']).dt.tz_localize(None)).abs() 
            min_indices = filtered_df.groupby(['Name', "Lineitem name", 'CHECK'])['Time_difference'].idxmin()
            df_min_time_diff = df_check.loc[min_indices]

            df_non_trovato = df_check[df_check['CHECK'] == "NON TROVATO"]
            df_check = pd.concat([df_min_time_diff, df_non_trovato], ignore_index=True)

            names_with_vero = df_check[df_check['CHECK'] == 'VERO']['Name'].unique()
            df_check = df_check[~((df_check['CHECK'] == 'FALSO') & (df_check['Name'].isin(names_with_vero)))]

        elif satispay == True:
            df_check = df_check.loc[df_check.groupby(['CHECK', "Data"])['Time_difference'].idxmin()]
        
            names_with_vero = df_check[(df_check['CHECK'] == 'VERO')]['Data'].unique()
            df_check = df_check[~((df_check['CHECK'] == 'FALSO') & (df_check['Data'].isin(names_with_vero)))]
            df_check["Payment Method"] = "Satispay"

            for n in names_with_vero:
                PaymentMatcher.payment_info_list.append(n)

        df_check = self.check_non_trovato(df_check)
        df_check = self.check_partially_refunded(df_check)
        
        if valuta == True:
            df_check = self.check_valuta(df_check) 

        if double_payments == True:
            df_check = self.check_double_payments(df_check)

        df_check = self.check_resi(df_check)

        cols = df_check.columns.tolist()
        cols = [col for col in cols if col not in ["CHECK", "note_interne"]] + ["CHECK", "note_interne"]
        df_check = df_check[cols]
    
        return df_check

    #gestisce pagamenti con più di un payment reference
    def match_references(self, payment_reference, merchant_ids):

        references = payment_reference.split('+') if '+' in payment_reference else [payment_reference]
        
        matching_references = []
    
        for ref in references:
            stripped_ref = ref.strip()  # Strip whitespace
            if stripped_ref in merchant_ids:
                matching_references.append(stripped_ref)  # Add matching reference to the list
        
        return matching_references  # Return the list of matching references
    
    #merge il df di ordini e di pagamenti
    def merge_dfs(self, ordini, pagamenti):
        merchant_ids = pagamenti["Numero Pagamento"].astype(str).str.strip().tolist()
        ordini['Matched Reference'] = ordini['Payment References'].apply(lambda ref: self.match_references(ref, merchant_ids))
        ordini = ordini.explode('Matched Reference')
        ordini.reset_index(drop=True, inplace=True)

        merged_df = pd.merge(ordini, pagamenti, left_on="Matched Reference", right_on="Numero Pagamento", how='outer')

        return merged_df

