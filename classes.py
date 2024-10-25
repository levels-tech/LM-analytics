#LIL MILAN CLASSES:

import pandas as pd
import numpy as np
import re

from openpyxl import Workbook, load_workbook
from openpyxl.utils.cell import quote_sheetname

filepath = "C:\\Users\\isabe\\Downloads\\"


#CLASSE CHE PRENDE IN ENTRATA FILE DI ORDINI, LO PULISCE E LO RESTITUISCE PULITO
class Ordini:
    def __init__(self, filepath):
        self.filepath = filepath
        self.df = None  # This will hold the DataFrame once loaded

    def load_data(self):
        # Load the CSV data
        # self.df = pd.read_csv(self.filepath + "Ordini LIL.csv", 
        #                       dtype={'Lineitem sku': 'string', 'Device ID': 'string', 'Id': 'string', 
        #                              "Tags": "string", "Next Payment Due At": "string"})
        self.df = pd.read_excel(self.filepath + "Vendite Agosto v3.xlsx", sheet_name="Generale LIL")
        
        # Forward-fill NaN values for the same Name
        self.df[self.df.columns] = self.df.groupby('Name')[self.df.columns].ffill()

    def adjust_financial_status(self):
        # PARTIALLY_PAID handling
        partially_paid_names = self.df[self.df["Financial Status"] == "partially_paid"]["Name"].unique()
        mask = self.df["Name"].isin(partially_paid_names)
        self.df.loc[mask, "Total"] = self.df.loc[mask, "Total"] - self.df.loc[mask, "Outstanding Balance"]
        
        # REFUNDED handling
        refunded_names = self.df[self.df["Financial Status"] == "refunded"]["Name"].unique()
        for name in refunded_names:
            mask = self.df["Name"] == name
            total_value = self.df.loc[mask, "Total"].iloc[0]
            if total_value != 0:
                diff = self.df.loc[mask, "Total"] - self.df.loc[mask, "Refunded Amount"]
                self.df.loc[mask & (diff == 0), "Total"] = 0
                self.df.loc[mask & (diff == 0), "Lineitem quantity"] = 0

    def handle_discounts(self):
        # Handle discount codes (e.g., Roma100, MILANO100%, etc.)
        sconto100_names = self.df[(self.df["Discount Code"].str.contains('100%', case=False, na=False)) & 
                                  (self.df["Total"] == 0)]["Name"].unique()
        for name in sconto100_names:
            mask = self.df["Name"] == name
            self.df.loc[mask, "CHECK"] = "SCONTO100"

    def adjust_country(self):        
        # Handle missing Shipping Country
        self.df.loc[((self.df["Shipping Method"] == "Firgun House") | 
                     (self.df["Shipping Method"].isna())) & 
                    (self.df["Shipping Country"].isna()), "Shipping Country"] = "IT"

    def handle_gift_card(self):
        # Handle gift card payments
        gift_card_names = self.df[self.df["Payment Method"] == "Gift Card"]["Name"].unique()
        mask = self.df["Name"].isin(gift_card_names)
        self.df.loc[mask, "CHECK"] = "FALSO"
        self.df.loc[mask, "CHECK_VALORE_GIFT_CARD"] = self.df.loc[mask, "Total"]

    def handle_payments(self):
        #Handle payment types
        self.df["Payment Method"] = self.df["Payment Method"].str.strip()
        self.df["Payment Method"] = self.df["Payment Method"].str.replace("Custom (POS)", "Qromo")
        self.df["Payment Method"] = self.df["Payment Method"].str.replace("custom", "Bonifico")

    def handle_location(self):
        # Add LIL House London Locations
        london_locations = self.df.loc[self.df['Location'].isna() & (self.df['Shipping Method'] == "Standard")]
        self.df.loc[london_locations.index, 'Location'] = "LIL House London"
        
        # Fill missing Location values with default value
        location_nan = self.df.groupby('Name')['Location'].transform(lambda x: x.isna().all())
        self.df.loc[location_nan, 'Location'] = "Firgun House"

    def apply_cambi(self):
        # Apply the changes defined in the 'ordini_con_cambi' logic
        self.df = self.ordini_con_cambi()

    def ordini_con_cambi(self):
        nomi_cambi = self.df.loc[(self.df['Lineitem compare at price'] == 0) & 
                                 (self.df['Lineitem price'] != 0) & 
                                 (self.df['Total'] != 0), 'Name'].unique()

        # Process each group by 'Name' for the return handling logic
        for name, group in self.df.groupby('Name'):
            if name in nomi_cambi:
                items_comprati_dopo = group[group['Lineitem compare at price'] == 0]
                primi_items = group[group['Lineitem compare at price'].isna()]
                primi_items_gioielli = primi_items[primi_items['Lineitem price'] > 10]

                total = group['Total'].values[0]
                shipping = group['Shipping'].values[0]
                discount = group['Discount Amount'].values[0]
            
                #Solo un oggetto è stato scambiato
                if len(items_comprati_dopo) == 1: 

                    item_comprato_dopo_price = items_comprati_dopo['Lineitem price'].values[0]
                    item_comprato_dopo_quantity = items_comprati_dopo['Lineitem quantity'].values[0]

                    #solo un oggetto tra quelli comprati inizialmente è candidato per essere stato scambiato (supponiamo che il cliente non scambia borse, scatole ed engraving)
                    if len(primi_items_gioielli) == 1 and item_comprato_dopo_price > 10: #se è minore o uguale a 10, l'ha probabilmente aggiunto

                        item_restituito_price = primi_items_gioielli['Lineitem price'].values[0]
                        item_restituito_quantity = primi_items_gioielli['Lineitem quantity'].values[0]
                    
                        items_tenuti_prices = (primi_items.loc[~primi_items.index.isin(primi_items_gioielli.index)].apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1)
                                            .sum()) + (item_comprato_dopo_price * item_comprato_dopo_quantity) #primi items acquistati che non sono gioielli + item comprato dopo
                        
                        new_total = total - (item_restituito_price * item_comprato_dopo_quantity)  #tolgo tante unità dell'oggetto comprato prima quanti oggeti sono stati comprati dopo
                        check_total = items_tenuti_prices + shipping - discount + item_restituito_price * (item_restituito_quantity - item_comprato_dopo_quantity)

                        if new_total == check_total and new_total > 0:
                            self.df.loc[group.index, 'Total'] = new_total
                            self.df.loc[primi_items_gioielli.index, 'Lineitem quantity'] = item_restituito_quantity - item_comprato_dopo_quantity

                    #più di un oggetto tra quelli comprati inizialmente potrebbe essere stato scambiato
                    elif len(primi_items_gioielli) > 1 and item_comprato_dopo_price > 10:

                        matched_row = primi_items_gioielli[primi_items_gioielli['Lineitem price'] == item_comprato_dopo_price]

                        # Check if there's a match and retrieve its price and quantity
                        if len(matched_row) == 1:
                            item_restituito_price = matched_row['Lineitem price'].values[0]
                            item_restituito_quantity = matched_row['Lineitem quantity'].values[0]

                            items_tenuti_prices = (primi_items.loc[~primi_items.index.isin(matched_row.index)].apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1)
                                            .sum()) + (item_comprato_dopo_price * item_comprato_dopo_quantity) #primi items acquistati che non sono gioielli + item comprato dopo
                        
                            new_total = total - (item_restituito_price * item_comprato_dopo_quantity)  #tolgo tante unità dell'oggetto comprato prima quanti oggeti sono stati comprati dopo
                            check_total = items_tenuti_prices + shipping - discount + item_restituito_price * (item_restituito_quantity - item_comprato_dopo_quantity)

                            if new_total == check_total and new_total > 0:
                                self.df.loc[group.index, 'Total'] = new_total
                                self.df.loc[matched_row.index, 'Lineitem quantity'] = item_restituito_quantity - item_comprato_dopo_quantity

                
                #più oggeti sono stati scambiati
                elif len(items_comprati_dopo) == 2:
                    
                    #più oggetti consecutivamente
                    if len(primi_items_gioielli) == 1: #si assume che avvengano due resi consecutivi

                        ultimo_item_tenuto = items_comprati_dopo.iloc[-1] #si assume siano in ordine
                        ultimo_item_tenuto_price = ultimo_item_tenuto['Lineitem price']
                        ultimo_item_tenuto_quantity = ultimo_item_tenuto['Lineitem quantity']

                        item_aggiunto_e_reso = items_comprati_dopo.loc[items_comprati_dopo.index != ultimo_item_tenuto.name]
                        item_aggiunto_e_reso_quantity = item_aggiunto_e_reso['Lineitem quantity'].values[0]

                        item_restituito_price = primi_items_gioielli['Lineitem price'].values[0]
                        item_restituito_quantity = primi_items_gioielli['Lineitem quantity'].values[0]

                        if ultimo_item_tenuto_quantity == item_aggiunto_e_reso_quantity == item_restituito_quantity:
                            primi_items = pd.concat([primi_items, item_aggiunto_e_reso])
                            tutti_gioielli_tranne_ultimo = primi_items[primi_items['Lineitem price'] > 10]

                            items_tenuti_prices = (primi_items.loc[~primi_items.index.isin(tutti_gioielli_tranne_ultimo.index)].apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1)
                                                .sum()) + (ultimo_item_tenuto_price * ultimo_item_tenuto_quantity) #primi items acquistati che non sono gioielli + item comprato dopo
                            
                            items_restituiti_prices = (tutti_gioielli_tranne_ultimo.apply(lambda row: row['Lineitem price'] * row['Lineitem quantity'], axis=1).sum())
                        
                            new_total = total - items_restituiti_prices
                            check_total = items_tenuti_prices + shipping - discount 

                            if new_total == check_total and new_total > 0:
                                self.df.loc[group.index, 'Total'] = new_total
                                self.df.loc[item_aggiunto_e_reso.index, 'Lineitem quantity'] = 0
                                self.df.loc[primi_items_gioielli.index, 'Lineitem quantity'] = 0

        return self.df

    def preprocess(self):
        # Call all preprocessing steps in sequence
        self.load_data()
        self.adjust_financial_status()
        self.handle_discounts()
        self.adjust_country()
        self.handle_gift_card()
        self.handle_payments()
        self.handle_location()
        self.apply_cambi()

        return self.df
    


