import pandas as pd

from model.matchers.matcher_base import PaymentMatcher
from model.utils.exceptions import SkipMatcherException


#matcher di scalapay
class ScalapayMatcher(PaymentMatcher):

    def match(self, mese, anno):

        df_full = self.handle_load_data("Scalapay", mese, anno)
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Scalapay")
        
        columns = df_full.columns

        df = df_full.groupby('Merchant ID', as_index=False, dropna=False).agg({'Import lordo': 'sum',        # Sum the 'Lordo' values
                                                                                'Data acquisto/rimborso': 'first',      # Take the first 'Valuta' value for each group
                                                                                })

        df = df.rename(columns={'Merchant ID': "Numero Pagamento", "Data acquisto/rimborso": "Data", "Import lordo": "Importo Pagato"})

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Scalapay', case=False, na=False)]

        # Check orders with double reference
        df_check = self.merge_dfs(df_ordini, df)

        df_check = self.apply_checks(df_check, double_payments=True)

        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))

        df_check.loc[mask & df_check["Payment Method"].str.contains("Scalapay"), "Payment Method"] = "Scalapay"

        df_full = pd.merge(df_full, df_check[["Name", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK"]], left_on = 'Merchant ID', right_on = "Numero Pagamento", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Scalapay"

        return df_check, df_full, columns
  