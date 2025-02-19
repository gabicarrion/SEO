import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import base64
from pathlib import Path
import uuid

# Import utility functions
from utils.data_loader import (
    load_mapping_data, 
    load_sf_issues, 
    load_semrush_data,
    process_semrush_categories,
    get_issue_stats
)
from utils.export import export_to_excel
from utils.visualizations import create_issues_chart, create_comparison_chart, create_priority_pie_chart



# Constants
MAPPING_FILE = Path("data/mapping/SemRush vs. ScreamingFrog.csv")

def create_download_link(df, filename):
    """Create a download link for a dataframe"""
    excel_data = export_to_excel(df)
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Download {filename}</a>'
    return href

def main():
    st.set_page_config(page_title="SEO Audit Comparison", layout="wide")
    
    # Custom CSS
    st.markdown("""
        <style>
        .issue-card {
            padding: 20px;
            border-radius: 5px;
            background-color: #f8f9fa;
            margin: 10px 0;
            border-left: 4px solid #1f77b4;
        }
        .priority-high { border-left-color: #dc3545; }
        .priority-medium { border-left-color: #ffc107; }
        .priority-low { border-left-color: #28a745; }
        .filter-container {
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin: 10px 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🔍 SEO Audit Comparison Dashboard")
    
    # Sidebar inputs
    with st.sidebar:
        st.header("Input Files")
        domain = st.text_input("Domain", "example.com")
        audit_date = st.date_input("Audit Date", datetime.now())
        
        semrush_file = st.file_uploader("Upload SemRush Export", type=['csv'])
        sf_file = st.file_uploader("Upload Screaming Frog Issues", type=['csv'])
        
        st.header("Filters")
        st.session_state.show_filters = st.checkbox("Show Filters", True)
    
    # Load mapping data
    mapping_data = load_mapping_data(MAPPING_FILE)
    
    if mapping_data is not None and semrush_file and sf_file:
        semrush_data = load_semrush_data(semrush_file)
        sf_issues = load_sf_issues(sf_file)
        
        if semrush_data is not None and sf_issues is not None:
            # Create tabs
            tab1, tab2, tab3 = st.tabs(["SemRush Audit Results", 
                                       "ScreamingFrog Internal Audit Results",
                                       "Comparison"])
            
            with tab1:
                st.header("SemRush Audit Results")
                
                # Process data to handle multiple categories
                semrush_issues = process_semrush_categories(mapping_data[mapping_data['Issue Type - SemRush'] != 'NA'])
                
                # Filters
                if st.session_state.show_filters:
                    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        # Get unique categories, excluding NA/None/Uncategorized values
                        categories = sorted([cat for cat in semrush_issues['Issue category - SemRush'].unique() 
                                        if pd.notna(cat) and cat != 'Uncategorized'])
                        selected_categories = st.multiselect(
                            "Filter by Category",
                            options=categories,
                            default=[]
                        )
                    with col2:
                        # Get unique types, excluding NA/None/Uncategorized values
                        types = sorted([t for t in semrush_issues['Issue Type - SemRush'].unique() 
                                    if pd.notna(t) and t != 'Uncategorized'])
                        selected_types = st.multiselect(
                            "Filter by Type",
                            options=types,
                            default=[]
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Filter data
                filtered_semrush = semrush_issues.copy()
                if selected_categories:
                    filtered_semrush = filtered_semrush[
                        filtered_semrush['Issue category - SemRush'].isin(selected_categories)
                    ]
                if selected_types:
                    filtered_semrush = filtered_semrush[
                        filtered_semrush['Issue Type - SemRush'].isin(selected_types)
                    ]
                
                # Export button for all filtered issues
                if not filtered_semrush.empty:
                    st.download_button(
                        "📥 Export All SemRush Issues",
                        export_to_excel(filtered_semrush),
                        "semrush_issues.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_semrush_all"
                    )
                
                # Create horizontal bar chart
                if not filtered_semrush.empty:
                    # Count issues by category
                    categories_count = filtered_semrush.groupby('Issue category - SemRush').size().reset_index(name='count')
                    
                    # Create interactive horizontal bar chart
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        y=categories_count['Issue category - SemRush'],
                        x=categories_count['count'],
                        orientation='h',
                        text=categories_count['count'],
                        textposition='auto',
                    ))
                    
                    fig.update_layout(
                        title='Issues by Category',
                        yaxis_title="Category",
                        xaxis_title="Number of Issues",
                        height=max(400, len(categories_count) * 50),  # Adjust height based on number of categories
                        margin=dict(t=50, b=50, l=200),  # Increase left margin for category names
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    def get_affected_urls_by_issue(issue_name, semrush_data):
                        """Get URLs affected by a specific issue"""
                        # Find the exact column name that matches this issue
                        matching_column = None
                        for col in semrush_data.columns:
                            if col.lower() == issue_name.lower():
                                matching_column = col
                                break
                        
                        if not matching_column:
                            return []
                        
                        # Get URLs where this issue has a value > 0
                        mask = pd.to_numeric(semrush_data[matching_column], errors='coerce') > 0
                        return semrush_data[mask]['Page URL'].tolist()
                    
                    
                    # Function to get issue stats from SemRush data
                    def get_category_stats(category_issues, semrush_data):
                        """Get statistics for a category"""
                        stats = {'Issues': 0, 'Warnings': 0, 'Notices': 0}
                        has_urls = False
                        # Keep track of processed issues to avoid duplicates
                        processed_issues = set()
                        
                        for _, issue in category_issues.iterrows():
                            issue_name = issue['Issue Name Contains - SemRush']
                            
                            # Skip if we've already processed this issue
                            if issue_name in processed_issues:
                                continue
                                
                            affected_urls = get_affected_urls_by_issue(issue_name, semrush_data)
                            
                            if affected_urls:
                                has_urls = True
                                count = len(affected_urls)
                                issue_type = issue['Issue Type - SemRush'].lower()
                                
                                if 'error' in issue_type:
                                    stats['Issues'] += count
                                elif 'warning' in issue_type:
                                    stats['Warnings'] += count
                                else:
                                    stats['Notices'] += count
                                    
                                processed_issues.add(issue_name)
                        
                        return stats, has_urls
                    
                    # Display issues by category
                    # Keep track of displayed issues to avoid duplicates
                    displayed_issues = set()
                    
                    for category in sorted(filtered_semrush['Issue category - SemRush'].unique()):
                        if pd.isna(category) or category == 'Uncategorized':
                            continue
                            
                        category_issues = filtered_semrush[
                            filtered_semrush['Issue category - SemRush'] == category
                        ]
                        
                        # Get statistics for this category
                        stats, has_urls = get_category_stats(category_issues, semrush_data)
                        
                        # Only show category if it has URLs with issues
                        if has_urls:
                            expander_label = (
                                f"📊 {category} - "
                                f"{stats['Issues']} Issues, "
                                f"{stats['Warnings']} Warnings, "
                                f"{stats['Notices']} Notices"
                            )
                            
                            with st.expander(expander_label):
                                for _, issue in category_issues.iterrows():
                                    issue_name = issue['Issue Name Contains - SemRush']
                                    
                                    # Skip if we've already displayed this issue in another category
                                    if issue_name in displayed_issues:
                                        continue
                                        
                                    affected_urls = get_affected_urls_by_issue(issue_name, semrush_data)
                                    
                                    if affected_urls:  # Only show issues with affected URLs
                                        displayed_issues.add(issue_name)  # Mark this issue as displayed
                                        st.markdown("---")  # Separator between issues
                                        
                                        cols = st.columns([4, 1])
                                        with cols[0]:
                                            st.markdown(f"""
                                                <div class="issue-card">
                                                    <h4>{issue_name}</h4>
                                                    <p><strong>Type:</strong> {issue['Issue Type - SemRush']}</p>
                                                    <p><strong>Description:</strong> {issue['Issue description - SemRush']}</p>
                                                    <p><strong>How to fix:</strong> {issue['How to fix - SemRush']}</p>
                                                </div>
                                            """, unsafe_allow_html=True)
                                        
                                        with cols[1]:
                                            urls_df = pd.DataFrame({
                                                'URL': affected_urls,
                                                'Issue Type': [issue['Issue Type - SemRush']] * len(affected_urls),
                                                'Issue': [issue_name] * len(affected_urls)
                                            })
                                            
                                            # Create a unique key for the download button
                                            unique_id = str(uuid.uuid4())
                                            download_key = f"download_{category}_{issue_name}_{unique_id}".replace(' ', '_').lower()
                                            
                                            st.download_button(
                                                f"📥 Download URLs ({len(affected_urls)} found)",
                                                export_to_excel(urls_df),
                                                f"urls_{issue_name}.xlsx".replace(' ', '_'),
                                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                key=download_key
                                            )
        
            with tab2:
                st.header("ScreamingFrog Internal Audit Results")
                
                # Filters
                if st.session_state.show_filters:
                    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        selected_priorities = st.multiselect(
                            "Filter by Priority",
                            options=['High', 'Medium', 'Low'],
                            default=[]
                        )
                    with col2:
                        sf_types = sorted(sf_issues['Issue Type'].unique())
                        selected_sf_types = st.multiselect(
                            "Filter by Type",
                            options=sf_types,
                            default=[]
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Filter data
                filtered_sf_issues = sf_issues.copy()
                if selected_priorities:
                    filtered_sf_issues = filtered_sf_issues[
                        filtered_sf_issues['Issue Priority'].isin(selected_priorities)
                    ]
                if selected_sf_types:
                    filtered_sf_issues = filtered_sf_issues[
                        filtered_sf_issues['Issue Type'].isin(selected_sf_types)
                    ]
                
                # Export button
                if not filtered_sf_issues.empty:
                    st.download_button(
                        "Export ScreamingFrog Issues",
                        export_to_excel(filtered_sf_issues),
                        "screaming_frog_issues.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # Display charts and issues
                if not filtered_sf_issues.empty:
                    priority_chart = create_issues_chart(
                        filtered_sf_issues, 
                        'URLs',
                        'Issue Priority',
                        'Issues by Priority'
                    )
                    st.plotly_chart(priority_chart, use_container_width=True)
                    
                    for priority in ['High', 'Medium', 'Low']:
                        if priority in filtered_sf_issues['Issue Priority'].values:
                            priority_issues = filtered_sf_issues[
                                filtered_sf_issues['Issue Priority'] == priority
                            ]
                            with st.expander(f"{'🔴' if priority == 'High' else '🟡' if priority == 'Medium' else '🟢'} {priority} Priority Issues"):
                                for _, issue in priority_issues.iterrows():
                                    st.markdown(f"""
                                        <div class="issue-card priority-{priority.lower()}">
                                            <h4>{issue['Issue Name']} ({issue['URLs']} URLs)</h4>
                                            <p><strong>Description:</strong> {issue['Description']}</p>
                                            <p><strong>How to fix:</strong> {issue['How To Fix']}</p>
                                            <p><em>Affects {issue['% of Total']}% of total URLs</em></p>
                                        </div>
                                    """, unsafe_allow_html=True)
            
            with tab3:
                st.header("Tool Comparison")
                
                # Export comparison data
                matched_issues = mapping_data[
                    (mapping_data['Issue Name Contains - SemRush'] != 'NA') & 
                    (mapping_data['Issue Name - ScreamingFrog'] != 'NA')
                ]
                
                if not matched_issues.empty:
                    st.download_button(
                        "Export Comparison Data",
                        export_to_excel(matched_issues),
                        "tool_comparison.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # Summary statistics
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
                
                    # Display comparison
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

if __name__ == "__main__":
    main()