#PAGAMENTI: PRENDE IN ENTRATA I VARI METODI DI PAGAMENTO, GLI ORDINI PULITI E TROVA I MATCH. 
#RESTITUISCE IL DF DEI MATCH CHE SERVE PER MOSTRARE I CASI DA CONTROLLARE, IL DF DEGLI ORDINI ULTERIORMENTE CONTROLLATI E IL DF DEI PAGAMENTI CON AGGIUNTA COLONNA CHECK
class PaymentMatcher:
    payment_info_list = [] 

    def __init__(self, filepath, df_ordini):
        self.filepath = filepath
        self.df_ordini = df_ordini

    #fare check se va controllato
    def check_values(self, row, tipo):
        total = row["Total"]
        amount = self.get_amount(row, tipo)

        if pd.isna(total) or pd.isna(amount):
            return "NON TROVATO"
        elif abs(total - amount) <= 0.05:
            return "VERO"
        else:
            return "FALSO"

    #Calcolare valore teorico della gift card
    def calculate_gift_card(self, row, tipo):
        amount = self.get_amount(row, tipo)
        if row["CHECK"] == "FALSO" and "Gift Card" in str(row["Payment Method"]):
            return row["Total"] - amount
        elif row["CHECK"] == "NON TROVATO" and "Gift Card" in str(row["Payment Method"]):
            return row["Total"] - amount
        else:
            return np.nan

    #controlla se il discount è giusto
    def check_discounts(self, row, df_check, tipo):
        
        nomi = df_check.loc[(df_check["CHECK"] == "FALSO") & 
                        (df_check["CHECK_VALORE_GIFT_CARD"].isna()) & 
                        (df_check["Lineitem compare at price"] == 0)]["Name"]
    
        # If nomi is empty, return df_check unchanged
        if nomi.empty:
            return df_check
        
        for name, group in df_check.groupby('Name'):
            if name in nomi.values:
                items_comprati_dopo = group[group['Lineitem compare at price'] == 0]
                primi_items = group[group['Lineitem compare at price'].isna()]
                primi_items_gioielli = primi_items[primi_items['Lineitem price'] > 10]

                total = group['Total'].values[0]
                shipping = group['Shipping'].values[0]
                discount = group['Discount Amount'].values[0]

                amount = self.get_amount(row, tipo)

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

        return df_check
       
    #in base al metodo di pagamento, la colonna dell'amount differisce                     
    def get_amount(self, row, tipo):
        """To be implemented in subclass, depending on the 'tipo'"""
        raise NotImplementedError


    #applica tutti i check
    def apply_checks(self, df_check, tipo):
        df_check["CHECK"] = df_check.apply(lambda row: self.check_values(row, tipo), axis=1)
        df_check["CHECK_VALORE_GIFT_CARD"] = df_check.apply(lambda row: self.calculate_gift_card(row, tipo), axis=1)

        cols = df_check.columns.tolist()
        cols = [col for col in cols if col not in ["CHECK", "CHECK_VALORE_GIFT_CARD"]] + ["CHECK", "CHECK_VALORE_GIFT_CARD"]
        df_check = df_check[cols]
    
        return df_check


    #gestisce pagamenti con più di un payment reference
    def match_references(self, payment_reference, merchant_ids):
        # Split the Payment Reference if there is a "+" sign
        references = payment_reference.split('+') if '+' in payment_reference else [payment_reference]
        
        # Check if any of the references matches a Merchant ID
        for ref in references:
            if ref.strip() in merchant_ids:
                return ref.strip()  # Return the first matching reference
        return None  # No match found

