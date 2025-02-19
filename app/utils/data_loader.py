import pandas as pd
import streamlit as st
import numpy as np

def clean_category_values(series):
    """Clean category values by replacing NA/NaN with 'Uncategorized'"""
    return series.fillna('Uncategorized')

def process_semrush_categories(df):
    """Process SemRush data to handle multiple categories per issue"""
    # Create expanded dataframe with split categories
    expanded_rows = []
    for _, row in df.iterrows():
        if pd.notna(row['Issue category - SemRush']) and row['Issue category - SemRush'] != 'NA':
            categories = [cat.strip() for cat in str(row['Issue category - SemRush']).split(',')]
            for category in categories:
                if category and category != 'Uncategorized':  # Skip empty and Uncategorized categories
                    new_row = row.copy()
                    new_row['Issue category - SemRush'] = category
                    expanded_rows.append(new_row)
    
    return pd.DataFrame(expanded_rows)

def get_issue_stats(issues_df):
    """Calculate issue statistics by type"""
    return {
        'Issues': len(issues_df[issues_df['Issue Type - SemRush'] == 'Error']),
        'Warnings': len(issues_df[issues_df['Issue Type - SemRush'] == 'Warning']),
        'Notices': len(issues_df[issues_df['Issue Type - SemRush'] == 'Notice'])
    }

def load_mapping_data(file_path):
    """Load the mapping between SemRush and Screaming Frog issues"""
    try:
        df = pd.read_csv(file_path)
        # Clean up category values
        df['Issue category - SemRush'] = clean_category_values(df['Issue category - SemRush'])
        df['Issue Type - SemRush'] = clean_category_values(df['Issue Type - SemRush'])
        df['Issue Type - ScreamingFrog'] = clean_category_values(df['Issue Type - ScreamingFrog'])
        return df
    except Exception as e:
        st.error(f"Error loading mapping file: {str(e)}")
        return None

def load_sf_issues(file):
    """Load Screaming Frog issues overview"""
    try:
        df = pd.read_csv(file)
        # Convert percentage string to float, handling commas
        df['% of Total'] = df['% of Total'].str.replace(',', '.').astype(float)
        # Clean up categorical columns
        df['Issue Type'] = clean_category_values(df['Issue Type'])
        df['Issue Priority'] = clean_category_values(df['Issue Priority'])
        return df
    except Exception as e:
        st.error(f"Error loading Screaming Frog issues: {str(e)}")
        return None

def load_semrush_data(file):
    """Load SemRush export data"""
    try:
        df = pd.read_csv(file)
        # Clean categorical columns if they exist
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = clean_category_values(df[col])
        return df
    except Exception as e:
        st.error(f"Error loading SemRush file: {str(e)}")
        return None