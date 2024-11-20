#FILE CHE PRENDE IN INPUT I MATCHER E DA COME OUTPUT I VARI DATAFRAME ELABORATI
import pandas as pd
import numpy as np

from model.utils.exceptions import SkipMatcherException
from model.utils.functions import reformat_date, check_partially_refunded, process_check_groups

class MatcherRunner:

    def __init__(self, matchers, df_ordini_iniziale):
        self.matchers = matchers
        self.df_ordini_iniziale = df_ordini_iniziale
        self.df_ordini_all = None
        self.columns = {}


    def possibili_pagamenti(self):
        #mergiare la lisa dei possibili pagamenti con gli ordini
        numero_pagamento_lists = self.df_ordini_all.groupby('Name')['Numero Pagamento'].agg(list).reset_index()
        numero_pagamento_lists = numero_pagamento_lists.rename(columns={'Numero Pagamento': 'possibili_pagamenti'})

        self.df_ordini_all = pd.merge(self.df_ordini_all, numero_pagamento_lists, on='Name', how='left')
        self.df_ordini_all['possibili_pagamenti'] = self.df_ordini_all['possibili_pagamenti'].apply(lambda x: np.nan if isinstance(x, list) and all(pd.isna(i) for i in x) else x)

        return self.df_ordini_all


    def handle_nan(self):

        fill_columns = ["Subtotal", "Shipping", "Total", "Discount Amount", "Refunded Amount", "Outstanding Balance"]
        self.df_ordini_all[fill_columns] = self.df_ordini_all[fill_columns].fillna(0)
        
        colonne_non_na = ["Name", "Paid at", "Lineitem quantity", "Lineitem name", "Lineitem price", "Lineitem sku", 
                        "Payment Method", "Location", "Shipping Country", "Payment References"]
        
        exclude_strings = ["Luxury Pack", "Engraving", "E-gift", "Repair", "Whatever Tote", "Piercing Party", "LIL Bag"]
        
        rilevanti = self.df_ordini_all[(self.df_ordini_all["CHECK"] != "ESCLUSO")]["Name"].unique()

        mask_rilevanti = self.df_ordini_all["Name"].isin(rilevanti)
        nan_mask = self.df_ordini_all[mask_rilevanti][colonne_non_na].isna().any(axis=1)
        check_mask = (self.df_ordini_all["CHECK"] == "VERO")
        
        total_names =  self.df_ordini_all[(self.df_ordini_all["Total"] != 0)]["Name"].unique() 
        total_mask = self.df_ordini_all["Name"].isin(total_names)

        gioelli_mask = ~self.df_ordini_all["Lineitem name"].isin(exclude_strings)

        final_mask = mask_rilevanti & nan_mask & check_mask & total_mask & gioelli_mask
        self.df_ordini_all.loc[final_mask, "CHECK"] = "VALORE NAN"
            
        return self.df_ordini_all


    def handle_pagamenti_altri(self, pag):
        
        mask = self.df_ordini_all["CHECK"] == "PAGAMENTO ALTRO"
        self.df_ordini_all["giorno"] = self.df_ordini_all['Paid at'].apply(reformat_date)
        pag["giorno"] = pag['Data'].apply(reformat_date)
        self.df_ordini_all["index_df"] = self.df_ordini_all.index
        pag["index_pag"] = pag.index
        merged = pd.merge(self.df_ordini_all[mask], pag[pag["CHECK"] == "NON TROVATO"], left_on=["Total", "giorno"], right_on = ["Importo Pagato", "giorno"], how = "inner")
        print(merged.columns)
        
        if len(merged) > 0:
            for _, row in merged.iterrows():
                idx_df = row["index_df"] 
                idx_pag = row["index_pag"] 
                metodo = row["Metodo"]
                brand = row["Brand_x"]
                self.df_ordini_all.loc[idx_df, "Payment Method"] = metodo
                self.df_ordini_all.loc[idx_df, "CHECK"] = "VERO"
                pag.loc[idx_pag, "CHECK"] = "VERO"
                pag.loc[idx_pag, "Brand"] = brand
        else:
            self.df_ordini_all.loc[mask, "CHECK"] = "NON TROVATO"

        return self.df_ordini_all, pag
    
    def handle_pagamenti_methods_diversi(self, pag):

        # Mask for rows where CHECK is FALSO and Payment Methods contain '+'
        mask = (self.df_ordini_all["CHECK"] == "FALSO") & \
            (self.df_ordini_all["Payment Method"].str.contains(r'\+', na=False, case=False))
        
        # Get unique names meeting the criteria
        nomi = self.df_ordini_all[mask]["Name"].unique()
        
        for n in nomi:
            # Filter rows for this name only
            mask_nomi = self.df_ordini_all["Name"] == n
            df_n = self.df_ordini_all[mask_nomi]
            
            # If there are 2 or more unique values in 'Numero Pagamento', proceed
            if df_n["Numero Pagamento"].nunique() >= 2:
                # Take the first 'Importo Pagato' value for each unique 'Numero Pagamento' and sum them
                importo_sum = df_n.drop_duplicates(subset="Numero Pagamento")["Importo Pagato"].sum()
                
                # Check if this sum equals the first value in 'Total' for this name
                if importo_sum == df_n["Total"].iloc[0]:
                    # Update 'CHECK' to 'VERO' for all rows with this Name
                    self.df_ordini_all.loc[mask_nomi, "CHECK"] = "VERO"

                    # Find matching rows in 'pag' DataFrame where 'Numero Pagamento' is in df_n["Numero Pagamento"]
                    mask_pagamenti = pag["Numero Pagamento"].isin(df_n["Numero Pagamento"])
                    # Update 'CHECK' column in 'pag' DataFrame for these rows
                    pag.loc[mask_pagamenti, "CHECK"] = "VERO"

        return self.df_ordini_all, pag
    

    def handle_london(self):

        # Mask for rows where CHECK is FALSO and Payment Methods contain '+'
        mask = (self.df_ordini_all["Shipping Country"] == "GB") & (self.df_ordini_all["Location"] != "LIL House London") & (self.df_ordini_all["CHECK"] == "VERO")
        
        print("GB", self.df_ordini_all.loc[mask][["Name", "CHECK", "Location"]])

        # Update the "CHECK" column to "LONDON" where the condition is true
        self.df_ordini_all.loc[mask, "CHECK"] = "LONDON"

        return self.df_ordini_all


    def run_all_matchers(self, mese, anno):
        try:
            all_dfs = []
            check_dfs = []
        
            for matcher in self.matchers:
                try:
                    print(f"Processing matcher: {type(matcher).__name__}")
                    df_check, df, columns = matcher.match(mese, anno)
                    print(f"Match successful for {type(matcher).__name__}")

                    all_dfs.append(df)
                    check_dfs.append(df_check)
                    self.columns[df["Metodo"].values[0]] = columns
                                
                except SkipMatcherException as e:
                    print(f"Skipped matcher: {e}")
                    continue
                except Exception as e:
                    print(f"Error in matcher {type(matcher).__name__}: {str(e)}")
                    raise e

            # Concatenate all DataFrames for final processing
            df_ordini = pd.concat(check_dfs, ignore_index=True)
            df_ordini = df_ordini.groupby("Name", group_keys=False).apply(process_check_groups) 

            # Check for unmatched names using explicit boolean indexing
            unique_names = set(df_ordini["Name"].unique())  # Use a set for faster lookup
            unmatched_mask = ~self.df_ordini_iniziale["Name"].isin(unique_names)
            unmatched_rows = self.df_ordini_iniziale[unmatched_mask]

            # Concatenate ordini and unmatched rows
            self.df_ordini_all = pd.concat([df_ordini, unmatched_rows], ignore_index=True)
            
            self.df_ordini_all = self.df_ordini_all.drop_duplicates() #(subset=['Name', 'Lineitem name'])
            self.df_ordini_all['CHECK'] = self.df_ordini_all['CHECK'].fillna("NON TROVATO")
            self.df_ordini_all.loc[(self.df_ordini_all['Importo Pagato'].isna()), "Importo Pagato"] = 0
            

            # Select columns from each DataFrame in all_dfs before concatenating
            df_pagamenti = pd.concat([df for df in all_dfs], ignore_index=True)
            # print("BONIFICO URGENTE 2", len(df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"]))
            print("BONIFICO isa 2", df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"][["Importo", "CHECK", "Brand"]]) 
            self.df_ordini_all, df_pagamenti = check_partially_refunded(self.df_ordini_all, df_pagamenti)
            # print("BONIFICO URGENTE 3", len(df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"]))
            print("BONIFICO isa 3", df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"][["Importo", "CHECK", "Brand"]]) 

            self.df_ordini_all, df_pagamenti = self.handle_pagamenti_altri(df_pagamenti)
            # print("BONIFICO URGENTE 4", len(df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"]))
            print("BONIFICO isa 4", df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"][["Importo", "CHECK", "Brand"]]) 
            self.df_ordini_all, df_pagamenti = self.handle_pagamenti_methods_diversi(df_pagamenti)
            # print("BONIFICO URGENTE 5", len(df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"]))
            print("BONIFICO isa 5", df_pagamenti[df_pagamenti["Metodo"] == "Bonifico"][["Importo", "CHECK", "Brand"]]) 


            self.df_ordini_all = self.possibili_pagamenti()

            subset_columns = self.df_ordini_all.columns[:self.df_ordini_all.columns.get_loc("Payment References") + 2]

            self.df_ordini_all = self.df_ordini_all.sort_values('CHECK', key=lambda x: x.map({'VERO': 0, 'FALSO': 1, 'NON TROVATO': 2}))
            self.df_ordini_all = self.df_ordini_all.drop_duplicates(subset=subset_columns, keep='first')

            print("ORDINI ALL", self.df_ordini_all.CHECK.value_counts())
            print("PAGAMENTI", df_pagamenti.CHECK.value_counts())

            self.df_ordini_all = self.handle_nan()
            self.df_ordini_all = self.handle_london()

            self.df_ordini_all['Total'] = self.df_ordini_all.groupby('Name')['Total'].transform(lambda x: x.where(x.index == x.index[0], np.nan))

            self.df_ordini_all.to_excel("ordini.xlsx")


            return self.df_ordini_all, df_pagamenti, self.columns
        
        except Exception as e:
            print(f"Error in run_all_matchers: {str(e)}")
            raise e