#matcher di paypal
class PaypalMatcher(PaymentMatcher):
    def get_amount(self, row, tipo):
        return row["Lordo"]

    def match(self):
        # df_full = pd.read_csv(filepath+"Paypal.csv")
        df_full = pd.read_csv(filepath+"Paypal 8 2024.csv")
        df_full['Lordo'] = df_full['Lordo'].str.replace('.', '', regex=False)  # Remove periods (thousands separator)
        df_full['Lordo'] = df_full['Lordo'].str.replace(',', '.', regex=False)  # Replace commas with periods (decimal separator)
        df_full['Lordo'] = pd.to_numeric(df_full['Lordo'], errors='coerce')  # Convert to numeric, coercing errors to NaN        
        df_full = df_full[df_full["Tipo"].isin(["Pagamento Express Checkout", "Rimborso di pagamento"])]
        df_full = df_full[~df_full["Nome"].str.contains("propac", case=False, na=False)] #ha detto di toglierlo


        df = df_full[['Data',"Nome", "Tipo", 'Valuta', 'Lordo', 'N° ordine commerciante', "Titolo oggetto"]]
        df = df.groupby('N° ordine commerciante', as_index=False)['Lordo'].sum()

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Paypal', case=False, na=False)]

        merchant_ids = df['N° ordine commerciante'].astype(str).tolist()
        df_ordini['Matched Reference'] = df_ordini['Payment References'].apply(lambda ref: self.match_references(ref, merchant_ids))
        df_check = pd.merge(df_ordini, df, left_on="Matched Reference", right_on="N° ordine commerciante", how='outer')

        df_check = self.apply_checks(df_check, "paypal")
    
        # Apply check_discounts function directly for each row and modify df_check
        for _, row in df_check.iterrows():
            df_check = self.check_discounts(row, df_check, "paypal")
        
        df_check["Payment Method"] = df_check["Payment Method"].astype(str)
        mask = (df_check["Payment Method"].str.contains(r'\+') 
                & (df_check["CHECK"] == "VERO"))
        df_check.loc[mask & df_check["Payment Method"].str.contains("PayPal Express Checkout"), "Payment Method"] = "PayPal Express Checkout" 
        
        df_ordini = df_check[self.df_ordini.columns]

        df_full = pd.merge(df_full, df_check[["N° ordine commerciante", "CHECK"]], on = ["N° ordine commerciante"], how = "left")
        df_full = df_full.drop_duplicates()

        return df_check, df_ordini, df_full
    
