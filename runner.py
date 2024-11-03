#FILE CHE PRENDE IN INPUT I MATCHER E DA COME OUTPUT I VARI DATAFRAME ELABORATI
import pandas as pd
import numpy as np

from exceptions import SkipMatcherException
from matcher_qromo import QromoMatcher



class MatcherRunner:

    def __init__(self, matchers, df_ordini_iniziale):
        self.matchers = matchers
        self.df_ordini_iniziale = df_ordini_iniziale
        self.df_ordini_all = None
        self.columns = {}

    def reformat_date(self, date_str):
        if pd.notna(date_str):
            date_str = date_str.strip().replace("/", "-")[:10]
        # Check if the string starts with "2024"
            if not date_str.startswith("2024"):
                # Split and rearrange as "YYYY-MM-DD"
                return "-".join(date_str.split("-")[::-1])
        return date_str  # Return as-is if already starts with "2024"

    def run_all_matchers(self, mese, anno=2024):
        try:
            all_dfs = []
            check_dfs = []
        
            for matcher in self.matchers:
                try:
                    print(f"Processing matcher: {type(matcher).__name__}")
                    if not isinstance(matcher, QromoMatcher):
                        df_check, df, columns = matcher.match()
                    else:
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
            
            # Select columns from each DataFrame in all_dfs before concatenating
            df_pagamenti = pd.concat([df#[["Name", "Metodo", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK", "note_interne"]] 
                                      for df in all_dfs], 
                                      ignore_index=True)
            
            mask = self.df_ordini_all["note_interne"] == "Metodo di pagamento ignoto"
            self.df_ordini_all["giorno"] = self.df_ordini_all['Paid at'].apply(self.reformat_date)
            df_pagamenti["giorno"] = df_pagamenti['Data'].apply(self.reformat_date)
            self.df_ordini_all["index_df"] = self.df_ordini_all.index
            df_pagamenti["index_pag"] = df_pagamenti.index
            # print(self.df_ordini_all[mask])
            # print(df_pagamenti[df_pagamenti["CHECK"] == "NON TROVATO"])
            merged = pd.merge(self.df_ordini_all[mask], df_pagamenti[df_pagamenti["CHECK"] == "NON TROVATO"], left_on=["Total", "giorno"], right_on = ["Importo Pagato", "giorno"], how = "inner")
            
            print(merged)
            if len(merged) > 0:
                for _, row in merged.iterrows():
                    idx_df = row["index_df"] 
                    idx_pag = row["index_pag"] 
                    metodo = row["Metodo"]
                    self.df_ordini_all.loc[idx_df, "Payment Method"] = metodo
                    self.df_ordini_all.loc[idx_df, "CHECK"] = "VERO"
                    self.df_ordini_all.loc[idx_df, "note_interne"] = np.nan
                    df_pagamenti.loc[idx_pag, "CHECK"] = "VERO"
                    print(self.df_ordini_all.loc[idx_df, "Payment Method"])
                    print(df_pagamenti.loc[idx_pag, "CHECK"])
            
            # Checking for inconsistencies in "Total" using explicit length check
            inconsistent_groups = self.df_ordini_all.groupby('Name').filter(lambda group: group['Total'].nunique() > 1)
            if len(inconsistent_groups) > 0:
                print(f"Inconsistent 'Total' values detected for the following 'Names':\n{inconsistent_groups}")
            else:
                print("All 'Names' have consistent 'Total' values.")

            print()

            print(self.df_ordini_all["note_interne"].value_counts(), self.df_ordini_all["note_interne"].isna().sum())
            print(self.df_ordini_all["CHECK"].value_counts(), self.df_ordini_all["CHECK"].isna().sum())

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