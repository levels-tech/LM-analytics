import pandas as pd

from model.matchers.matcher_base import PaymentMatcher
from model.utils.exceptions import SkipMatcherException


#matcher di paypal   
class PaypalMatcher(PaymentMatcher):
    """matcher di paypal"""

    def match(self, mese, anno):

        df_full = self.handle_load_data("Paypal", mese, anno)
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Paypal")
        
        columns = df_full.columns
        
        df_full['Lordo'] = df_full['Lordo'].str.replace('.', '', regex=False)  # Remove periods (thousands separator)
        df_full['Lordo'] = df_full['Lordo'].str.replace(',', '.', regex=False)  # Replace commas with periods (decimal separator)
        df_full['Lordo'] = pd.to_numeric(df_full['Lordo'], errors='coerce')  # Convert to numeric, coercing errors to NaN        
        df_full = df_full[df_full["Tipo"].isin(["Pagamento Express Checkout", "Rimborso di pagamento"])]
        df_full = df_full[~df_full["Nome"].str.contains("propac", case=False, na=False)] #ha detto di toglierlo

        df = df_full[['Data', "Nome", "Tipo", 'Valuta', 'Lordo', 'N° ordine commerciante', "Titolo oggetto"]]
        df = df.groupby('N° ordine commerciante', as_index=False).agg({'Lordo': 'sum',        # Sum the 'Lordo' values
                                                                               'Valuta': 'first',      # Take the first 'Valuta' value for each group
                                                                               "Data": "first"})
        
        # Using a dictionary where keys are old names and values are new names
        df = df.rename(columns={'N° ordine commerciante': 'Numero Pagamento', 'Lordo': 'Importo Pagato'})

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Paypal', case=False, na=False)]

        df_check = self.merge_dfs(df_ordini, df)
       
        df_check = self.apply_checks(df_check, valuta=True, double_payments=True)

        mask = (df_check["Payment Method"].str.contains(r'\+') 
                & (df_check["CHECK"] == "VERO"))
        df_check.loc[mask & df_check["Payment Method"].str.contains("PayPal Express Checkout"), "Payment Method"] = "PayPal Express Checkout" 

        df_full = pd.merge(df_full, df_check[["Name", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK"]], left_on = 'N° ordine commerciante', right_on = "Numero Pagamento", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "PayPal Express Checkout"

        return df_check, df_full, columns