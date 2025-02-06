import streamlit as st
import math

PAYMENTS_PER_PAGE = 3  # Numero di pagamenti da mostrare per pagina

def init_pagination_state():
    """Inizializza lo stato della paginazione se non esiste"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'items_per_page' not in st.session_state:
        st.session_state.items_per_page = PAYMENTS_PER_PAGE

def get_paginated_payments(pagamenti_df, page, items_per_page):
    """
    Restituisce una porzione del DataFrame dei pagamenti basata sulla paginazione
    """
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    return pagamenti_df.iloc[start_idx:end_idx].copy()

def render_pagination_controls(total_items, items_per_page):
    """
    Renderizza i controlli di paginazione e gestisce la navigazione
    """
    total_pages = math.ceil(total_items / items_per_page)
    
    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 2])
    
    with col1:
        if st.button("⏮️ Prima", disabled=st.session_state.current_page == 1):
            st.session_state.current_page = 1
            st.rerun()
    
    with col2:
        if st.button("◀️", disabled=st.session_state.current_page == 1):
            st.session_state.current_page -= 1
            st.rerun()
    
    with col3:
        st.write(f"Pagina {st.session_state.current_page} di {total_pages}")
    
    with col4:
        if st.button("▶️", disabled=st.session_state.current_page == total_pages):
            st.session_state.current_page += 1
            st.rerun()
    
    with col5:
        if st.button("⏭️ Ultima", disabled=st.session_state.current_page == total_pages):
            st.session_state.current_page = total_pages
            st.rerun()

def handle_paginated_payments(pagamenti_da_ricontrollare_df, num_pagamenti_totale):
    """
    Gestisce la visualizzazione paginata dei pagamenti
    """
    init_pagination_state()
    
    # Mostra il conteggio totale dei pagamenti
    st.write("")
    st.subheader("Pagamenti da controllare")
    num_pagamenti_da_ricontrollare = len(pagamenti_da_ricontrollare_df)
    st.write(f"{num_pagamenti_da_ricontrollare} pagamenti su {num_pagamenti_totale}")
    
    # Ottiene i pagamenti per la pagina corrente
    paginated_df = get_paginated_payments(
        pagamenti_da_ricontrollare_df, 
        st.session_state.current_page,
        st.session_state.items_per_page
    )
    
    # Renderizza i controlli di paginazione
    render_pagination_controls(
        len(pagamenti_da_ricontrollare_df),
        st.session_state.items_per_page
    )
    
    return paginated_df