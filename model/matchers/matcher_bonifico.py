import pandas as pd

from model.matchers.matcher_base import PaymentMatcher
from model.utils.exceptions import SkipMatcherException


#matcher del bonifico
class BonificoMatcher(PaymentMatcher):
    
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
        
        df_full = self.handle_load_data("Bonifici", mese, anno)
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Bonifici")
        
        columns = df_full.columns
        
        mask = ~df_full['Operazione'].str.contains('|'.join(operations_patterns), case=False, regex=True, na=False)
        df_full = df_full[mask]

        df = df_full.copy()
        df = df.rename(columns={"Dettagli": "Numero Pagamento", 'Importo': 'Importo Pagato'})

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Bonifico', case=True, na=False)] 

        df_check = pd.merge(df_ordini, df, left_on='Total', right_on='Importo Pagato', how='outer')
        df_check = df_check.sort_values(by='Data')
        
        paid_at = df_check['Paid at'].str.replace(r'\s[+-]\d{4}$', '', regex=True)
        df_check['Time_difference'] = (pd.to_datetime(paid_at).dt.tz_localize(None) - pd.to_datetime(df_check['Data'], errors='coerce').dt.tz_localize(None)).dt.days
        df_check = df_check[(df_check['Time_difference'] >= 0) | df_check['Time_difference'].isna()]
        print("BONIFICO URGENTE", df_check[["Name", "Total", "CHECK", "Time_difference"]])
        
        # Find the minimum Days_difference for each "Numero Pagamento"
        df_check = self.apply_checks(df_check, bonifico = True)

        mask = (df_check["Payment Method"].str.contains(r'\+') 
                & (df_check["CHECK"] == "VERO"))
        df_check.loc[mask & df_check["Payment Method"].str.contains("Bonifico"), "Payment Method"] = "Bonifico"

        df_full = pd.merge(df_full, df_check[["Name", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK"]], left_on = "Dettagli", right_on = "Numero Pagamento", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Bonifico"
        print("BONIFICO URGENTE", df_check[["Name", "Total", "CHECK"]])

        return df_check, df_full, columns
