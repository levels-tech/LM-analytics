import pandas as pd

from model.matchers.matcher_base import PaymentMatcher
from model.utils.exceptions import SkipMatcherException


#matcher del bonifico
class CashMatcher(PaymentMatcher):
    
    def match(self, mese, anno):
        
        df_full, columns = self.handle_load_data("Bonifici", mese, anno)
        
        if len(df_full) == 0:
            raise SkipMatcherException("Non ci sono pagamenti con Bonifici")
        
        mask = df_full['Operazione'] == "Versamento Contanti Su Sportello Automatico"
        df_full = df_full[mask]

        df_check = self.df_ordini[self.df_ordini['Payment Method'].str.contains('Cash', case=True, na=False)] 
    
        df_full["Metodo"] = "Cash"

        return df_check, df_full, columns
