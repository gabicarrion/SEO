# utils/ui/semrush_tab.py
import streamlit as st
import pandas as pd
import uuid
from pathlib import Path
import threading
import sys
from datetime import datetime
import time
from utils.visualizations import create_issues_stats_chart
from utils.export import export_to_excel
from utils.ui.common import create_download_button, create_expander_with_title
from utils.sf_crawler import SFCrawler
import glob
import json


############################ FILTRATION ############################
# Used in render_semrush_tabs
def apply_semrush_filters(semrush_issues):
    """Apply filters to SemRush issues and return selected values"""
    if st.session_state.show_filters:
        col1, col2 = st.columns(2)
        
        with col1:
            categories = sorted([cat for cat in semrush_issues['Issue category - SemRush'].unique() 
                            if pd.notna(cat) and cat.strip() != 'Uncategorized'])
            selected_categories = st.multiselect("Filter by Category", options=categories, default=categories if categories else [])

        with col2:
            all_types = [t for t in semrush_issues['Issue Type - SemRush'].unique() if pd.notna(t) and t.strip() != 'Uncategorized']
            sorted_types = sorted(all_types, key=lambda x: ("Error" in x, "Warning" in x), reverse=True)
            default_types = [t for t in sorted_types if "Error" in t or "Warning" in t]
            selected_types = st.multiselect("Filter by Type", options=sorted_types, default=default_types)

        return {'categories': selected_categories, 'types': selected_types}
    
    return {'categories': [], 'types': []}

# Used in render_semrush_tabs
def filter_semrush_data(semrush_issues, filters):
    """Filter SemRush data based on the selected filters"""
    filtered = semrush_issues.copy()
    if filters['categories']:
        filtered = filtered[filtered['Issue category - SemRush'].isin(filters['categories'])]
    if filters['types']:
        filtered = filtered[filtered['Issue Type - SemRush'].isin(filters['types'])]
    return filtered


############################ SEM RUSH ISSUES ############################
#Used in display_crawl_controls, that is used in display_semrush_issues
def display_crawl_status(crawl_id, output_folder):
    """Display Screaming Frog crawl status by reading from a JSON file."""

    status_file = Path(output_folder) / f"{crawl_id}_status.json"

    # ✅ Check if status file exists
    if not status_file.exists():
        st.warning(f"⚠️ No status found for `{crawl_id}`.")
        return

    # ✅ Read crawl status
    with status_file.open("r") as f:
        crawl_info = json.load(f)

    status = crawl_info.get('status', 'unknown')
    start_time = crawl_info.get('start_time', 'unknown')
    end_time = crawl_info.get('end_time', 'unknown')

    st.markdown("---")
    st.markdown(f"### Screaming Frog Crawl Status for {crawl_id}")

    if status == 'running':
        st.warning(f"🔄 **CRAWL IN PROGRESS**  \n🕒 Started at: {start_time}")
        
        # ✅ Dynamically update progress bar
        progress_bar = st.progress(50)

        # ✅ Refresh UI every 5 seconds
        time.sleep(5)
        st.rerun()

    elif status == 'completed':
        st.success(f"✅ **CRAWL COMPLETED!**  \n📅 Finished at: {end_time}")

        # ✅ Remove progress bar
        progress_bar = st.empty()
        progress_bar.empty()

        report_folder = Path(crawl_info.get('output_folder', ''))

        if report_folder.exists():
            st.write(f"📁 Output Directory: `{report_folder}`")

            # ✅ Show CSV reports
            report_files = list(report_folder.glob("*.csv"))
            if report_files:
                st.write("📊 **Available Reports:**")
                for report_file in report_files:
                    with report_file.open("rb") as file:
                        st.download_button(
                            label=f"📥 Download {report_file.name}",
                            data=file,
                            file_name=report_file.name,
                            mime="text/csv",
                            key=f"download_{crawl_id}_{report_file.name}"
                        )
            else:
                st.warning("⚠️ No CSV reports found.")

    elif status in ['error', 'failed']:
        st.error(f"❌ **CRAWL FAILED!**")
        st.write(f"⚠️ Error: {crawl_info.get('error', 'Unknown error')}")

        # ✅ Retry button
        if st.button(f"🔄 Retry Crawl", key=f"retry_{crawl_id}", use_container_width=True):
            status_file.unlink(missing_ok=True)  # Delete status file
            st.rerun()