#matcher del bonifico
class BonificoMatcher(PaymentMatcher):
    def get_amount(self, row, tipo):
        return row["Importo"]
    
    def find_header_row(self, excel_file, column_name):

        df_sample = pd.read_excel(excel_file)  # Adjust number as needed
        header_row = 0

        # Find the row containing the known column name
        for idx, row in df_sample.iterrows():
            if column_name in row.values:
                header_row = idx
                break

        df = pd.read_excel(excel_file, header=header_row)
                
        return df
    

    def match(self):

        operations_patterns = [
            r'stripe',
            r'paypal',
            r'satispay',
            r'scalapay',
            r'rinascente',
            r'paesi ue',
            r'retail group',
            r'sportello automatico',
        ]

        # df_full =  self.find_header_row(filepath+"Intesa 9.xlsx", "Importo")
        df_full =  self.find_header_row(filepath+"Bonifici 8 2024.xlsx", "Importo")
        mask = ~df_full['Operazione'].str.contains('|'.join(operations_patterns), case=False, regex=True, na=False)
        df_full = df_full[mask]        
        df_full["Data_datetime"] = pd.to_datetime(df_full['Data']).dt.tz_localize(None)

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Bonifico', case=True, na=False)]
        df_ordini['Paid_datetime'] = pd.to_datetime(df_ordini['Paid at']).dt.tz_localize(None)

        df_check = pd.merge(df_ordini, df_full, left_on='Total', right_on='Importo', how='outer')

        df_check = self.apply_checks(df_check, "bonifico")

        df_check['Days_difference'] = ((df_check['Data_datetime'] - df_check['Paid_datetime']).dt.days).abs() 
    
        # Using .values for direct comparison without index dependency
        mask = df_check['Days_difference'].values == df_check.groupby('Name')['Days_difference'].transform('min').values
        df_check = df_check[mask | df_check['Days_difference'].isna()]

        # min_days_difference = df_check.groupby('Name')['Days_difference'].transform(lambda x: x.min())
        # df_check = df_check[(df_check['Days_difference'] == min_days_difference) | df_check['Days_difference'].isna()]

        # Apply check_discounts function directly for each row and modify df_check
        for _, row in df_check.iterrows():
            df_check = self.check_discounts(row, df_check, "bonifico")

        df_check["Payment Method"] = df_check["Payment Method"].astype(str)
        mask = (df_check["Payment Method"].str.contains(r'\+') 
                & (df_check["CHECK"] == "VERO"))
        df_check.loc[mask & df_check["Payment Method"].str.contains("Bonifico"), "Payment Method"] = "Bonifico"

        # names_with_vero = df_check[df_check['CHECK'] == 'VERO']['Name'].unique()
        # df_check = df_check[~((df_check['CHECK'] == 'FALSO') & (df_check['Name'].isin(names_with_vero)))]

        df_ordini = df_check[self.df_ordini.columns]

        df_full = pd.merge(df_full, df_check[["Data_datetime", "CHECK"]], on = ["Data_datetime"], how = "left")
        df_full = df_full.drop_duplicates()

        return df_check, df_ordini, df_full

