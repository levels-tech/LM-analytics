# paypal_matcher.py
import pandas as pd

from matcher_base import PaymentMatcher
from exceptions import SkipMatcherException


#matcher di qromo
class QromoMatcher(PaymentMatcher):

    def match(self, mese, anno):

        qromo_file = self.uploaded_files.get("Qromo")
        
        if not qromo_file:
            raise SkipMatcherException("Non ci sono pagamenti col POS")
        
        # Process the file and proceed with matching
        df_full = pd.read_csv(qromo_file, thousands='.')
        columns = df_full.columns
        data_interesse = f"{anno}-{mese:02}"

        df_full = df_full[df_full["Data"].str.startswith(data_interesse)]
        # df_full = self.adjust_paid_at(df_full, "Data")
        df_full = df_full[df_full["Stato"] != "Annullato"]

        df_full["Importo €"] = df_full["Importo €"].astype(float)
        df_full["Importo rimborsato €"] = df_full["Importo rimborsato €"].astype(float)
        df_full["Importo Pagato"] = df_full["Importo €"] - df_full["Importo rimborsato €"]
        df_full = df_full[df_full["Importo Pagato"] != 0]
        df_full['Numero Pagamento'] = df_full['ID'] 

        df = df_full.copy()

        cutoff_date1 = '2024-08-27 11:42:28'
        df['Month'] = df['Data'].str[5:7]  # Extract the month part (MM)
        if (df['Month'] == '08').all():
            df = df[df['Data'] <= cutoff_date1]
        
        df['partial_date'] =  pd.to_datetime(df['Data']).dt.tz_localize(None).dt.date
        df = df[["Data", "Stato", "Importo €", "Importo rimborsato €", "Importo Pagato", "Numero Pagamento", "partial_date"]]
        df = df.sort_values('Data')
        
        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Qromo', case=False, na=False)]
        # df_ordini['Paid_datetime'] = pd.to_datetime(df_ordini['Paid at']).dt.tz_localize(None)
        df_ordini['partial_date'] = pd.to_datetime(df_ordini['Paid at']).dt.tz_localize(None).dt.date
        df_ordini = df_ordini[~df_ordini["Name"].isin(PaymentMatcher.payment_info_list)]
        df_ordini = df_ordini.sort_values('Paid at')

        df_check = pd.merge(df_ordini, df, on='partial_date', how='outer', suffixes=('_qromo', '_ordini'))
        df_check = df_check.drop(columns=['partial_date'])

        df_check = self.apply_checks(df_check, qromo = True)

        # Create a mask for rows that contain '+' in the 'Payment Method', exclude 'Gift Card', and have 'CHECK' set to 'VERO'
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))
    
        df_check.loc[mask & df_check["Payment Method"].str.contains('Qromo'), "Payment Method"] = "Qromo"
        print(df_full.columns, df_check.columns)

        df_full = pd.merge(df_full, df_check[["Name", "Brand", "CHECK", "note_interne", "Data"]], on = "Data", how = "left")
        # df_full = df_full.drop("Data_datetime", axis = 1)
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Qromo"

        return df_check, df_full, columns

