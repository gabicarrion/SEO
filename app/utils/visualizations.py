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