#matcher di qromo
class QromoMatcher(PaymentMatcher):
    def get_amount(self, row, tipo):
        # return row["Importo Effettivo"]
        return row["Importo Effettivo"]

    def match(self, mese, anno):
        df_full = pd.read_csv(filepath+"qromo.csv")
        # df_full = pd.read_csv(filepath+"Qromo 8 2024.csv")
        if mese < 10:
            data_interesse = str(anno)+"-0"+str(mese)
        else:
            data_interesse = str(anno)+"-"+str(mese)

        df_full = df_full[df_full["Data"].str.startswith(data_interesse)]
        df_full = df_full[df_full["Stato"] != "Annullato"]
        df_full["Data_datetime"] = pd.to_datetime(df_full["Data"]).dt.tz_localize(None)

        df_full["Importo €"] = df_full["Importo €"].astype(float)
        df_full["Importo rimborsato €"] = df_full["Importo rimborsato €"].astype(float)
        df_full["Importo Effettivo"] = df_full["Importo €"] - df_full["Importo rimborsato €"]
        df_full = df_full[df_full["Importo Effettivo"] != 0]

        df = df_full.copy()
        df['partial_date'] = df['Data_datetime'].dt.date
        df = df[["Stato", "Importo €", "Importo rimborsato €", "Importo Effettivo", "Data_datetime", "partial_date"]]
        df = df.sort_values('Data_datetime')

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Qromo', case=False, na=False)]
        df_ordini['Paid_datetime'] = pd.to_datetime(df_ordini['Paid at']).dt.tz_localize(None)
        df_ordini['partial_date'] = df_ordini['Paid_datetime'].dt.date
        df_ordini = df_ordini[~df_ordini["Name"].isin(PaymentMatcher.payment_info_list)]
        df_ordini = df_ordini.sort_values('Paid_datetime')

        df_check = pd.merge(df_ordini, df, on='partial_date', how='outer', suffixes=('_qromo', '_ordini'))
        df_check = df_check.drop(columns=['partial_date'])

        df_check = self.apply_checks(df_check, "qromo")

        df_check['Time_difference'] = (df_check['Data_datetime'] - df_check['Paid_datetime']).abs() 
    
        # Using .values for direct comparison without index dependency
        mask = df_check['Time_difference'].values == df_check.groupby('Name')['Time_difference'].transform('min').values
        df_check = df_check[mask | df_check['Time_difference'].isna()]

        # df_check = df_check.loc[df_check.groupby(['Name', "Lineitem name", 'CHECK'])['Time_difference'].idxmin()]

        names_with_vero = df_check[df_check['CHECK'] == 'VERO']['Name'].unique()
        df_check = df_check[~((df_check['CHECK'] == 'FALSO') & (df_check['Name'].isin(names_with_vero)))]

        for _, row in df_check.iterrows():
            df_check = self.check_discounts(row, df_check, "qromo")

        # Create a mask for rows that contain '+' in the 'Payment Method', exclude 'Gift Card', and have 'CHECK' set to 'VERO'
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))
    
        df_check.loc[mask & df_check["Payment Method"].str.contains('Qromo'), "Payment Method"] = "Qromo"

        df_ordini = df_check[self.df_ordini.columns]

        df_full = pd.merge(df_full, df_check[["Data_datetime", "CHECK"]], on = ["Data_datetime"], how = "left")
        df_full = df_full.drop("Data_datetime", axis = 1)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full = df_full.drop_duplicates()

        return df_check, df_ordini, df_full

#matcher di shopify   
class ShopifyMatcher(PaymentMatcher):
    def get_amount(self, row, tipo):
        return row["Amount"]

    def match(self):
        # df_full = pd.read_csv(self.filepath + "Shopify LIL.csv")
        df_full = pd.read_csv(self.filepath + "Shopify LIL 8 2024.csv")
        df = df_full.groupby('Order', as_index=False)['Amount'].sum()

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Shopify', case=False, na=False)]

        df_check = pd.merge(df_ordini, df, left_on="Name", right_on="Order", how='outer')
        df_check = self.apply_checks(df_check, "shopify")
    
        # Apply check_discounts function directly for each row and modify df_check
        for _, row in df_check.iterrows():
            df_check = self.check_discounts(row, df_check, "shopify")
        
        df_check["Payment Method"] = df_check["Payment Method"].astype(str)
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))

        df_check.loc[mask & df_check["Payment Method"].str.contains("Shopify Payments"), "Payment Method"] = "Shopify Payments"
        df_ordini = df_check[self.df_ordini.columns]

        df_full = pd.merge(df_full, df_check[["Name", "CHECK"]], left_on = "Order", right_on = "Name", how = "left")
        df_full = df_full.drop("Name", axis = 1)
        df_full = df_full.drop_duplicates()

        return df_check, df_ordini, df_full
    
#matcher di scalapay
class ScalapayMatcher(PaymentMatcher):
    def get_amount(self, row, tipo):
        return row["Import lordo"]

    def match(self):
        # df_full = pd.read_csv(filepath + "scalapay 9.2023.csv")
        df_full = pd.read_csv(filepath + "scalapay 8 2024.csv")
        df = df_full[["Merchant ID", "Tipo", "Data acquisto/rimborso", "Import lordo"]]

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Scalapay', case=False, na=False)]

        # Check orders with double reference
        merchant_ids = df['Merchant ID'].astype(str).tolist()
        df_ordini['Matched Reference'] = df_ordini['Payment References'].apply(lambda ref: self.match_references(ref, merchant_ids))
        df_check = pd.merge(df_ordini, df, left_on="Matched Reference", right_on="Merchant ID", how='outer')

        df_check = self.apply_checks(df_check, "scalapay")
    
        # Apply check_discounts function directly for each row and modify df_check
        for _, row in df_check.iterrows():
            df_check = self.check_discounts(row, df_check, "scalapay")

        df_check["Payment Method"] = df_check["Payment Method"].astype(str)
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))

        df_check.loc[mask & df_check["Payment Method"].str.contains("Scalapay"), "Payment Method"] = "Scalapay"

        df_ordini = df_check[self.df_ordini.columns]

        df_full = pd.merge(df_full, df_check[["Merchant ID", "CHECK"]], on = ["Merchant ID"], how = "left")
        df_full = df_full.drop_duplicates()

        return df_check, df_ordini, df_full
    
