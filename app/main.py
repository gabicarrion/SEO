import streamlit as st
st.set_page_config(page_title="SEO Audit Comparison", layout="wide")
    
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import base64
from pathlib import Path
import uuid
import tempfile
import subprocess
import platform
import logging
import time
import sys
import threading
import glob

# Constants
BASE_DIR = Path(__file__).parent
MAPPING_FILE = Path("data/mapping/SemRush vs. ScreamingFrog.csv")
CONFIG_DIR = BASE_DIR / "config" / "sf_configs"
CRAWLS_DIR = Path("data/crawls")

# Import utility functions
from utils.data_loader import (
    load_mapping_data, 
    load_sf_issues, 
    load_semrush_data,
    process_semrush_categories,
    get_issue_stats
)
from utils.export import export_to_excel
from utils.visualizations import create_issues_chart, create_comparison_chart, create_priority_pie_chart, create_issues_stats_chart
from utils.sf_crawler import SFCrawler

# Import UI modules
from utils.ui.semrush_tab import render_semrush_tab
from utils.ui.sf_tab import render_sf_tab
from utils.ui.comparison_tab import render_comparison_tab

def setup_folders():
    """Create necessary folders if they don't exist"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CRAWLS_DIR.mkdir(parents=True, exist_ok=True)
    
def get_affected_urls_by_issue(issue_name, semrush_data):
    """Get URLs affected by a specific issue"""
    matching_column = None
    for col in semrush_data.columns:
        if col.lower() == issue_name.lower():
            matching_column = col
            break
    
    if not matching_column:
        return []
    
    mask = pd.to_numeric(semrush_data[matching_column], errors='coerce') > 0
    urls = semrush_data[mask]['Page URL'].tolist()
    sys.stdout.flush()
    
    return urls

def get_category_stats(category_issues, semrush_data):
    """Get statistics for a category"""
    stats = {'Issues': 0, 'Warnings': 0, 'Notices': 0}
    has_urls = False
    processed_issues = set()
    
    for _, issue in category_issues.iterrows():
        issue_name = issue['Issue Name Contains - SemRush']
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


def setup_logger():
    """Set up the application logger"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a logger for this session
    session_logger = logging.getLogger('seo_audit')
    session_logger.setLevel(logging.INFO)
    
    # Add streamlit handler to show logs in the UI
    class StreamlitHandler(logging.Handler):
        def emit(self, record):
            try:
                msg = self.format(record)
                with st.expander("📝 Application Logs", expanded=False):
                    st.text(msg)
            except Exception:
                self.handleError(record)
    
    # Add the handler if not already added
    if not any(isinstance(h, StreamlitHandler) for h in session_logger.handlers):
        session_logger.addHandler(StreamlitHandler())
    
    return session_logger

def setup_sidebar():
    """Set up the sidebar with configuration options"""
    with st.sidebar:
        st.header("Input Files")
        domain = st.text_input("Domain", "example.com")
        audit_date = st.date_input("Audit Date", datetime.now())
        
        semrush_file = st.file_uploader("Upload SemRush Export", type=['csv'])
        sf_file = st.file_uploader("Upload Screaming Frog Issues", type=['csv'])
        
        st.header("Filters")
        st.session_state.show_filters = st.checkbox("Show Filters", True)
        
        # ScreamingFrog Settings
        st.header("ScreamingFrog Settings")
        sf_path = st.text_input(
            "ScreamingFrog Path",
            value=r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe",
            help="Path to ScreamingFrog CLI executable"
        )
            
        # Debug Information
        with st.expander("🔍 Debug Information", expanded=True):
            # ScreamingFrog Executable Check
            st.markdown("### ScreamingFrog Setup")
            st.write("📌 Current Path:", sf_path)
            
            # Configuration Directory
            st.markdown("### Configuration")
            st.write("📌 Config Directory:", CONFIG_DIR)
            if CONFIG_DIR.exists():
                st.success("✅ Config directory found")
                config_files = list(CONFIG_DIR.glob("*.seospiderconfig"))
                st.write(f"📄 Found {len(config_files)} config files:")
                for cf in config_files:
                    st.code(cf.name, language="text")
            else:
                st.error("❌ Config directory not found!")
            
            # Crawls Directory
            st.markdown("### Crawls")
            st.write("📌 Crawls Directory:", CRAWLS_DIR)
            if CRAWLS_DIR.exists():
                st.success("✅ Crawls directory found")
                recent_crawls = list(CRAWLS_DIR.glob("crawl_*"))[-5:]  # Last 5 crawls
                if recent_crawls:
                    st.write("🕒 Recent crawls:")
                    for crawl in recent_crawls:
                        st.code(crawl.name, language="text")
            else:
                st.error("❌ Crawls directory not found!")
            
            # System Info
            st.markdown("### System")
            st.write("💻 Platform:", platform.system())
            st.write("💾 Python Version:", platform.python_version())
    
    return {
        'domain': domain,
        'audit_date': audit_date,
        'semrush_file': semrush_file,
        'sf_file': sf_file,
        'sf_path': sf_path
    }

def main():
    # Setup necessary folders
    setup_folders()
    
    # Set up app title
    st.title("🔍 SEO Audit Comparison Dashboard")
    
    # Set up logger
    session_logger = setup_logger()
    
    # Set up sidebar
    sidebar_config = setup_sidebar()
    
    # Initialize SF crawler
    if 'sf_crawler' not in st.session_state:
        st.session_state.sf_crawler = SFCrawler(sidebar_config['sf_path'], str(CONFIG_DIR))

    sf_crawler = st.session_state.sf_crawler  # ✅ Use session state to persist instance
    
    # Load mapping data
    mapping_data = load_mapping_data(MAPPING_FILE)
    
    # Only proceed if required data is available
    if mapping_data is not None and sidebar_config['semrush_file'] and sidebar_config['sf_file']:
        semrush_data = load_semrush_data(sidebar_config['semrush_file'])
        sf_issues = load_sf_issues(sidebar_config['sf_file'])
        
        if semrush_data is not None and sf_issues is not None:
            # Process SemRush data
            semrush_issues = process_semrush_categories(mapping_data[mapping_data['Issue Type - SemRush'] != 'NA'])
            
            # Create tabs
            tab1, tab2, tab3 = st.tabs([
                "SemRush Audit Results", 
                "ScreamingFrog Internal Audit Results",
                "Comparison"
            ])
            
            # Render each tab
            with tab1:
                render_semrush_tab(
                    semrush_data=semrush_data,
                    semrush_issues=semrush_issues,
                    mapping_data=mapping_data,
                    sf_crawler=sf_crawler,
                    CRAWLS_DIR=CRAWLS_DIR,
                    get_affected_urls_by_issue=get_affected_urls_by_issue,
                    get_category_stats=get_category_stats
                )
                
            with tab2:
                render_sf_tab(sf_issues=sf_issues)
                
            with tab3:
                render_comparison_tab(mapping_data=mapping_data)
    else:
        st.info("Please upload SemRush and Screaming Frog files to get started.")

if __name__ == "__main__":
    main()