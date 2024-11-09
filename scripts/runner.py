#FILE CHE PRENDE IN INPUT I MATCHER E DA COME OUTPUT I VARI DATAFRAME ELABORATI
import pandas as pd
import numpy as np

from utils.exceptions import SkipMatcherException
from utils.functions import reformat_date, check_partially_refunded, process_check_groups

class MatcherRunner:

    def __init__(self, matchers, df_ordini_iniziale):
        self.matchers = matchers
        self.df_ordini_iniziale = df_ordini_iniziale
        self.df_ordini_all = None
        self.columns = {}


    def handle_pagamenti_altri(self, pag):
        
        mask = self.df_ordini_all["CHECK"] == "PAGAMENTO ALTRO"
        self.df_ordini_all["giorno"] = self.df_ordini_all['Paid at'].apply(reformat_date)
        pag["giorno"] = pag['Data'].apply(reformat_date)
        self.df_ordini_all["index_df"] = self.df_ordini_all.index
        pag["index_pag"] = pag.index
        print(pag[pag["CHECK"] == "NON TROVATO"][["Importo Pagato", "Metodo", "Data"]])
        merged = pd.merge(self.df_ordini_all[mask], pag[pag["CHECK"] == "NON TROVATO"], left_on=["Total", "giorno"], right_on = ["Importo Pagato", "giorno"], how = "inner")
        
        if len(merged) > 0:
            for _, row in merged.iterrows():
                idx_df = row["index_df"] 
                idx_pag = row["index_pag"] 
                metodo = row["Metodo"]
                self.df_ordini_all.loc[idx_df, "Payment Method"] = metodo
                self.df_ordini_all.loc[idx_df, "CHECK"] = "VERO"
                pag.loc[idx_pag, "CHECK"] = "VERO"
        else:
            self.df_ordini_all.loc[mask, "CHECK"] = "NON TROVATO"

        print(merged[["Name_x", "Total", "Payment Method", "Metodo", "Importo Pagato_y"]])
        # print(pag)

        return self.df_ordini_all, pag


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
            self.df_ordini_all['Total'] = self.df_ordini_all.groupby('Name')['Total'].transform(lambda x: x.where(x.index == x.index[0], np.nan))
            
            self.df_ordini_all = self.df_ordini_all.drop_duplicates(subset=['Name', 'Lineitem name'])
            self.df_ordini_all['CHECK'] = self.df_ordini_all['CHECK'].fillna("NON TROVATO")
            self.df_ordini_all.loc[(self.df_ordini_all['Importo Pagato'].isna()), "Importo Pagato"] = 0
            
            self.df_ordini_all = check_partially_refunded(self.df_ordini_all, post_processing=True)
            
            # Select columns from each DataFrame in all_dfs before concatenating
            df_pagamenti = pd.concat([df for df in all_dfs], ignore_index=True)

            self.df_ordini_all, df_pagamenti = self.handle_pagamenti_altri(df_pagamenti)
            print(self.df_ordini_all.CHECK.value_counts())
            print(df_pagamenti.CHECK.value_counts())


            return self.df_ordini_all, df_pagamenti, self.columns
        
        except Exception as e:
            print(f"Error in run_all_matchers: {str(e)}")
            raise e

