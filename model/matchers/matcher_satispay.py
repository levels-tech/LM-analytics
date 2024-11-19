import pandas as pd

from model.matchers.matcher_base import PaymentMatcher
from model.utils.exceptions import SkipMatcherException

#matcher di satispay
class SatispayMatcher(PaymentMatcher):

    def match(self, mese, anno):

        df_full = self.handle_load_data("Satispay", mese, anno)
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Satispay")
        
        columns = df_full.columns

        df = df_full[['payment_uid', 'payment_date', 'total_amount', 'description']]
        df['partial_date'] = pd.to_datetime(df['payment_date']).dt.tz_localize(None).dt.date
        df = df.rename(columns={"description": "Numero Pagamento", "payment_date": "Data", "total_amount": "Importo Pagato"})
        df_online = df[df["Numero Pagamento"] != "0"]
        
        #Ordini online con description != 0
        df_ordini_online = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Satispay', case=False, na=False)]
        df_check_online = self.merge_dfs(df_ordini_online, df_online)

        df_check_online = self.apply_checks(df_check_online, double_payments=True)

        #Ordini negozio con description = 0
        df_ordini_negozio = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Qromo', case=False, na=False)] 
        df_ordini_negozio = df_ordini_negozio[~df_ordini_negozio["Name"].isin(PaymentMatcher.payment_info_list)]

        paid_at = df_ordini_negozio['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)
        df_ordini_negozio['partial_date'] = pd.to_datetime(paid_at).dt.tz_localize(None).dt.date
        df_ordini_negozio = df_ordini_negozio.sort_values('Paid at')

        #nuova logica matching
        df_negozio = df[df["Numero Pagamento"] == "0"]
        df_ordini_negozio_solo = df_ordini_negozio.loc[df_ordini_negozio["Payment Method"] == "Qromo"]

        df_check_negozio = pd.merge(df_ordini_negozio_solo, df_negozio, left_on=['partial_date', "Total"], right_on = ["partial_date", "Importo Pagato"], how='right', suffixes=('_ordini', '_satispay'))
        
        # create Time_difference
        paid_at = pd.to_datetime(df_check_negozio['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)).reset_index(drop=True)
        data_at = pd.to_datetime(df_check_negozio['Data']).reset_index(drop=True)
        df_check_negozio['Time_difference'] = abs(paid_at.dt.tz_localize(None) - data_at)

        #tieni solo coppia pagamento-ordine più vicina nel tempo
        df_check2 = df_check_negozio.sort_values("Data")
        names = df_check2["payment_uid"].unique()
            
        for n in names:
            f = df_check2[(df_check2["payment_uid"] == n)]
            if f['Time_difference'].isna().all():
                continue  # Skip this iteration if all values are NaN
            min_days_idx = f['Time_difference'].idxmin()
            order = f.loc[min_days_idx, "Name"]
            rows_to_drop = df_check2[(df_check2["Name"] == order) & (df_check2["payment_uid"] != n) | (df_check2["Name"] != order) & (df_check2["payment_uid"] == n)]
            df_check2 = df_check2.drop(rows_to_drop.index, axis = 0)

        df_check2 = df_check2.drop_duplicates()
        df_check2 = df_check2[(~df_check2["Name"].isna()) & (~df_check2["payment_uid"].isna())]

        #cambia check a VERO per ordini e pagamenti matchati
        nomi_vero = df_check2["Name"].unique()
        pagamenti_vero = df_check2["payment_uid"].unique()

        # passiamo agli ordini che non hanno solo Qromo come metodo di pagamento
        df_mix = df_negozio[~df_negozio["payment_uid"].isin(pagamenti_vero)] 
        df_ordini_suggestions = df_ordini_negozio[~df_ordini_negozio["Name"].isin(nomi_vero)]

        df_check3 = pd.merge(df_ordini_suggestions, df_mix, on= "partial_date", how='outer', suffixes=('_ordini', '_satispay'))
        df_check3 = df_check3.drop_duplicates()
        df_check3 = df_check3[~df_check3["Name"].isna()]

        #calculate time difference
        paid_at = pd.to_datetime(df_check3['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)).dt.tz_localize(None) #.reset_index(drop=True).dt.tz_localize(None) 
        data_at = pd.to_datetime(df_check3['Data'])#.reset_index(drop=True)
        df_check3['Time_difference'] = abs(paid_at - data_at)
        df_check3 = df_check3.drop_duplicates()

        df_check3.loc[(df_check3["Total"] == df_check3["Importo Pagato"]), "CHECK"] = "VERO"
        df_check3.loc[(~df_check3["payment_uid"].isna()) & (df_check3["Total"] != df_check3["Importo Pagato"]), "CHECK"] = "FALSO"
        df_check3.loc[(df_check3["payment_uid"].isna()), "CHECK"] = "NON TROVATO"
        print(df_check3[df_check3["payment_uid"] == "f4924aa1-79ec-4e55-980f-be0a32016c38"])

        # Identify the names that are in df_ordini_solo but not in df_step1
        missing_names = set(df_ordini_suggestions.Name.unique()) - set(df_check3.Name.unique())
        missing_num = set(df_mix["payment_uid"].unique()) - set(df_check3["payment_uid"].unique())
        print(df_mix[df_mix["payment_uid"] == "f4924aa1-79ec-4e55-980f-be0a32016c38"])

        # Filter df_ordini_suggestions to include only the rows with missing names
        missing_rows_step3 = df_ordini_suggestions[df_ordini_suggestions["Name"].isin(missing_names)]
        missing_rows_num = df_mix[df_mix["payment_uid"].isin(missing_num)]

        df_final_check = pd.concat([df_check2, df_check3, missing_rows_step3, missing_rows_num])
        print(df_final_check[df_final_check["payment_uid"] == "f4924aa1-79ec-4e55-980f-be0a32016c38"])

        df_final_check = self.apply_checks(df_final_check)
        df_final_check = df_final_check[(df_final_check["CHECK"] == "VERO") | (~df_final_check["Numero Pagamento"].isna())]
        print(df_final_check[df_final_check["payment_uid"] == "f4924aa1-79ec-4e55-980f-be0a32016c38"])

        # Drop the unwanted columns in both DataFrames before concatenation
        df_check_online = df_check_online.drop(columns=["partial_date", "Matched Reference"], errors='ignore')
        df_final_check = df_final_check.drop(columns=["partial_date", "Time_difference"], errors='ignore')

        df_check = pd.concat([df_check_online, df_final_check])
        print(df_check[["Importo Pagato", "Data"]])
        print(df_check[df_check["payment_uid"] == "f4924aa1-79ec-4e55-980f-be0a32016c38"])

        #vedi se ci sono altri match
        # altri_nomi_vero = df_final_check[df_final_check["CHECK"] == "VERO"]["Name"].unique()
        # altri_pagamenti_vero = df_final_check[df_final_check["CHECK"] == "VERO"]["Numero Pagamento"].unique()

        # #mergiare la lisa dei possibili pagamenti con gli ordini
        # numero_pagamento_lists = df_final_check.groupby('Name')['Numero Pagamento'].agg(list).reset_index()
        # numero_pagamento_lists = numero_pagamento_lists.rename(columns={'Numero Pagamento': 'possibili_pagamenti'})
        # df_ordini = pd.merge(df_ordini, numero_pagamento_lists, on='Name', how='left')

        # #aggiornare CHECK
        # df_ordini['possibili_pagamenti'] = df_ordini['possibili_pagamenti'].apply(lambda x: np.nan if isinstance(x, list) and all(pd.isna(i) for i in x) else x)
        # df_ordini.loc[df_ordini['possibili_pagamenti'].apply(lambda x: isinstance(x, list) and len(x) > 0), 'CHECK'] = 'FALSO'
        # df_ordini.loc[(df_ordini['possibili_pagamenti'].isna()) & (df_ordini["CHECK"] == "FALSO"), 'CHECK'] = 'NON TROVATO'

        # Create a mask for rows that contain '+' in the 'Payment Method', exclude 'Gift Card', and have 'CHECK' set to 'VERO'  
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))

        df_check.loc[mask & df_check["Payment Method"].str.contains("Satispay"), "Payment Method"] = "Satispay"

        df_full = pd.merge(df_full, df_check[["Name", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK"]], left_on = ["payment_date", "description"], right_on = ["Data", "Numero Pagamento"], how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Satispay"

        return df_check, df_full, columns
    