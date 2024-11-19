import pandas as pd

from model.matchers.matcher_base import PaymentMatcher
from model.utils.exceptions import SkipMatcherException

#matcher di shopify   
class ShopifyMatcher(PaymentMatcher):

    def match(self, mese, anno):  

        lil = self.handle_load_data("Shopify LIL", mese, anno)
        agee =  self.handle_load_data("Shopify AGEE", mese, anno)

        # Concatenate dataframes if both are available
        df_full = pd.concat([lil, agee], ignore_index=True) if len(lil) > 0 or len(agee) > 0 else pd.DataFrame()
        columns = df_full.columns
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Shopify")
        
        df = df_full.groupby('Order', as_index=False).agg({'Amount': 'sum',        # Sum the 'Lordo' values
                                                            'Transaction Date': 'first',      # Take the first 'Valuta' value for each group
                                                            })

        df = df.rename(columns={"Transaction Date": "Data", "Order": "Numero Pagamento", "Amount": "Importo Pagato"})

        df_ordini = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Shopify', case=False, na=False)]

        df_check = pd.merge(df_ordini, df, left_on="Name", right_on="Numero Pagamento", how='outer')
        df_check = self.apply_checks(df_check)
        
        mask = (df_check["Payment Method"].str.contains(r'\+') &
                (df_check["CHECK"] == "VERO"))
        df_check.loc[mask & df_check["Payment Method"].str.contains("Shopify Payments"), "Payment Method"] = "Shopify Payments"
        
        df_full = pd.merge(df_full, df_check[["Name", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK"]], left_on = "Order", right_on = "Numero Pagamento", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Shopify Payments"

        return df_check, df_full, columns