#matcher di satispay
class SatispayMatcher(PaymentMatcher):
    def get_amount(self, row, tipo):
        return row["total_amount"]
    
    def match(self):
        df_full = pd.read_csv(filepath+"Satispay.csv")
        df = df_full[['payment_date', 'total_amount', 'description']]
        df["Data_datetime"] = pd.to_datetime(df["payment_date"] ).dt.tz_localize(None)
        df['partial_date'] = df['Data_datetime'].dt.date

        df_ordini_online = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Satispay', case=False, na=False)]

        df_ordini_negozio = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Qromo', case=False, na=False)]
        df_ordini_negozio['Paid_datetime'] = pd.to_datetime(df_ordini_negozio['Paid at']).dt.tz_localize(None)
        df_ordini_negozio['partial_date'] = df_ordini_negozio['Paid_datetime'].dt.date

        # Check orders ONLINE with double reference: 
        merchant_ids = df['description'].astype(str).tolist()
        df_ordini_online['Matched description'] = df_ordini_online['Payment References'].apply(lambda ref: self.match_references(ref, merchant_ids))
        df_check_online = pd.merge(df_ordini_online, df[df["description"] != "0"], left_on="Matched description", right_on="description", how='outer')

        df_check_online = self.apply_checks(df_check_online, "satispay")

        for _, row in df_check_online.iterrows():
            df_check_online = self.check_discounts(row, df_check_online, "satispay")

        # Check order in Negozio:
        df_check_negozio = pd.merge(df_ordini_negozio, df[df["description"] == "0"], on="partial_date", how='right')
        df_check_negozio['Time_difference'] = (df_check_negozio['Paid_datetime'] - df_check_negozio['Data_datetime']).abs()    

        df_check_negozio = self.apply_checks(df_check_negozio, "satispay")

        for _, row in df_check_negozio.iterrows():
            df_check_negozio = self.check_discounts(row, df_check_negozio, "satispay")

        df_check_negozio = df_check_negozio.loc[df_check_negozio.groupby(['CHECK', "Data_datetime"])['Time_difference'].idxmin()]
        
        names_with_vero = df_check_negozio[(df_check_negozio['CHECK'] == 'VERO')]['Data_datetime'].unique()
        df_check_negozio = df_check_negozio[~((df_check_negozio['CHECK'] == 'FALSO') & (df_check_negozio['Data_datetime'].isin(names_with_vero)))]

        # Store payment_date and total_amount of rows with "VERO"
        for n in names_with_vero:
            PaymentMatcher.payment_info_list.append(n)

        df_check = pd.concat([df_check_online, df_check_negozio])
    
        df_check["Payment Method"] = df_check["Payment Method"].astype(str)
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))

        df_check.loc[mask & df_check["Payment Method"].str.contains("Satispay"), "Payment Method"] = "Satispay"

        df_ordini = df_check[self.df_ordini.columns]

        df_full = pd.merge(df_full, df_check[["payment_date", "description", "CHECK"]], on = ["payment_date", "description"], how = "left")
        df_full = df_full.drop_duplicates()

        return df_check, df_ordini, df_full
    


