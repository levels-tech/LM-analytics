import pandas as pd
import streamlit as st


class OrderWidgets:
    """Classe per gestire i widget comuni della sezione ordini"""
    
    @staticmethod
    def create_lineitem_input(column: str, name: str, row: pd.Series, row_index: int) -> tuple:
        """
        Crea input widget per campi Lineitem
        Returns: (widget_key, new_value)
        """
        input_key = f"widget_{column}_{name}_{row_index}"
        current_value = row[column]

        if column == "Lineitem quantity":
            
            new_value = st.number_input(
                f"Valore per {column} - {row['Lineitem name']}: {current_value}",
                value=current_value if pd.notna(current_value) else 0,
                step=1.0,
                format="%.0f",
                key=input_key
            )
            
        elif column == "Lineitem price":
            new_value = st.number_input(
                f"Valore per {column} - {row['Lineitem name']}: {current_value}", 
                value=current_value if pd.notna(current_value) else 0,
                step=None,
                format="%.2f", 
                key=input_key
            )
            
        elif column == "Lineitem sku":
            new_value = st.text_input(
                f'Valore per {column} - {row["Lineitem name"]}: {current_value}' 
                if not pd.isna(current_value) 
                else f'Inserire {column} per {row["Lineitem name"]}:',
                value=str(current_value) if not pd.isna(current_value) else "015790000000",
                key=input_key
            )
        
        elif column == "Lineitem name":
            new_value = st.text_input(
                f"Valore attuale per {column} - {row['Lineitem sku']}: {current_value}",
                value=str(current_value),
                key=input_key
            )
            
        else:
            new_value = st.text_input(
                f"Valore per {column} - {row['Lineitem name']}: {current_value}",
                value=str(current_value),
                key=input_key
            )
            
        return new_value

    @staticmethod
    def create_payment_method_input(name: str, current_value: str, payment_options: list) -> str:
        """Crea select box per metodo pagamento"""
        input_key = f"widget_Payment Method_{name}_0"
        return st.selectbox(
            "Seleziona Payment Method:",
            options=payment_options,
            index=0 if pd.isna(current_value) or not payment_options else 0,
            key=input_key
        )

    @staticmethod
    def create_total_input(name: str, current_value: float, importo_pagato: float) -> float:
        """Crea number input per totale"""
        input_key = f"widget_Total_{name}_0"
        return st.number_input(
            f"Valore attuale Total: {current_value}",
            value=importo_pagato if pd.notna(importo_pagato) else 0.0,
            step=None,
            format="%.2f",
            key=input_key
        )

    @staticmethod
    def create_location_input(name: str, current_value: str, locations: list) -> str:
        """Crea select box per location"""
        input_key = f"widget_Location_{name}_0"
        return st.selectbox(
            "Seleziona Location:",
            options=locations,
            index=0 if pd.isna(current_value) else locations.index(current_value),
            key=input_key
        )
