import plotly.express as px
import plotly.graph_objects as go

def create_issues_chart(df, value_column, category_column, title):
    """Create a bar chart for issues"""
    fig = px.bar(df, 
                 x=category_column,
                 y=value_column,
                 title=title)
    fig.update_layout(
        xaxis_title=category_column,
        yaxis_title="Number of Issues",
        xaxis={'categoryorder':'total descending'},
        height=400,
        margin=dict(t=50, b=50)
    )
    
    # Update bar colors based on priority/category
    if category_column == 'Issue Priority':
        color_map = {
            'High': '#dc3545',
            'Medium': '#ffc107',
            'Low': '#28a745'
        }
        fig.update_traces(marker_color=[color_map.get(x, '#1f77b4') for x in df[category_column]])
    
    # Rotate x-axis labels if they're too long
    if df[category_column].astype(str).str.len().max() > 15:
        fig.update_layout(xaxis_tickangle=-45)
    
    # Add value labels on top of bars
    fig.update_traces(
        texttemplate='%{y}',
        textposition='outside'
    )
    
    return fig

def create_comparison_chart(semrush_data, sf_data, metric):
    """Create a comparison chart between SemRush and ScreamingFrog"""
    fig = go.Figure(data=[
        go.Bar(name='SemRush', x=semrush_data.index, y=semrush_data.values),
        go.Bar(name='ScreamingFrog', x=sf_data.index, y=sf_data.values)
    ])
    
    fig.update_layout(
        barmode='group',
        title=f'Comparison of {metric}',
        xaxis_title=metric,
        yaxis_title='Count',
        height=400,
        margin=dict(t=50, b=50)
    )
    
    return fig

def create_priority_pie_chart(df, values, names, title):
    """Create a pie chart for priority distribution"""
    fig = px.pie(
        values=values,
        names=names,
        title=title
    )
    
    fig.update_traces(
        textinfo='percent+label',
        pull=[0.1 if name == 'High' else 0 for name in names]
    )
    
    return fig

def create_interactive_category_chart(df, category_col, count_col, issues_df):
    """Create an interactive horizontal bar chart for categories"""
    # Count issues by category and sort descending
    categories_count = filtered_semrush.groupby('Issue category - SemRush').size().reset_index(name='count')
    categories_count = categories_count.sort_values('count', ascending=False)
    
    
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        y=categories_count['Issue category - SemRush'],
        x=categories_count['count'],
        orientation='h',
        text=categories_count['count'],
        textposition='auto',
    ))
    
    # Update layout
    fig.update_layout(
        title='Issues by Category (Click bars to see details)',
        yaxis_title="Category",
        xaxis_title="Number of Issues",
        height=max(400, len(categories_count) * 50),  # Adjust height based on number of categories
        margin=dict(t=50, b=50, l=200),  # Increase left margin for category names
        showlegend=False,
        yaxis={'categoryorder':'array', 'categoryarray': categories_count['Issue category - SemRush']},  # Keep the sorted order
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,
            font_family="Rockwell"
        )
    )
    
    # Add click event data
    fig.update_traces(
        customdata=df[category_col],
        clickmode='event+select'
    )
    
    return fig