#CLASSE PER RUNNARE I MATCHERS E CREARE EXCEL
class MatcherRunner:
    def __init__(self, matchers, df_ordini_iniziale, filename):
        self.matchers = matchers
        self.df_ordini_iniziale = df_ordini_iniziale
        self.filename = filename
        self.df_ordini_all = None

    #runna matchers e crea excel
    def run_all_matchers(self, mese=9, anno=2024):
        qromo_matcher = next((matcher for matcher in self.matchers if isinstance(matcher, QromoMatcher)), None)
        all_dfs = []
        check_dfs = []
        
        with pd.ExcelWriter(self.filename, engine='openpyxl', mode='w') as writer:
            for matcher in self.matchers:
                if matcher != qromo_matcher:
                    df_check, df_ordini, df = matcher.match()
                else:
                    df_check, df_ordini, df = matcher.match(mese, anno)

                # Append the DataFrame to our list
                all_dfs.append(df_ordini)
                check_dfs.append(df_check)

                # Write each returned `df` (the additional DataFrame) as a new sheet
                payment_name = matcher.__class__.__name__.replace("Matcher", "")
                df.to_excel(writer, sheet_name=f'{payment_name}', index=False)
            
            # Concatenate all DataFrames for final processing
            df_ordini_payments = pd.concat(all_dfs, ignore_index=True)
            df_ordini_payments = df_ordini_payments[df_ordini_payments["Name"].notna()]
            df_ordini_payments = df_ordini_payments.groupby("Name", group_keys=False).apply(self.process_check_groups)

            # Check for unmatched names
            unique_names_payments = df_ordini_payments["Name"].unique()
            unmatched_rows = self.df_ordini_iniziale[~self.df_ordini_iniziale["Name"].isin(unique_names_payments)]

            # Concatenate payments and unmatched rows
            self.df_ordini_all = pd.concat([df_ordini_payments, unmatched_rows], ignore_index=True)
            self.df_ordini_all['Total'] = self.df_ordini_all.groupby('Name')['Total'].transform(lambda x: x.where(x.index == x.index[0], np.nan))
            self.df_ordini_all = self.df_ordini_all.drop_duplicates(subset=['Name', 'Lineitem name'])

            # Checking for inconsistencies in "Total"
            inconsistent_totals = self.df_ordini_all.groupby('Name').filter(lambda group: group['Total'].nunique() > 1)
            
            if not inconsistent_totals.empty:
                print(f"Inconsistent 'Total' values detected for the following 'Names':\n{inconsistent_totals}")
            else:
                print("All 'Names' have consistent 'Total' values.")

            print()

            # Write the concatenated data to the main sheet
            self.df_ordini_all.to_excel(writer, sheet_name='Ordini LIL', index=False)

        # Create the summary table in a new sheet
        self.create_summary_table()
        self.create_daily_summary_table()

        # First, create a list of all unique names that have CHECK == "VERO" across all dataframes
        all_vero_names = set()  # using a set for unique values
        for df in check_dfs:
            vero_names = df[df['CHECK'] == "VERO"]['Name'].dropna().unique()
            all_vero_names.update(vero_names)

        # Now process each dataframe
        for df in check_dfs:
            mask = (
                (~df['Name'].isin(all_vero_names)) | 
                (df['Name'].isna()) |
                ((df['Name'].isin(all_vero_names)) & (df['CHECK'] == "VERO"))
            )
            
            # Apply the mask and print
            filtered_df = df[mask]
            filtered_df = filtered_df.drop_duplicates(subset=['Name', 'Lineitem name'])
            display(filtered_df[filtered_df["CHECK"] != "VERO"])
        
        return df_check, self.df_ordini_all, df

    #check
    def process_check_groups(self, group):
        if "VERO" in group["CHECK"].values:
            return group[group["CHECK"] == "VERO"]
        else:
            return group


    def create_summary_table(self):
        try:
            workbook = load_workbook(self.filename)
        except FileNotFoundError:
            workbook = Workbook()

        # Create or select the sheet for the summary
        summary_sheet = workbook['Totale'] if 'Totale' in workbook.sheetnames else workbook.create_sheet('Totale')

        # Clear previous content in the summary sheet
        for row in summary_sheet.iter_rows(min_row=1, max_col=10, max_row=summary_sheet.max_row):
            for cell in row:
                cell.value = None
                
        # Write headers for payments
        summary_sheet['A1'] = 'Payments'
        summary_sheet['B1'] = 'LIL'
        summary_sheet['C1'] = 'CHECK'
        
        # Title mapping for totals
        title_of_totals = {
            'Scalapay': 'J',
            'Shopify': 'I',
            'PayPal': 'H',
            'Bonifico': 'H', 
            'Qromo': 'F',
            'Satispay': 'E',
            'Cash': ''  # Placeholder; no column for Cash since it will be a hyphen
        }

        # Write payment methods to the summary sheet
        row = 2  # Start from the second row
        for payment_label, payment_amount in title_of_totals.items():
            summary_sheet[f'A{row}'] = payment_label
            summary_sheet[f'B{row}'] = f'=SUMIFS(\'Ordini LIL\'!$L:$L, \'Ordini LIL\'!$AV:$AV, "*{payment_label}*")'
            
            if payment_label == "Cash":
                summary_sheet[f'C{row}'] = '-'  # Write a hyphen for Cash
            else:
                summary_sheet[f'C{row}'] = f'=SUM(\'{payment_label}\'!{payment_amount}:{payment_amount})'

            row += 1  # Increment the row for the next payment method

        # Add the "Total" row for payments
        summary_sheet[f'A{row}'] = 'Totale'
        summary_sheet[f'B{row}'] = f'=SUM(B2:B{row-1})'  # Adjust row number based on the last payment method

        # Leave some columns between the two tables (e.g., start the location table at column E)
        summary_sheet['F1'] = 'Locations'  # Header for the Locations table
        summary_sheet['G1'] = 'Incasso'         # Header for LIL sums
        summary_sheet['H1'] = 'Ordini'    # Header for the Locations table
        summary_sheet['I1'] = 'Items'         # Header for LIL sums
        summary_sheet['J1'] = 'Oggetti per ordine'  

        # Create list of strings to exclude
        exclude_strings = [
            "Luxury Pack",
            "Engraving",
            "E-gift",
            "Repair",
            "Whatever Tote",
            "Piercing Party",
            "LIL Bag"
        ]

        # Create the filter using | (OR) operator between all patterns
        df_ordini_gioielli = self.df_ordini_all[~self.df_ordini_all['Lineitem name'].str.contains('|'.join(exclude_strings), case=False, na=False)]

        # First, let's create the groupby object with multiple aggregations
        location_stats = df_ordini_gioielli.groupby('Location').agg({'Name': 'nunique',  # Count unique names
                                                                    'Lineitem quantity': 'sum'      # Sum of totals
                                                                    }).reset_index()

        # Convert to dictionary for easier access
        stats_dict = location_stats.set_index('Location').to_dict()

        # Example usage for locations
        title_of_locations = df_ordini_gioielli["Location"].unique()
        
        for idx, location_label in enumerate(title_of_locations, start=2):            
            # Set the formula in the cell
            summary_sheet[f'F{idx}'] = location_label
        
            # Set other formulas as needed
            summary_sheet[f'G{idx}'] = (
                f'=SUMIFS(\'Ordini LIL\'!$L:$L, '
                f'\'Ordini LIL\'!$BB:$BB, "{location_label}")'
            )

            #numero ordini per location
            #numero oggetti per location
            unique_orders = stats_dict['Name'].get(location_label, 0)
            items_quantity = stats_dict['Lineitem quantity'].get(location_label, 0)

            # Write the scalar values
            summary_sheet[f'H{idx}'] = unique_orders 
            summary_sheet[f'I{idx}'] = items_quantity 

            summary_sheet[f'J{idx}'] = (f'=I{idx}/H{idx}')
        
        
        # Add the "Total" row for locations
        summary_sheet[f'F{idx+1}'] = 'Totale'
        summary_sheet[f'G{idx+1}'] = f'=SUM(G2:G{idx})'  # Adjust row number based on the last location method
        summary_sheet[f'H{idx+1}'] = f'=SUM(H2:H{idx})'
        summary_sheet[f'I{idx+1}'] = f'=SUM(I2:I{idx})'
        summary_sheet[f'J{idx+1}'] = f'=I{idx+1}/H{idx+1}'

        # Save the workbook
        workbook.save(self.filename)

    def create_daily_summary_table(self):
        try:
            workbook = load_workbook(self.filename)
        except FileNotFoundError:
            workbook = Workbook()

        # Create or select the sheet for the daily summary
        daily_sheet = workbook['Totale_daily'] if 'Totale_daily' in workbook.sheetnames else workbook.create_sheet('Totale_daily')

        # Clear previous content in the daily sheet
        for row in daily_sheet.iter_rows(min_row=1, max_col=10, max_row=daily_sheet.max_row):
            for cell in row:
                cell.value = None

        # Write headers
        daily_sheet['A1'] = 'Giorno'
        daily_sheet['B1'] = 'Paese'
        daily_sheet['C1'] = 'Incasso'


        # Filter the dataframe same as before
        # Extract just the date part (without time) from 'Paid at'
        self.df_ordini_all['Paid at'] = pd.to_datetime(self.df_ordini_all['Paid at'])
        self.df_ordini_all['Data'] = self.df_ordini_all['Paid at'].dt.date

        df_ordini_locations = self.df_ordini_all[self.df_ordini_all["Location"].isin(["Firgun House", "LIL house", "LIL House London"])]

        daily_country_totals = df_ordini_locations.groupby(['Data', 'Shipping Country'])['Total'].sum().reset_index()
        daily_country_totals = daily_country_totals.sort_values(['Data', 'Shipping Country'])
        daily_country_totals = daily_country_totals.rename(columns={'Shipping Country': 'Country'})

        for idx, row in enumerate(daily_country_totals.itertuples(), start=2):
            daily_sheet[f'A{idx}'] = row.Data
            daily_sheet[f'B{idx}'] = row.Country
            daily_sheet[f'C{idx}'] = row.Total

        # Add totals row at the bottom
        last_row = idx + 2
        daily_sheet[f'C{last_row}'] = f'=SUM(C2:C{idx})'
    
        # Save the workbook
        workbook.save(self.filename)


        

        # #
        # # Write location methods to the summary sheet
        # loc_row = 2  # Start from the second row for locations
        # for location_label in title_of_locations:
        #     summary_sheet[f'F{loc_row}'] = location_label
        #     summary_sheet[f'G{loc_row}'] = f'=SUMIFS(\'Ordini LIL\'!$L:$L, \'Ordini LIL\'!$BB:$BB, "{location_label}")'
        #     summary_sheet[f'H{loc_row}'] = f'=COUNTA(UNIQUE(FILTER(\'Ordini LIL\'!A2:A1030; \'Ordini LIL\'!BB2:BB1030="{location_label}")))'
        #      # summary_sheet[f'H{loc_row}'] = f'=IFERROR(@__xludf.DUMMYFUNCTION("COUNTA(UNIQUE(FILTER(\'Ordini LIL\'!A:A, \'Ordini LIL\'!BB:BB = "{location_label}")))");326)'
        # summary_sheet[f'H{loc_row}'] = (
        #     f'=SUM(IF(FREQUENCY(IF(\'Ordini LIL\'!BB:BB="{location_label}", MATCH(\'Ordini LIL\'!A:A, \'Ordini LIL\'!A:A, 0)), ROW(\'Ordini LIL\'!A:A)-ROW(\'Ordini LIL\'!A$1)+1), 1))'
        # )
        
        # # Numero oggetti
        # summary_sheet[f'I{loc_row}'] = f'=SUMIFS(\'Ordini LIL\'!Q:Q, \'Ordini LIL\'!BB:BB, "{location_label}")'

        # summary_sheet[f'J{loc_row}'] = (
        #     f'=SUMPRODUCT((\'Ordini LIL\'!BB:BB = "{location_label}") * (ISERROR(SEARCH({"Luxury Pack","Engraving","E-gift","Repair","Whatever Tote","Piercing Party","LIL Bag"}, \'Ordini LIL\'!R:R))) * (\'Ordini LIL\'!Q:Q))'
        # )