#Used in display_semrush_issues
def display_crawl_controls(category, issue_name, displayed_issue_count, affected_urls, mapping_data, sf_crawler, CRAWLS_DIR):
    """Display crawl controls for an issue."""

    safe_category = str(category).replace(" ", "_").lower()
    safe_issue_name = str(issue_name).replace(" ", "_").lower()
    crawl_id = f"{safe_category}_{safe_issue_name}_{displayed_issue_count}"

    crawl_output = CRAWLS_DIR / f"crawl_{safe_category}_{safe_issue_name}_{displayed_issue_count}"
    crawl_output.mkdir(parents=True, exist_ok=True)

    if st.button("Run Screaming Frog Crawl", key=f"run_crawl_{crawl_id}"):
        print(f"✅ [DEBUG] Starting crawl for {safe_issue_name}...")
        
        # ✅ Write affected URLs to file
        url_list_path = crawl_output / "urls.txt"
        with url_list_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(affected_urls))

        # ✅ Fetch config file from mapping
        issue_row = mapping_data[mapping_data["Issue Name Contains - SemRush"] == issue_name]
        if issue_row.empty:
            st.error(f"❌ No Screaming Frog config found for `{issue_name}`.")
            return

        sf_config_file = issue_row["sf_config_file"].values[0]
        sf_export_tabs = issue_row["sf_export_tabs"].values[0] or "Internal:All"

        config_file_path = sf_crawler.config_folder / sf_config_file
        if not config_file_path.exists():
            st.error(f"❌ Config file `{config_file_path}` not found!")
            return

        # ✅ Build command
        command = [
            sf_crawler.sf_path,
            "--crawl-list", str(url_list_path),
            "--headless",
            "--output-folder", str(crawl_output),
            "--config", str(config_file_path),
            "--export-format", "csv",
            "--export-tabs", sf_export_tabs,
            "--overwrite",
            "--save-crawl"
        ]

        print(f"🚀 Running Screaming Frog: {' '.join(command)}")

        # ✅ Run Screaming Frog in background thread
        thread = threading.Thread(
            target=sf_crawler.run_sf_with_status,
            args=(command, crawl_id, crawl_output)
        )
        thread.daemon = True
        thread.start()

        st.rerun()

    # ✅ Always show status
    display_crawl_status(crawl_id, crawl_output)


#Used in render_semrush_tab
def display_semrush_issues(filtered_semrush, semrush_data, mapping_data, sf_crawler, CRAWLS_DIR, get_affected_urls_by_issue, get_category_stats):
    """Display SemRush issues by category"""
    displayed_issues = set()
    displayed_issue_count = 0
    
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
                    
                    if issue_name in displayed_issues:
                        continue
                        
                    affected_urls = get_affected_urls_by_issue(issue_name, semrush_data)
                    
                    if affected_urls:
                        displayed_issues.add(issue_name)
                        st.markdown("---")
                        
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
                            
                            # Create unique keys
                            safe_category = str(category).replace(' ', '_').lower()
                            safe_issue_name = str(issue_name).replace(' ', '_').lower()
                            base_key = f"{safe_category}_{safe_issue_name}_{displayed_issue_count}_{uuid.uuid4()}"
                            
                            # Add buttons in columns
                            button_cols = st.columns(2)
                            with button_cols[0]:
                                create_download_button(
                                    urls_df,
                                    f"urls_{safe_category}_{safe_issue_name}_{displayed_issue_count}.xlsx",
                                    f"📥 Download URLs ({len(affected_urls)})",
                                    key=f"download_{base_key}"
                                )
                            
                        # Inside your expander where you show issue details
                        with button_cols[1]:
                            display_crawl_controls(category, issue_name, displayed_issue_count, affected_urls, mapping_data, sf_crawler, CRAWLS_DIR)

                        
                        displayed_issue_count += 1



#Main function
def render_semrush_tab(semrush_data, semrush_issues, mapping_data, sf_crawler, CRAWLS_DIR, get_affected_urls_by_issue, get_category_stats):
    """Render the SemRush tab content"""
    st.header("SemRush Audit Results")
    
    # Apply filters
    filters = apply_semrush_filters(semrush_issues)
    
    # Filter data
    filtered_semrush = filter_semrush_data(semrush_issues, filters)
    
    
    # Create horizontal bar chart
    if semrush_data is not None:
        fig = create_issues_stats_chart(
            semrush_data,
            mapping_data,
            filters['types'] if filters['types'] else None,
            filters['categories'] if filters['categories'] else None
        )
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No issues found with the current filter settings.")
                    
    # Display issues by category
    display_semrush_issues(filtered_semrush, semrush_data, mapping_data, sf_crawler, CRAWLS_DIR, get_affected_urls_by_issue, get_category_stats)