def create_issues_stats_chart(semrush_data, mapping_data, filtered_types=None, filtered_categories=None):
    """
    Creates a bar chart showing accurate URL counts by individual issue in the SemRush data
    with proper filtering for both issue types and categories.
    
    Parameters:
    - semrush_data: DataFrame containing the SemRush export data
    - mapping_data: DataFrame containing the mapping between SemRush and SF issues
    - filtered_types: Optional list of issue types to include (for filtering)
    - filtered_categories: Optional list of categories to include (for filtering)
    
    Returns:
    - A Plotly figure object
    """
    import plotly.graph_objects as go
    import pandas as pd
    import re
    
    # Dictionary to track issues and affected URLs
    issue_dict = {}
    
    # Apply both type and category filters to mapping data first for efficiency
    filtered_mapping = mapping_data.copy()
    
    if filtered_types:
        filtered_mapping = filtered_mapping[filtered_mapping['Issue Type - SemRush'].isin(filtered_types)]
    
    if filtered_categories:
        # Handle multi-category issues (where category may contain commas)
        if filtered_mapping['Issue category - SemRush'].dtype == 'object':
            category_mask = filtered_mapping['Issue category - SemRush'].apply(
                lambda cats: any(cat.strip() in filtered_categories 
                                for cat in str(cats).split(',') 
                                if pd.notna(cats))
            )
            filtered_mapping = filtered_mapping[category_mask]
        else:
            filtered_mapping = filtered_mapping[filtered_mapping['Issue category - SemRush'].isin(filtered_categories)]
    
    # First pass - find all columns that match each issue
    issue_to_columns = {}
    for _, issue in filtered_mapping.iterrows():
        issue_name = issue['Issue Name Contains - SemRush']
        issue_type = issue['Issue Type - SemRush']
        issue_category = issue['Issue category - SemRush']
        
        # Skip if NA
        if pd.isna(issue_name) or issue_name == 'NA' or pd.isna(issue_type) or issue_type == 'NA':
            continue
            
        # Skip if it doesn't match our category filter
        if filtered_categories and pd.notna(issue_category) and issue_category != 'NA':
            categories = [cat.strip() for cat in str(issue_category).split(',')]
            if not any(cat in filtered_categories for cat in categories):
                continue
        
        # Normalize issue name for comparison
        normalized_name = re.sub(r'\s+', '', issue_name.lower())
        
        # Find all matching columns for this issue
        matching_columns = []
        for col in semrush_data.columns:
            if col.lower() == issue_name.lower():
                matching_columns.append(col)
                
        if matching_columns:
            # Create a unique key for this issue or find an existing one
            issue_key = None
            for existing_key in issue_to_columns:
                if re.sub(r'\s+', '', existing_key.lower()) == normalized_name:
                    issue_key = existing_key
                    break
            
            if issue_key is None:
                issue_key = issue_name
                issue_to_columns[issue_key] = {
                    'columns': [],
                    'type': issue_type,
                    'category': issue_category
                }
            
            # Add these columns to the issue
            issue_to_columns[issue_key]['columns'].extend(matching_columns)
    
    # Second pass - count unique URLs for each issue
    for issue_name, issue_data in issue_to_columns.items():
        affected_urls = set()  # Using a set to ensure unique URLs
        
        for column in issue_data['columns']:
            try:
                # Count URLs affected by this issue in this column
                mask = pd.to_numeric(semrush_data[column], errors='coerce') > 0
                column_urls = set(semrush_data[mask]['Page URL'].tolist())
                affected_urls.update(column_urls)  # Add to set of affected URLs
            except Exception as e:
                print(f"Error processing column {column}: {str(e)}")
        
        # Only include issues that affect at least one URL
        if affected_urls:
            issue_dict[issue_name] = {
                'Issue Name': issue_name,
                'Issue Type': issue_data['type'],
                'URL Count': len(affected_urls),
                'Issue Category': issue_data['category']
            }
    
    # Convert dictionary to list for DataFrame
    issue_stats = list(issue_dict.values())
    
    # Convert to DataFrame for plotting
    if not issue_stats:
        print("No issues found with the current filter settings.")
        return None
        
    stats_df = pd.DataFrame(issue_stats)
    
    # Sort by URL count descending
    stats_df = stats_df.sort_values('URL Count', ascending=False)
    
    # Determine colors based on issue type
    colors = []
    for issue_type in stats_df['Issue Type']:
        if 'error' in str(issue_type).lower():
            colors.append('#dc3545')  # Red for errors
        elif 'warning' in str(issue_type).lower():
            colors.append('#ffc107')  # Yellow for warnings
        else:
            colors.append('#28a745')  # Green for notices
    
    # Create the bar chart
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        y=stats_df['Issue Name'],
        x=stats_df['URL Count'],
        marker_color=colors,
        orientation='h',
        text=stats_df['URL Count'],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>URLs affected: %{x}<br>Type: %{customdata}',
        customdata=stats_df['Issue Type']
    ))
    
    # Create filter description for title
    filter_desc = []
    if filtered_types:
        filter_desc.append("Types")
    if filtered_categories:
        filter_desc.append("Categories")
    filter_text = f" - Filtered by {' & '.join(filter_desc)}" if filter_desc else ""
    
    # Update layout
    fig.update_layout(
        title=f'Issues by URL Count (Descending){filter_text}',
        yaxis_title="Issue",
        xaxis_title="Number of URLs Affected",
        height=max(500, len(stats_df) * 25),
        margin=dict(t=50, b=50, l=300),
        showlegend=False,
        yaxis=dict(
            categoryorder='total ascending',
            autorange="reversed"
        )
    )
    
    return fig
def create_issues_list_chart(df, category):
    """Create a chart showing issues for a specific category"""
    issues_df = df[df['Issue category - SemRush'] == category]
    
    fig = px.bar(
        issues_df,
        x='Issue Name Contains - SemRush',
        y='count',
        color='Issue Type - SemRush',
        title=f'Issues in {category}',
        labels={'count': 'Number of URLs Affected'},
        height=400
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        margin=dict(t=50, b=100)
    )
    
    return fig