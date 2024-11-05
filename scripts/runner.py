#FILE CHE PRENDE IN INPUT I MATCHER E DA COME OUTPUT I VARI DATAFRAME ELABORATI
import pandas as pd
import numpy as np

from utils.exceptions import SkipMatcherException

class MatcherRunner:

    def __init__(self, matchers, df_ordini_iniziale):
        self.matchers = matchers
        self.df_ordini_iniziale = df_ordini_iniziale
        self.df_ordini_all = None
        self.columns = {}

    def reformat_date(self, date_str):
        if pd.notna(date_str):
            date_str = date_str.strip().replace("/", "-")[:10]
        # Check if the string starts with "202"
            if not date_str.startswith("202"):
                # Split and rearrange as "YYYY-MM-DD"
                return "-".join(date_str.split("-")[::-1])
        return date_str  # Return as-is if already starts with "2024"

    def check_partially_refunded(self, df_check):
        nomi = df_check[((df_check["Outstanding Balance"] != 0) | df_check["Refunded Amount"] != 0)  &
                         (df_check["note_interne"] != "Non rilevante") &
                         (df_check["note_interne"] != "Reso dubbio") &
                         (df_check['Importo Pagato'].isna()) & 
                         (df_check['Total'] != 0)]["Name"].unique()

        for name in nomi:
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
                    df_check.loc[name_mask, 'note_interne'] = "Pagamento non trovato"
        return df_check


    def run_all_matchers(self, mese, anno=2024):
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
            df_ordini = df_ordini.groupby("Name", group_keys=False).apply(self.process_check_groups) 

            # Check for unmatched names using explicit boolean indexing
            unique_names = set(df_ordini["Name"].unique())  # Use a set for faster lookup
            unmatched_mask = ~self.df_ordini_iniziale["Name"].isin(unique_names)
            unmatched_rows = self.df_ordini_iniziale[unmatched_mask]

            # Concatenate ordini and unmatched rows
            self.df_ordini_all = pd.concat([df_ordini, unmatched_rows], ignore_index=True)
            self.df_ordini_all['Total'] = self.df_ordini_all.groupby('Name')['Total'].transform(lambda x: x.where(x.index == x.index[0], np.nan))
            
            self.df_ordini_all = self.df_ordini_all.drop_duplicates(subset=['Name', 'Lineitem name'])
            self.df_ordini_all['CHECK'] = self.df_ordini_all['CHECK'].fillna("NON TROVATO")
            self.df_ordini_all.loc[(self.df_ordini_all['Importo Pagato'].isna()) & 
                                   (self.df_ordini_all['note_interne'] == "Gift Card only"), "Importo Pagato"] = 0
            
            self.df_ordini_all = self.check_partially_refunded(self.df_ordini_all)
            
            # Select columns from each DataFrame in all_dfs before concatenating
            df_pagamenti = pd.concat([df for df in all_dfs], ignore_index=True)
            
            mask = self.df_ordini_all["note_interne"] == "Metodo di pagamento ignoto"
            self.df_ordini_all["giorno"] = self.df_ordini_all['Paid at'].apply(self.reformat_date)
            df_pagamenti["giorno"] = df_pagamenti['Data'].apply(self.reformat_date)
            self.df_ordini_all["index_df"] = self.df_ordini_all.index
            df_pagamenti["index_pag"] = df_pagamenti.index
            merged = pd.merge(self.df_ordini_all[mask], df_pagamenti[df_pagamenti["CHECK"] == "NON TROVATO"], left_on=["Total", "giorno"], right_on = ["Importo Pagato", "giorno"], how = "inner")
            
            if len(merged) > 0:
                for _, row in merged.iterrows():
                    idx_df = row["index_df"] 
                    idx_pag = row["index_pag"] 
                    metodo = row["Metodo"]
                    self.df_ordini_all.loc[idx_df, "Payment Method"] = metodo
                    self.df_ordini_all.loc[idx_df, "CHECK"] = "VERO"
                    self.df_ordini_all.loc[idx_df, "note_interne"] = np.nan
                    df_pagamenti.loc[idx_pag, "CHECK"] = "VERO"
                
            self.df_ordini_all.loc[mask & (self.df_ordini_all["CHECK"] != "VERO"), "note_interne"] = "Pagamento non trovato"
            
            # Checking for inconsistencies in "Total" using explicit length check
            inconsistent_groups = self.df_ordini_all.groupby('Name').filter(lambda group: group['Total'].nunique() > 1)
            if len(inconsistent_groups) > 0:
                print(f"Inconsistent 'Total' values detected for the following 'Names':\n{inconsistent_groups}")
            else:
                print("All 'Names' have consistent 'Total' values.")

            return self.df_ordini_all, df_pagamenti, self.columns
        
        except Exception as e:
            print(f"Error in run_all_matchers: {str(e)}")
            raise e

    #check
    def process_check_groups(self, group):
        if "VERO" in group["CHECK"].values:
            return group[group["CHECK"] == "VERO"]
        else:
            return group