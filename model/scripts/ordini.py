#CLASSE CHE PRENDE IN ENTRATA FILE DI ORDINI, LO PULISCE E LO RESTITUISCE PULITO

import pandas as pd
import numpy as np
import io

class Ordini:
    def __init__(self, uploaded_files, mese, anno):
        """
        uploaded_files: A dictionary where keys are file names and values are UploadedFile objects
        mese: The month of interest
        """
        self.uploaded_files = uploaded_files  # Dictionary of UploadedFile objects
        self.df = None  # This will hold the DataFrame once loaded
        self.mese = mese
        self.anno = anno
        self.colonne = None



    def handle_data_upload(self, name):

        f_file = self.uploaded_files.get(name, {}).get("file")

        if f_file:

            stringio = io.StringIO(f_file.getvalue().decode("utf-8"))
            f = pd.read_csv(stringio, dtype={"Paid at": "string",'Lineitem sku': 'string'})  # Read the CSV data
        
            f["Brand"] = name
            f[f.columns] = f.groupby('Name')[f.columns].ffill()

            expected_date = f"{self.anno}-{str(self.mese).zfill(2)}"
            f_filtered = f[(f["Paid at"].str[:7] == expected_date) | (f["Paid at"].isna())].copy()
        else:
            f_filtered = pd.DataFrame()  # or handle the missing file as needed

        return f_filtered
    

