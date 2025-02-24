# Modified sf_crawler.py

import subprocess
import os
import pandas as pd
from pathlib import Path
import glob
import logging
import time
from threading import Timer
import streamlit as st
import zipfile
import io
import sys
from datetime import datetime
import json


class SFCrawler:
    def __init__(self, screaming_frog_path, config_folder):
        self.sf_path = screaming_frog_path
        self.config_folder = Path(config_folder)
        self.crawl_status = {}  # ✅ Use a dictionary instead of session_state
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized SFCrawler with path: {screaming_frog_path} and config folder: {config_folder}")

       


    #Used in display crawl status            
    def display_sf_reports(crawl_output, safe_category, safe_issue_name, displayed_issue_count):
        """
        Display and offer downloads for Screaming Frog crawl reports.
        
        Parameters:
        - crawl_output: Path object to the crawl output directory
        - safe_category: Sanitized category name
        - safe_issue_name: Sanitized issue name
        - displayed_issue_count: Counter to ensure unique crawl outputs
        
        Returns:
        - None
        """
        
        # Check if crawl directory exists
        if not crawl_output.exists():
            st.error(f"Crawl output directory not found: {crawl_output}")
            return
        
        # Find all CSV files in the crawl output directory
        csv_files = glob.glob(str(crawl_output / "*.csv"))
        
        if not csv_files:
            st.warning("No report files found in the crawl output directory.")
            return
        
        # Display success message with timestamp
        current_time = datetime.now().strftime("%H:%M:%S")
        st.success(f"✅ Found {len(csv_files)} report files in the crawl output.")
        
        # Create expandable section for the reports
        with st.expander("📊 View Crawl Reports", expanded=True):
            # Create tabs for each report
            if len(csv_files) > 0:
                # Sort files by name
                csv_files.sort()
                
                # Create a tab for each report file
                report_tabs = st.tabs([os.path.basename(file) for file in csv_files])
                
                for i, (tab, file) in enumerate(zip(report_tabs, csv_files)):
                    with tab:
                        try:
                            # Load the CSV data
                            df = pd.read_csv(file)
                            
                            # Display file info
                            st.info(f"File: {os.path.basename(file)} | Rows: {len(df)} | Columns: {len(df.columns)}")
                            
                            # Create download button for this file
                            file_name = os.path.basename(file)
                            with open(file, "rb") as f:
                                st.download_button(
                                    label=f"Download {file_name}",
                                    data=f,
                                    file_name=file_name,
                                    mime="text/csv",
                                    key=f"download_{safe_category}_{safe_issue_name}_{displayed_issue_count}_{i}"
                                )
                            
                            # Display the data preview
                            st.dataframe(df.head(10))
                            
                        except Exception as e:
                            st.error(f"Error loading file {os.path.basename(file)}: {str(e)}")
            else:
                st.warning("No report files found.")
                
        # Provide download link for all reports as ZIP
        try:
            # Create a buffer
            zip_buffer = io.BytesIO()
            
            # Create a zip file
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in csv_files:
                    file_name = os.path.basename(file)
                    zf.write(file, arcname=file_name)
            
            # Reset buffer position
            zip_buffer.seek(0)
            
            # Create download button for zip
            st.download_button(
                label="Download All Reports (ZIP)",
                data=zip_buffer,
                file_name=f"crawl_{safe_category}_{safe_issue_name}_{displayed_issue_count}.zip",
                mime="application/zip",
                key=f"download_zip_{safe_category}_{safe_issue_name}_{displayed_issue_count}"
            )
        except Exception as e:
            st.error(f"Error creating ZIP file: {str(e)}")
    
   # Used in SemRushTab - display_crawl_controls that uses display_semrush_issues
    def run_sf_with_status(self, command, crawl_id, output_folder):
        """Run Screaming Frog and track status using a JSON file instead of session state."""

        # ✅ Create a status file
        status_file = Path(output_folder) / f"{crawl_id}_status.json"

        def update_status(new_status):
            """Write status updates to a file instead of session state."""
            with status_file.open("w") as f:
                json.dump(new_status, f)
            print(f"🔹 Updated status file: {new_status}")

        # ✅ Initialize status file
        update_status({
            'status': 'running',
            'start_time': datetime.now().strftime("%H:%M:%S")
        })

        print(f"🚀 Running Screaming Frog: {' '.join(command)}")
        sys.stdout.flush()

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

            for line in process.stdout:
                print(f"🔍 SF Output: {line.strip()}")
                sys.stdout.flush()

            for line in process.stderr:
                print(f"❌ SF Errors: {line.strip()}")
                sys.stdout.flush()

            process.wait()

            if process.returncode == 0:
                print(f"✅ Crawl {crawl_id} completed successfully!")

                # ✅ Update status file to "completed"
                update_status({
                    'status': 'completed',
                    'end_time': datetime.now().strftime("%H:%M:%S"),
                    'output_folder': str(output_folder)
                })

            else:
                print(f"❌ Crawl {crawl_id} failed with error code {process.returncode}")
                update_status({'status': 'failed'})

        except Exception as e:
            print(f"💥 Error running Screaming Frog: {str(e)}")
            update_status({'status': 'error'})
