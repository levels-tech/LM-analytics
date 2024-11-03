#CLASSE CHE PRENDE IN ENTRATA FILE DI ORDINI, LO PULISCE E LO RESTITUISCE PULITO

import pandas as pd

class Ordini:
    def __init__(self, uploaded_files, mese):
        """
        uploaded_files: A dictionary where keys are file names and values are UploadedFile objects
        mese: The month of interest
        """
        self.uploaded_files = uploaded_files  # Dictionary of UploadedFile objects
        self.df = None  # This will hold the DataFrame once loaded
        self.mese = mese
        self.colonne = None

    #caricare i file
    def load_data(self):
        lil_file = self.uploaded_files.get("Ordini LIL")
        agee_file = self.uploaded_files.get("Ordini AGEE")
        
        # assicurarsi che esista
        if lil_file:
            lil = pd.read_csv(lil_file, dtype={'Lineitem sku': 'string', 'Device ID': 'string', 'Id': 'string', "Tags": "string", "Next Payment Due At": "string"})
            lil["Brand"] = "LIL Milan"
        else:
            lil = pd.DataFrame()  # or handle the missing file as needed

        # assicurarsi che esista
        if agee_file:
            agee = pd.read_csv(agee_file, dtype={'Lineitem sku': 'string', 'Device ID': 'string', 'Id': 'string', "Tags": "string", "Next Payment Due At": "string"})
            agee["Brand"] = "AGEE"
        else:
            agee = pd.DataFrame()  # or handle the missing file as needed

        # Concatenate dataframes if both are available
        self.df = pd.concat([lil, agee], ignore_index=True) if len(lil) > 0 or len(agee) > 0 else pd.DataFrame()

        # Forward-fill NaN values for the same Name
        self.df[self.df.columns] = self.df.groupby('Name')[self.df.columns].ffill()

        self.colonne = self.df.columns

    #gestire PARTIALLY_PAID e REFUNDED
    #FUNZIONANTE PER SETTEMBRE
    def adjust_financial_status(self):
        
        #partially_paid
        partially_paid_names = self.df[self.df["Financial Status"] == "partially_paid"]["Name"].unique()
        condition2 = self.df["Name"].isin(partially_paid_names) & (self.df["Payment Method"] == "Cash")

        # Apply the mask as before
        for name in self.df.loc[condition2, "Name"].unique():
            name_mask = self.df["Name"] == name
            new_total = self.df.loc[name_mask, "Total"].values[0] - self.df.loc[name_mask, "Outstanding Balance"].values[0]
            if new_total >= 0:
                self.df.loc[name_mask, "Total"] = new_total


    # #PROVAAAAAA
    # def adjust_financial_status(self):
        
    #     #partially_paid
    #     partially_paid_names = self.df[self.df["Financial Status"] == "partially_paid"]["Name"].unique()
        
    #     # condition1 = self.df["Name"].isin(partially_paid_names) & ~self.df["Name"].isin(nomi_cambi)
    #     condition2 = self.df["Name"].isin(partially_paid_names) # & (self.df["Payment Method"] == "Cash")
    #     # mask = condition1 | condition2

    #     # Apply the mask as before
    #     for name in self.df.loc[condition2, "Name"].unique():
    #         name_mask = self.df["Name"] == name
    #         new_total = self.df.loc[name_mask, "Total"].values[0] - self.df.loc[name_mask, "Outstanding Balance"].values[0]
    #         if new_total >= 0:
    #             self.df.loc[name_mask, "Total"] = new_total

    #     #partially_refunded
    #     partially_refunded_names = self.df[self.df["Financial Status"] == "partially_paid"]["Name"].unique()
    
    #     mask = self.df["Name"].isin(partially_refunded_names) # & ~self.df["Name"].isin(nomi_cambi)
    #     for name in self.df.loc[mask, "Name"].unique():
    #         name_mask = self.df["Name"] == name
    #         new_total = self.df.loc[name_mask, "Total"].values[0] - self.df.loc[name_mask, "Refunded Amount"].values[0]
    #         if new_total >= 0:
    #             self.df.loc[name_mask, "Total"] = new_total

    #     #refunded
    #     refunded_names = self.df[self.df["Financial Status"] == "refunded"]["Name"].unique()

    #     for name in refunded_names:
    #         mask = self.df["Name"] == name
    #         total_value = self.df.loc[mask, "Total"].values[0]
    #         if total_value != 0:
    #             diff = self.df.loc[mask, "Total"].values[0] - self.df.loc[mask, "Refunded Amount"].values[0]
    #             if diff <= 1: #diff == 0
    #                 self.df.loc[mask, "Total"] = 0
    #                 self.df.loc[mask, "Lineitem quantity"] = 0


    #sconti del 100%
    def handle_discounts(self):
        self.df["Payment Method"] = self.df["Payment Method"].str.strip()
        sconto100_names = self.df[(self.df["Payment Method"].isna()) & 
                                  (self.df["Total"] == 0)]["Name"].unique()
        for name in sconto100_names:
            mask = self.df["Name"] == name
            self.df.loc[mask, "CHECK"] = "SCONTO100"
            self.df.loc[mask, "note_interne"] = "Non rilevante"

    #aggiungere country se manca
    def adjust_country(self):   

        #"LIL Milan"
        self.df.loc[((self.df["Brand"] == "LIL Milan") & 
                    ((self.df["Shipping Method"] == "Firgun House") | 
                    (self.df["Shipping Method"].isna()))) & 
                    (self.df["Shipping Country"].isna()), "Shipping Country"] = "IT"
        
        #"AGEE"
        self.df.loc[((self.df["Brand"] == "AGEE") & 
                    (self.df["Shipping Method"] == "Standard")  | 
                    (self.df["Shipping Method"].isna())) & 
                    (self.df["Shipping Country"].isna()), "Shipping Country"] = "IT"

    #gestire pagamenti SOLO con gift card
    def handle_gift_card(self):
        gift_card_names = self.df[self.df["Payment Method"] == "Gift Card"]["Name"].unique()
        mask = self.df["Name"].isin(gift_card_names)
        self.df.loc[mask, "CHECK"] = "FALSO"
        self.df.loc[mask, "note_interne"] = "Gift Card only"

    #gestire i nomi dei pagamenti
    def handle_payments(self):

        # Define the list of payments and create a regex pattern, 
        payments = ["Bonifico", "PayPal Express Checkout", "Qromo", "Satispay", "Scalapay", "Shopify Payments", "Gift Card"]
        pattern = '|'.join(payments) 

        # Standardize specific payment methods
        self.df["Payment Method"] = self.df["Payment Method"].str.replace("Custom (POS)", "Qromo")
        self.df["Payment Method"] = self.df["Payment Method"].str.replace("custom|Wire Transfer", "Bonifico", regex=True)

        # Check if "Payment Method" contains any of the payment methods in the list
        self.df["CHECK"] = self.df["Payment Method"].apply(lambda x: "PAGAMENTO ALTRO" if pd.notna(x) and not pd.Series(x).str.contains(pattern, regex=True).any() else None)
        self.df["note_interne"] = self.df["CHECK"].apply(lambda x: "Metodo di pagamento ignoto" if x == "PAGAMENTO ALTRO" else None)

        cash_names = self.df[self.df["Payment Method"] == "Cash"]["Name"].unique()
        mask = self.df["Name"].isin(cash_names)
        self.df.loc[mask, "CHECK"] = "CASH"
        self.df.loc[mask, "note_interne"] = "Non rilevante"

    #gestire la location
    def handle_location(self):
        #LIL Milan
        self.df.loc[(self.df['Brand'] == "LIL Milan") & 
                    (self.df['Location'].isna()) & 
                    (self.df['Shipping Method'] == "Standard"), "Location"] = "LIL House London"
        
        #AGEE
        self.df.loc[(self.df['Brand'] == "AGEE") & 
                    (self.df['Location'].isna()) & 
                    (self.df['Shipping Method'] == "Standard"), "Location"] = "Firgun House"
        
        #Fill missing Location
        location_nan = self.df.groupby('Name')['Location'].transform(lambda x: x.isna().all())
        self.df.loc[location_nan, 'Location'] = "Firgun House"

        self.df['Location'] = self.df['Location'].str.replace(r'(?i)\blil house\b', 'LIL House', regex=True)
        self.df['Location'] = self.df['Location'].str.replace(r'(?i)\bfirgun house\b', 'Firgun House', regex=True)
        self.df['Location'] = self.df['Location'].str.replace(r'(?i)\blil house london\b', 'LIL House London', regex=True)

        #metti Non rilevante agli ordini che non ci interessano
        locations = ["LIL House", "Firgun House", "LIL House London"]            
        self.df.loc[~(self.df['Location'].isin(locations)) & (~self.df['Location'].isna()), "note_interne"] = "Non rilevante"            

    #applica le funzione ordin_con_cambi
    def apply_cambi(self):
        self.df = self.ordini_con_cambi()

    #gestire i cambi e modificare i totali e le quantità
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
        self.handle_payments()
        self.adjust_financial_status()
        self.handle_discounts()
        self.adjust_country()
        self.handle_gift_card()
        self.handle_location()
        self.apply_cambi()

        return self.df, self.colonne