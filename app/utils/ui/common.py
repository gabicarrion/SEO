# utils/ui/common.py
import streamlit as st
import pandas as pd
from utils.export import export_to_excel

def create_filters_container(filter_options):
    """Create a container for filters"""
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    result = st.columns(len(filter_options))
    st.markdown('</div>', unsafe_allow_html=True)
    return result

def create_download_button(df, filename, button_text="Download", key=None):
    """Create a download button for a dataframe"""
    return st.download_button(
        button_text,
        export_to_excel(df),
        filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key
    )

def create_expander_with_title(title, expanded=False):
    """Create an expander with formatted title"""
    return st.expander(title, expanded=expanded)