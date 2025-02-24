# utils/ui/comparison_tab.py
import streamlit as st
import pandas as pd
from utils.ui.common import create_download_button

def get_matched_issues(mapping_data):
    """Get issues that are mapped between SemRush and Screaming Frog"""
    return mapping_data[
        (mapping_data['Issue Name Contains - SemRush'] != 'NA') & 
        (mapping_data['Issue Name - ScreamingFrog'] != 'NA')
    ]

def display_summary_metrics(matched_issues, mapping_data):
    """Display summary metrics for the tool comparison"""
    st.subheader("📊 Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Mapped Issues", len(matched_issues))
        st.metric("Unique SemRush Issues", 
                len(mapping_data[mapping_data['Issue Name Contains - SemRush'] != 'NA']))
    
    with col2:
        st.metric("Issues Found in Both Tools", 
                len(matched_issues[matched_issues['Issue Name - ScreamingFrog'] != 'NA']))
        st.metric("Unique ScreamingFrog Issues",
                len(mapping_data[mapping_data['Issue Name - ScreamingFrog'] != 'NA']))

def display_issue_mapping(matched_issues):
    """Display the mapping between SemRush and Screaming Frog issues"""
    st.subheader("🔄 Issue Mapping")
    
    for _, row in matched_issues.iterrows():
        with st.expander(f"🔍 {row['Issue Name Contains - SemRush']} / {row['Issue Name - ScreamingFrog']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### SemRush")
                st.markdown(f"""
                    **Type:** {row['Issue Type - SemRush']}  
                    **Category:** {row['Issue category - SemRush']}  
                    **Description:** {row['Issue description - SemRush']}  
                    **How to fix:** {row['How to fix - SemRush']}
                """)
            
            with col2:
                st.markdown("### Screaming Frog")
                st.markdown(f"""
                    **Type:** {row['Issue Type - ScreamingFrog']}  
                    **Priority:** {row['Issue Priority - ScreamingFrog']}  
                    **Description:** {row['Description ScreamingFrog']}  
                    **How to fix:** {row['How To Fix - ScreamingFrog']}
                """)

def render_comparison_tab(mapping_data):
    """Render the comparison tab content"""
    st.header("Tool Comparison")
    
    # Get matched issues
    matched_issues = get_matched_issues(mapping_data)
    
    if not matched_issues.empty:
        # Export button
        create_download_button(
            matched_issues,
            "tool_comparison.xlsx",
            "Export Comparison Data"
        )
        
        # Display summary metrics
        display_summary_metrics(matched_issues, mapping_data)
        
        # Display issue mapping
        display_issue_mapping(matched_issues)
    else:
        st.info("No matching issues found between SemRush and Screaming Frog.")