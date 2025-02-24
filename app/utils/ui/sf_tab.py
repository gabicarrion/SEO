# utils/ui/sf_tab.py
import streamlit as st
import pandas as pd
from utils.visualizations import create_issues_chart
from utils.ui.common import create_download_button

def apply_sf_filters(sf_issues):
    """Apply filters to Screaming Frog issues and return selected values"""
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
        
        return {
            'priorities': selected_priorities,
            'types': selected_sf_types
        }
    else:
        return {
            'priorities': [],
            'types': []
        }

def filter_sf_data(sf_issues, filters):
    """Filter Screaming Frog data based on the selected filters"""
    filtered_sf_issues = sf_issues.copy()
    if filters['priorities']:
        filtered_sf_issues = filtered_sf_issues[
            filtered_sf_issues['Issue Priority'].isin(filters['priorities'])
        ]
    if filters['types']:
        filtered_sf_issues = filtered_sf_issues[
            filtered_sf_issues['Issue Type'].isin(filters['types'])
        ]
    
    return filtered_sf_issues

def display_sf_issues(filtered_sf_issues):
    """Display Screaming Frog issues by priority"""
    for priority in ['High', 'Medium', 'Low']:
        if priority in filtered_sf_issues['Issue Priority'].values:
            priority_issues = filtered_sf_issues[
                filtered_sf_issues['Issue Priority'] == priority
            ]
            
            # Create expander with appropriate emoji
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

def render_sf_tab(sf_issues):
    """Render the Screaming Frog tab content"""
    st.header("ScreamingFrog Internal Audit Results")
    
    # Apply filters
    filters = apply_sf_filters(sf_issues)
    
    # Filter data
    filtered_sf_issues = filter_sf_data(sf_issues, filters)
    
    # Export button
    if not filtered_sf_issues.empty:
        create_download_button(
            filtered_sf_issues,
            "screaming_frog_issues.xlsx",
            "Export ScreamingFrog Issues"
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
        
        # Display issues by priority
        display_sf_issues(filtered_sf_issues)
    else:
        st.info("No issues match the current filter criteria.")