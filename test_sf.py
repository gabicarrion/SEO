import streamlit as st
import subprocess
import os
import time
from pathlib import Path

# Page config
st.set_page_config(page_title="SF CLI Test", layout="wide")

# Title
st.title("🕷️ ScreamingFrog CLI Test")

# Input fields
sf_path = st.text_input(
    "ScreamingFrog CLI Path",
    value=r"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli.exe",
    key="sf_path"
)

test_url = st.text_input(
    "Test URL",
    value="https://www.brit.co",
    key="test_url"
)

# Create output directory
output_dir = Path("test_output")
output_dir.mkdir(parents=True, exist_ok=True)


# Define the correct config file path
config_path = Path(r"I:\Meu Drive\Automations_Project\SemRush2.0\app\config\sf_configs\default_config.seospiderconfig")
# Run test button
if st.button("Run Test Crawl"):
    if not os.path.exists(sf_path):
        st.error("❌ ScreamingFrog CLI path not found!")
    else:
        # Create status containers
        status = st.empty()
        log = st.empty()
        
        try:
            # Create URL list file
            url_file = output_dir / "urls.csv"
            url_file.write_text(test_url)
            time.sleep(1)  # Small delay to ensure file is written

            # Debugging: Verify file existence
            if not url_file.exists():
                st.error(f"❌ URL list file not found at {url_file.absolute()}")
                raise FileNotFoundError("urls.csv was not created!")
            else:
                st.success(f"✅ URL list file created at {url_file.absolute()}")
                st.text("File Contents:")
                st.code(url_file.read_text())

            # Build command with absolute paths
            command = [
                sf_path,  # Screaming Frog executable path
                "--crawl-list", f'"{url_file.resolve()}"',  # Add quotes around the file path
                "--headless",
                "--output-folder", f'"{output_dir.resolve()}"',  # Add quotes around output directory
                "--export-format", "csv",
                "--save-crawl",
                "--overwrite",
                "--export-tabs", "Internal:All",
                "--config", f'"{config_path.resolve()}"'  # Ensure quotes
            ]


            status.info("🚀 Starting crawl...")

            # Show command being run
            with log.container():
                st.text("Command:")
                st.code(" ".join(command))

                # Run the command
                process = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=str(output_dir.resolve())  # Ensure correct working directory
                )

                # Show output logs
                st.text("Standard Output:")
                st.code(process.stdout)

                st.text("Standard Error:")
                st.code(process.stderr)

                # Check process result
                if process.returncode == 0:
                    status.success("✅ Crawl completed successfully!")

                    # Show results
                    st.text("Results:")
                    for file in output_dir.glob("*.csv"):
                        st.text(f"- {file.name}")
                else:
                    status.error(f"❌ Process failed with code {process.returncode}")
        
        except Exception as e:
            status.error(f"❌ Error: {str(e)}")
            st.exception(e)

# Show debug info
with st.expander("Debug Info", expanded=False):
    st.text("Environment:")
    st.text(f"- Working directory: {os.getcwd()}")
    st.text(f"- Output directory: {output_dir.absolute()}")

    if output_dir.exists():
        st.text("\nOutput directory contents:")
        for file in output_dir.glob("*"):
            st.text(f"- {file.name}")
