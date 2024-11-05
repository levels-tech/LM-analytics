import pandas as pd

from matchers.matcher_base import PaymentMatcher
from utils.exceptions import SkipMatcherException
from utils.exceptions import DateMismatchError


#matcher di shopify   
class ShopifyMatcher(PaymentMatcher):

    def match(self, mese, anno):  

        shopify_lil_file = self.uploaded_files.get("Shopify LIL")
        shopify_agee_file = self.uploaded_files.get("Shopify AGEE")

        # assicurarsi che esista
        if shopify_lil_file:
            lil = pd.read_csv(shopify_lil_file)
        else:
            lil = pd.DataFrame()  # or handle the missing file as needed

        # assicurarsi che esista
        if shopify_agee_file:
            agee = pd.read_csv(shopify_agee_file)
        else:
            agee = pd.DataFrame()  # or handle the missing file as needed

        # Concatenate dataframes if both are available
        df_full = pd.concat([lil, agee], ignore_index=True) if len(lil) > 0 or len(agee) > 0 else pd.DataFrame()
        columns = df_full.columns
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Shopify")
        
        expected_date = f"{anno}-{mese:02}"
        df_filtered = df_full[df_full["Transaction Date"].str[:7] == expected_date].copy()
        df_na = df_full[df_full["Transaction Date"].isna()]

        if len(df_filtered) == 0:
            found_dates = sorted(df_full["Transaction Date"].str[:7].unique())
            raise DateMismatchError(
                message=f"Nessun pagamento con shopify trovato per il periodo {expected_date}",
                details=(f"Date disponibili nel file: {', '.join(found_dates)}\n"
                        "Selezionare un periodo presente nel file o caricare il file corretto."))
        else:
            df_full = pd.concat([df_filtered, df_na])
        

        # # solo per prove agosto perchè il file è troncato
        # cutoff_date1 = '2024-08-27 11:42:28'
        # df_full['Month'] = df_full['Transaction Date'].str[5:7]  # Extract the month part (MM)
        # if (df_full['Month'] == '08').all():
        #     df_full = df_full[df_full['Transaction Date'] <= cutoff_date1]
        
        
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
        
        df_full = pd.merge(df_full, df_check[["Name", "Data", "Numero Pagamento", "Importo Pagato", "Brand", "CHECK", "note_interne"]], left_on = "Order", right_on = "Numero Pagamento", how = "left")
        df_full = df_full.drop_duplicates(subset=columns)
        df_full["CHECK"] = df_full["CHECK"].fillna("NON TROVATO")
        df_full["Metodo"] = "Shopify Payments"

        return df_check, df_full, columns
