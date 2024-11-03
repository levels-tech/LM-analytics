# paypal_matcher.py
import pandas as pd

from matcher_base import PaymentMatcher
from exceptions import SkipMatcherException


#matcher del bonifico
class BonificoMatcher(PaymentMatcher):
    
    def find_header_row(self, excel_file, column_name):

        df_sample = pd.read_excel(excel_file)  # Adjust number as needed
        header_row = 0

        dtype_dict = {"Data":str}

        # Find the row containing the known column name
        for idx, row in df_sample.iterrows():
            if column_name in row.values:
                header_row = idx + 1
                break

        df = pd.read_excel(excel_file, header=header_row, dtype=dtype_dict)
                
        return df
    


    def match(self):
        
        operations_patterns = [
            r'stripe',
            r'paypal',
            r'satispay',
            r'scalapay',
            r'rinascente',
            r'paesi ue',
            r'retail group',
            r'sportello automatico',
        ]
        
        bonifici_file = self.uploaded_files.get("Bonifici")
        
        if not bonifici_file:
            raise SkipMatcherException("Non ci sono bonifici")
        
        # Process the file and proceed with matching
        df_full = self.find_header_row(bonifici_file, "Importo")
        # df_full = self.adjust_paid_at(df_full, "Data", bonifico=True)
        columns = df_full.columns
        
        print("str 1")
        mask = ~df_full['Operazione'].str.contains('|'.join(operations_patterns), case=False, regex=True, na=False)
        df_full = df_full[mask]        
        df = df_full.copy()
        cutoff_date1 = '2024-08-27'
        df['Month'] = df['Data'].str[5:7]  # Extract the month part (MM)
        if (df['Month'] == '08').all():
            df = df[df['Data'] <= cutoff_date1]
        df = df.rename(columns={"Dettagli": "Numero Pagamento", 'Importo': 'Importo Pagato'})

        print("str 2")
        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Bonifico', case=True, na=False)]
        # df_ordini['Paid_datetime'] = pd.to_datetime(df_ordini['Paid at']).dt.tz_localize(None)

        df_check = pd.merge(df_ordini, df, left_on='Total', right_on='Importo Pagato', how='outer')
        df_check['Days_difference'] = ((pd.to_datetime(df_check['Data'], errors='coerce').dt.tz_localize(None) - pd.to_datetime(df_check['Paid at']).dt.tz_localize(None)).dt.days).abs()
        
        mask = df_check['Days_difference'].values == df_check.groupby('Name')['Days_difference'].transform('min').values
        df_check = df_check[mask | df_check['Days_difference'].isna()]

        df_check = self.apply_checks(df_check)

        print("str 3")
        mask = (df_check["Payment Method"].str.contains(r'\+') 
                & (df_check["CHECK"] == "VERO"))
        print("str 4")
        df_check.loc[mask & df_check["Payment Method"].str.contains("Bonifico"), "Payment Method"] = "Bonifico"

        df_full = pd.merge(df_full, df_check[["Name", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK", "note_interne"]], on = "Data", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Bonifico"

        return df_check, df_full, columns
