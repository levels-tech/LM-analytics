import streamlit as st
import math

def init_pagination_state(section_key):
    """
    Inizializza lo stato della paginazione per una sezione specifica se non esiste
    
    Args:
        section_key (str): Identificatore unico della sezione ('lil', 'agee', or 'payments')
    """
    if f'current_page_{section_key}' not in st.session_state:
        st.session_state[f'current_page_{section_key}'] = 1
    if f'items_per_page_{section_key}' not in st.session_state:
        st.session_state[f'items_per_page_{section_key}'] = 3  # Default items per page

def get_paginated_items(items_df, section_key):
    """
    Restituisce una porzione del DataFrame basata sulla paginazione
    
    Args:
        items_df: DataFrame contenente tutti gli items
        section_key (str): Identificatore della sezione
    """
    current_page = st.session_state[f'current_page_{section_key}']
    items_per_page = st.session_state[f'items_per_page_{section_key}']
    
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    return items_df.iloc[start_idx:end_idx].copy()

def render_pagination_controls(total_items, section_key):
    """
    Renderizza i controlli di paginazione e gestisce la navigazione
    
    Args:
        total_items (int): Numero totale di items
        section_key (str): Identificatore della sezione
    """
    items_per_page = st.session_state[f'items_per_page_{section_key}']
    current_page = st.session_state[f'current_page_{section_key}']
    
    total_pages = math.ceil(total_items / items_per_page)
    
    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 2])
    
    with col1:
        if st.button("⏮️ Prima", 
                    disabled=current_page == 1,
                    key=f'widget_first_{section_key}'):
            st.session_state[f'current_page_{section_key}'] = 1
            st.rerun()
    
    with col2:
        if st.button("◀️", 
                    disabled=current_page == 1,
                    key=f'widget_prev_{section_key}'):
            st.session_state[f'current_page_{section_key}'] -= 1
            st.rerun()
    
    with col3:
        st.write(f"Pagina {current_page} di {total_pages}")
    
    with col4:
        if st.button("▶️", 
                    disabled=current_page == total_pages,
                    key=f'widget_next_{section_key}'):
            st.session_state[f'current_page_{section_key}'] += 1
            st.rerun()
    
    with col5:
        if st.button("⏭️ Ultima", 
                    disabled=current_page == total_pages,
                    key=f'widget_last_{section_key}'):
            st.session_state[f'current_page_{section_key}'] = total_pages
            st.rerun()

def handle_paginated_section(items_df, total_items, section_key, section_title):
    """
    Gestisce la visualizzazione paginata per una sezione
    
    Args:
        items_df: DataFrame contenente gli items da mostrare
        total_items (int): Numero totale di items
        section_key (str): Identificatore della sezione
        section_title (str): Titolo da mostrare per la sezione
    """
    init_pagination_state(section_key)
    
    st.write("")
    st.subheader(section_title)
    num_items = len(items_df)
    st.write(f"{num_items} elementi su {total_items}")
    
    paginated_df = get_paginated_items(items_df, section_key)
    
    render_pagination_controls(num_items, section_key)
    
    return paginated_df