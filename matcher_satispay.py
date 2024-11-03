# paypal_matcher.py
import pandas as pd

from matcher_base import PaymentMatcher
from exceptions import SkipMatcherException
#matcher di satispay
class SatispayMatcher(PaymentMatcher):

    def match(self):

        satispay_file = self.uploaded_files.get("Satispay")
        
        if not satispay_file:
            raise SkipMatcherException("Non ci sono pagamenti con Satispay")
        
        # Process the file and proceed with matching
        df_full = pd.read_csv(satispay_file)
        columns = df_full.columns

        df = df_full[['payment_date', 'total_amount', 'description']]
        df['partial_date'] = pd.to_datetime(df['payment_date']).dt.tz_localize(None).dt.date
        df = df.rename(columns={"description": "Numero Pagamento", "payment_date": "Data", "total_amount": "Importo Pagato"})

        #Ordini online con description != 0
        df_ordini_online = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Satispay', case=False, na=False)]
        df_check_online = self.merge_dfs(df_ordini_online, df[df["Numero Pagamento"] != "0"])

        df_check_online = self.apply_checks(df_check_online, double_payments=True)

        #Ordini negozio con description = 0
        df_ordini_negozio = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Qromo', case=False, na=False)]
        df_ordini_negozio['partial_date'] = pd.to_datetime(df_ordini_negozio['Paid at']).dt.tz_localize(None).dt.date

        df_check_negozio = pd.merge(df_ordini_negozio, df[df["Numero Pagamento"] == "0"], on="partial_date", how='right')
        data_time = pd.to_datetime(df_check_negozio['Data']).dt.tz_localize(None)
        paid_time = pd.to_datetime(df_check_negozio['Paid at']).dt.tz_localize(None)
        df_check_negozio['Time_difference'] = (data_time - paid_time).abs()   

        df_check_negozio = self.apply_checks(df_check_negozio, satispay=True)

        df_check = pd.concat([df_check_online, df_check_negozio])
    
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))

        df_check.loc[mask & df_check["Payment Method"].str.contains("Satispay"), "Payment Method"] = "Satispay"

        df_full = pd.merge(df_full, df_check[["Name", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK", "note_interne"]], left_on = ["payment_date", "description"], right_on = ["Data", "Numero Pagamento"], how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Satispay"

        return df_check, df_full, columns
    