import pandas as pd

from matchers.matcher_base import PaymentMatcher
from utils.exceptions import SkipMatcherException
from utils.exceptions import DateMismatchError


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
    


    def match(self, mese, anno):
        
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
        columns = df_full.columns
        
        mask = ~df_full['Operazione'].str.contains('|'.join(operations_patterns), case=False, regex=True, na=False)
        df_full = df_full[mask]
        print(len(df_full))

        # Format month for comparison
        expected_date = f"{anno}-{mese:02}"
        found_dates = sorted(df_full["Data"].str[:7].unique())
        df_na = df_full[df_full["Data"].isna()]
        df_filtered = df_full[df_full["Data"].str[:7] == expected_date].copy()

        if len(df_filtered) == 0:
            found_dates = sorted(df_full["Data"].str[:7].unique())
            raise DateMismatchError(
                message=f"Nessun pagamento con bonifico trovato per il periodo {expected_date}",
                details=(f"Date disponibili nel file: {', '.join(found_dates)}\n"
                        "Selezionare un periodo presente nel file o caricare il file corretto."))
        else:
            df_full = pd.concat([df_filtered, df_na])

        # # solo per prove agosto perchè il file è troncato
        # cutoff_date1 = '2024-08-27'   
        # df_full['Month'] = df_full['Data'].str[5:7]  # Extract the month part (MM)
        # if (df_full['Month'] == '08').all():
        #     df_full = df_full[df_full['Data'] <= cutoff_date1]    
        
        df = df_full.copy()
        df = df.rename(columns={"Dettagli": "Numero Pagamento", 'Importo': 'Importo Pagato'})

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Bonifico', case=True, na=False)]

        df_check = pd.merge(df_ordini, df, left_on='Total', right_on='Importo Pagato', how='outer')
        paid_at = df_check['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)
        df_check['Days_difference'] = ((pd.to_datetime(df_check['Data'], errors='coerce').dt.tz_localize(None) - pd.to_datetime(paid_at).dt.tz_localize(None)).dt.days).abs()
        
        mask = df_check['Days_difference'].values == df_check.groupby('Name')['Days_difference'].transform('min').values
        df_check = df_check[mask | df_check['Days_difference'].isna()]

        df_check = self.apply_checks(df_check)

        mask = (df_check["Payment Method"].str.contains(r'\+') 
                & (df_check["CHECK"] == "VERO"))
        df_check.loc[mask & df_check["Payment Method"].str.contains("Bonifico"), "Payment Method"] = "Bonifico"

        df_full = pd.merge(df_full, df_check[["Name", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK", "note_interne"]], on = "Data", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Bonifico"

        return df_check, df_full, columns