# scripts/your_processing_file.py
    def load_data(self):

        lil = self.handle_data_upload("Ordini LIL")
        agee = self.handle_data_upload("Ordini AGEE")

        self.df = pd.concat([lil, agee], ignore_index=True) if len(lil) > 0 or len(agee) > 0 else pd.DataFrame()

        self.colonne = self.df.columns

        # escludere = ["#42196", "#42244", "#42439", "#42471", "#42518", "#42675", "#42676", "#42691", "#42726", "#42745", "#42833", "#42927", "#43014", "#43017", ]

        # self.df = self.df[~self.df['Name'].isin(escludere)]

    #gestire i nomi dei pagamenti
    def handle_payment_method(self):

        self.df["Payment Method"] = self.df["Payment Method"].str.replace("Custom (POS)", "Qromo")
        self.df["Payment Method"] = self.df["Payment Method"].str.replace("QROMO", "Qromo")
        # self.df['Payment Method'] = self.df['Payment Method'].str.strip().str.lower().replace('qromo', 'Qromo')
        self.df["Payment Method"] = self.df["Payment Method"].str.replace("custom|Wire Transfer", "Bonifico", regex=True)

        payments = ["Bonifico", "PayPal Express Checkout", "Qromo", "Satispay", "Scalapay", "Shopify Payments", "Gift Card", "Cash"]
        pattern = '|'.join(payments) 

        # Check if "Payment Method" contains any of the payment methods in the list
        self.df["CHECK"] = self.df["Payment Method"].apply(lambda x: "PAGAMENTO ALTRO" if pd.notna(x) and not pd.Series(x).str.contains(pattern, regex=True).any() else None)

        #Gestire Cash
        cash_names = self.df[self.df["Payment Method"] == "Cash"]["Name"].unique()
        mask = self.df["Name"].isin(cash_names)
        self.df.loc[mask, "CHECK"] = "ESCLUSO" 

        #gestire gift cards
        gift_card_names = self.df[self.df["Payment Method"].str.contains("Gift Card", na=False)]["Name"].unique()
        mask = self.df["Name"].isin(gift_card_names)
        self.df.loc[mask, "CHECK"] = "FALSO"
        
   
    #gestire la location
    def handle_location(self):

        self.df['Location'] = self.df['Location'].str.replace(r'(?i)\blil house\b', 'LIL House', regex=True)
        self.df['Location'] = self.df['Location'].str.replace(r'(?i)\bfirgun house\b', 'Firgun House', regex=True)
        self.df['Location'] = self.df['Location'].str.replace(r'(?i)\blil house london\b', 'LIL House London', regex=True)

        #LIL Milan
        self.df.loc[(self.df['Brand'] == "Ordini LIL") & 
                    (self.df['Location'].isna()) & 
                    ((self.df['Shipping Method'] == "Standard") | (self.df['Shipping Method'] == "Standard Shipping")), "Location"] = "LIL House London"
        
        #AGEE
        self.df.loc[(self.df['Brand'] == "Ordini AGEE") & 
                    (self.df['Location'].isna()) & 
                    (self.df['Shipping Method'] == "Standard"), "Location"] = "Firgun House"
        
        #Fill missing Location
        # location_nan = self.df.groupby('Name')['Location'].transform(lambda x: x.isna().all())
        location_nan = self.df.groupby('Name')['Location'].transform('count') == 0
        self.df.loc[location_nan, 'Location'] = "Firgun House"

        #metti ESCLUSO agli ordini che non ci interessano
        relevant_locations = ["LIL House", "Firgun House", "LIL House London"]            
        self.df.loc[~(self.df['Location'].isin(relevant_locations)) & (~self.df['Location'].isna()), "CHECK"] = "ESCLUSO"    

   
    #aggiungere country se manca
    def handle_shipping_country(self):   

        #"LIL Milan"
        self.df.loc[((self.df["Brand"] == "Ordini LIL") & 
                    ((self.df["Shipping Method"] == "Firgun House") | (self.df["Shipping Method"].isna()))) & 
                    (self.df["Shipping Country"].isna()), "Shipping Country"] = "IT"
        
        #"AGEE"
        self.df.loc[((self.df["Brand"] == "Ordini AGEE") & 
                    (self.df["Shipping Method"] == "Standard") | (self.df["Shipping Method"].isna())) & 
                    (self.df["Shipping Country"].isna()), "Shipping Country"] = "IT"


    #sconti del 100%
    def handle_discount_code(self):

        self.df["Payment Method"] = self.df["Payment Method"].str.strip()

        altri_negozi = self.df[((self.df["Payment Method"].isna()) & (self.df["Total"] == 0))]["Name"].unique()
        gifts = self.df[((self.df["Discount Code"].str.contains(r"(?i)gift|diretti", na=False)))]["Name"].unique()
        ddt = self.df[((self.df["Discount Code"].str.contains(r"(?i)ddt", na=False)))]["Name"].unique()
        sostituzioni = self.df[((self.df["Discount Code"].str.contains(r"(?i)(sostituzione)", na=False)) & (self.df["Total"] == 0))]["Name"].unique()
        
        for name in np.concatenate([altri_negozi, sostituzioni]):
            mask = self.df["Name"] == name
            self.df.loc[mask, "CHECK"] = "ESCLUSO"

        for name in gifts:
            mask = self.df["Name"] == name
            self.df.loc[mask, "Total"] = 0
            self.df.loc[mask, "CHECK"] = "ESCLUSO"
        
        for name in ddt:
            mask = self.df["Name"] == name
            self.df.loc[mask, "Total"] = 0
            self.df.loc[mask, "Lineitem quantity"] = 0
            self.df.loc[mask, "CHECK"] = "ESCLUSO"
   
    #applica le funzione handle_cambi
    def apply_cambi(self):
        self.df = self.handle_cambi()

    #gestire i cambi e modificare i totali e le quantità
    def handle_cambi(self):
        nomi_cambi = self.df.loc[(self.df['Lineitem compare at price'] == 0) & 
                                 (self.df['Lineitem price'] != 0) 
                                # & (self.df['Total'] != 0)
                                 , 'Name'].unique()

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
                        elif total == 0:
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
                            elif total == 0:
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
                            elif total == 0:
                                self.df.loc[item_aggiunto_e_reso.index, 'Lineitem quantity'] = 0
                                self.df.loc[primi_items_gioielli.index, 'Lineitem quantity'] = 0

        return self.df
    

    #gestire PARTIALLY_PAID/PARTIALLY_REFUNDED E REFUNDED di Cash only
    def handle_financial_status(self):
        
        all_compare_nonzero = self.df.groupby("Name")["Lineitem compare at price"].transform(lambda x: (x != 0).all())
        nomi = self.df[((self.df["Outstanding Balance"] != 0) | self.df["Refunded Amount"] != 0) & ((self.df["Payment Method"] == "Cash")) & all_compare_nonzero]["Name"].unique()

        for name in nomi:
            name_mask = self.df["Name"] == name
            
            if name_mask.any():  # Check if any rows match
                new_total = self.df.loc[name_mask, "Total"].values[0] - self.df.loc[name_mask, "Refunded Amount"].values[0] - self.df.loc[name_mask, "Outstanding Balance"].values[0]
                if new_total > 0:
                    self.df.loc[name_mask, "Total"] = new_total
                elif new_total == 0:
                    self.df.loc[name_mask, "Total"] = 0
                    self.df.loc[name_mask, "Lineitem quantity"] = 0
                else:
                    self.df.loc[name_mask, 'CHECK'] = "FALSO" 


    def handle_nan(self):

        fill_columns = ["Subtotal", "Shipping", "Total", "Discount Amount", "Refunded Amount", "Outstanding Balance"]
        self.df[fill_columns] = self.df[fill_columns].fillna(0)
        
        colonne_non_na = ["Name", "Paid at", "Lineitem quantity", "Lineitem name", "Lineitem price", 
                        "Payment Method", "Location", "Shipping Country", "Payment References"]
        
        rilevanti = self.df[(self.df["CHECK"] != "ESCLUSO")]["Name"].unique()

        mask_rilevanti = self.df["Name"].isin(rilevanti)
        nan_mask = self.df[mask_rilevanti][colonne_non_na].isna().any(axis=1)
        self.df.loc[mask_rilevanti & nan_mask, "CHECK"] = "VALORE NAN"



    def preprocess(self):
        # Call all preprocessing steps in sequence
        self.load_data()
        self.handle_payment_method() #1
        self.handle_location() #2
        self.handle_shipping_country() #3
        self.handle_discount_code() #4
        self.apply_cambi() #5
        self.handle_financial_status() #6
        self.handle_nan()#7


        return self.df, self.colonne