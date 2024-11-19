import pandas as pd
import numpy as np

from model.matchers.matcher_base import PaymentMatcher
from model.utils.exceptions import SkipMatcherException


#matcher di qromo
class QromoMatcher(PaymentMatcher):

    def match(self, mese, anno):

        df_full = self.handle_load_data("Qromo", mese, anno)
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Qromo")
        
        columns = df_full.columns

        df_full = df_full[df_full["Stato"] != "Annullato"]

        df_full["Importo €"] = df_full["Importo €"].astype(float)
        df_full["Importo rimborsato €"] = df_full["Importo rimborsato €"].astype(float)
        df_full["Importo Pagato"] = df_full["Importo €"] - df_full["Importo rimborsato €"]
        df_full = df_full[df_full["Importo Pagato"] != 0]
        df_full['Numero Pagamento'] = df_full['ID'] 
        
        df = df_full.copy()
        
        df['partial_date'] =  pd.to_datetime(df['Data']).dt.tz_localize(None).dt.date
        df = df[["Data", "Stato", "Importo €", "Importo rimborsato €", "Importo Pagato", "Numero Pagamento", "partial_date"]]
        df = df.sort_values('Data')
        
        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Qromo', case=False, na=False)]
        paid_at = df_ordini['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)
        df_ordini['partial_date'] = pd.to_datetime(paid_at).dt.tz_localize(None).dt.date
        df_ordini = df_ordini.sort_values('Paid at')

        #nuova logica matching
        df_ordini_solo = df_ordini.loc[df_ordini["Payment Method"] == "Qromo"]

        #solo falso perchè prendiamo solo gli ordini che hanno Qromo come unico metodo di pagamento 
        df_check = pd.merge(df_ordini_solo, df, left_on=['partial_date', "Total"], right_on = ["partial_date", "Importo Pagato"], how='outer', suffixes=('_ordini', '_qromo'))

        # create Time_difference
        paid_at = pd.to_datetime(df_check['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)).reset_index(drop=True)
        df_check['Data'] = pd.to_datetime(df_check['Data']).reset_index(drop=True)
        df_check['Time_difference'] = abs(paid_at.dt.tz_localize(None) - df_check['Data'])

        #tieni solo coppia pagamento-ordine più vicina nel tempo
        df_check2 = df_check.sort_values("Data")
        names = df_check2["Numero Pagamento"].unique()
            
        for n in names:
            f = df_check2[(df_check2["Numero Pagamento"] == n)]
            if f['Time_difference'].isna().all():
                continue  # Skip this iteration if all values are NaN
            min_days_idx = f['Time_difference'].idxmin()
            order = f.loc[min_days_idx, "Name"]
            rows_to_drop = df_check2[(df_check2["Name"] == order) & (df_check2["Numero Pagamento"] != n) | (df_check2["Name"] != order) & (df_check2["Numero Pagamento"] == n)]
            df_check2 = df_check2.drop(rows_to_drop.index, axis = 0)

        df_check2 = df_check2.drop_duplicates()
        df_check2 = df_check2[(~df_check2["Name"].isna()) & (~df_check2["Numero Pagamento"].isna())]

        #cambia check a VERO per ordini e pagamenti matchati
        nomi_vero = df_check2["Name"].unique()
        pagamenti_vero = df_check2["Numero Pagamento"].unique()

        # #add to df_check Names and Numero Pagamento that we lost in the matching
        # missing_names = set(df_ordini.Name.unique()) - set(df_check2.Name.unique())
        # missing_num = set(df["Numero Pagamento"].unique()) - set(df_check2["Numero Pagamento"].unique())

        # missing_rows_step2 = df_ordini[df_ordini["Name"].isin(missing_names)]
        # missing_rows_num = df[df["Numero Pagamento"].isin(missing_num)]
        # df_steps = pd.concat([df_check2, missing_rows_step2, missing_rows_num])

        # passiamo agli ordini che non hanno solo Qromo come metodo di pagamento
        df_mix = df[~df["Numero Pagamento"].isin(pagamenti_vero)]  
        df_ordini_suggestions = df_ordini[~df_ordini["Name"].isin(nomi_vero)]

        df_check3 = pd.merge(df_ordini_suggestions, df_mix, on= "partial_date", how='outer', suffixes=('_ordini', '_qromo'))
        df_check3 = df_check3.drop_duplicates()
        df_check3 = df_check3[~df_check3["Name"].isna()]

        #calculate time difference
        paid_at = pd.to_datetime(df_check3['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)).dt.tz_localize(None) #.reset_index(drop=True).dt.tz_localize(None) 
        df_check3['Data'] = pd.to_datetime(df_check3['Data'])#.reset_index(drop=True)
        df_check3['Time_difference'] = abs(paid_at- df_check3['Data'])
        df_check3 = df_check3.drop_duplicates()

        # df_check4 = df_check3.sort_values("Paid at")
        # names = df_check4["Name"].unique()
            
        # for n in names:
        #     f = df_check4[(df_check4["Name"] == n)]
        #     if f['Time_difference'].isna().all():
        #         continue  # Skip this iteration if all values are NaN
        #     min_days_idx = f['Time_difference'].idxmin()
        #     order = f.loc[min_days_idx, "Numero Pagamento"]
        #     rows_to_drop = df_check4[(df_check4["Numero Pagamento"] == order) & (df_check4["Name"] != n) | (df_check4["Numero Pagamento"] != order) & (df_check4["Name"] == n)]
        #     df_check4 = df_check4.drop(rows_to_drop.index, axis = 0)

        # df_check4 = df_check4.drop_duplicates()

        df_check3.loc[(df_check3["Total"] == df_check3["Importo Pagato"]), "CHECK"] = "VERO"
        df_check3.loc[(~df_check3["Numero Pagamento"].isna()) & (df_check3["Total"] != df_check3["Importo Pagato"]), "CHECK"] = "FALSO"
        df_check3.loc[(df_check3["Numero Pagamento"].isna()), "CHECK"] = "NON TROVATO"

        # Identify the names that are in df_ordini_solo but not in df_step1
        missing_names = set(df_ordini_suggestions.Name.unique()) - set(df_check3.Name.unique())
        missing_num = set(df_mix["Numero Pagamento"].unique()) - set(df_check3["Numero Pagamento"].unique())

        # Filter df_ordini_suggestions to include only the rows with missing names
        missing_rows_step3 = df_ordini_suggestions[df_ordini_suggestions["Name"].isin(missing_names)]
        missing_rows_num = df_mix[df_mix["Numero Pagamento"].isin(missing_num)]

        df_final_check = pd.concat([df_check2, df_check3, missing_rows_step3, missing_rows_num])

        df_final_check = self.apply_checks(df_final_check)
        print(df_final_check.CHECK.value_counts())

        #vedi se ci sono altri match
        tutti_nomi_vero = df_final_check[df_final_check["CHECK"] == "VERO"]["Name"].unique()
        # altri_pagamenti_vero = df_final_check[df_final_check["CHECK"] == "VERO"]["Numero Pagamento"].unique()

        PaymentMatcher.payment_info_list.append(tutti_nomi_vero)
          
        # #mergiare la lisa dei possibili pagamenti con gli ordini
        # numero_pagamento_lists = df_final_check.groupby('Name')['Numero Pagamento'].agg(list).reset_index()
        # numero_pagamento_lists = numero_pagamento_lists.rename(columns={'Numero Pagamento': 'possibili_pagamenti'})
        # df_ordini = pd.merge(df_ordini, numero_pagamento_lists, on='Name', how='left')

        # #aggiornare CHECK
        # df_ordini['possibili_pagamenti'] = df_ordini['possibili_pagamenti'].apply(lambda x: np.nan if isinstance(x, list) and all(pd.isna(i) for i in x) else x)
        # df_ordini.loc[df_ordini['possibili_pagamenti'].apply(lambda x: isinstance(x, list) and len(x) > 0), 'CHECK'] = 'FALSO'
        # df_ordini.loc[(df_ordini['possibili_pagamenti'].isna()) & (df_ordini["CHECK"] == "FALSO"), 'CHECK'] = 'NON TROVATO'

        # Create a mask for rows that contain '+' in the 'Payment Method', exclude 'Gift Card', and have 'CHECK' set to 'VERO'
        mask = (df_final_check["Payment Method"].str.contains(r'\+') &
                (df_final_check["CHECK"] == "VERO"))
    
        df_final_check.loc[mask & df_final_check["Payment Method"].str.contains('Qromo'), "Payment Method"] = "Qromo"

        df_full = pd.merge(df_full, df_final_check[["Name", "Numero Pagamento", "Brand", "CHECK"]], on = "Numero Pagamento", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Qromo"

        return df_final_check, df_full, columns

