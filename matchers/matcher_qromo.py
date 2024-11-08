import pandas as pd

from matchers.matcher_base import PaymentMatcher
from utils.exceptions import SkipMatcherException
from utils.exceptions import DateMismatchError


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
        df_ordini = df_ordini[~df_ordini["Name"].isin(PaymentMatcher.payment_info_list)]
        df_ordini = df_ordini.sort_values('Paid at')

        df_check = pd.merge(df_ordini, df, on='partial_date', how='outer', suffixes=('_qromo', '_ordini'))
        df_check = df_check.drop(columns=['partial_date'])

        # df_check['Time_difference'] = pd.to_datetime(paid_at, errors="coerce").dt.tz_localize(None) - pd.to_datetime(df_check['Data']).dt.tz_localize(None)
        # df_check = df_check[(df_check['Time_difference'] >= pd.Timedelta(0)) | df_check['Time_difference'].isna()]

        df_check = self.apply_checks(df_check, qromo = True)

        # Create a mask for rows that contain '+' in the 'Payment Method', exclude 'Gift Card', and have 'CHECK' set to 'VERO'
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))
    
        df_check.loc[mask & df_check["Payment Method"].str.contains('Qromo'), "Payment Method"] = "Qromo"

        df_full = pd.merge(df_full, df_check[["Name", "Brand", "CHECK", "Data"]], on = "Data", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Qromo"

        return df_check, df_full, columns

