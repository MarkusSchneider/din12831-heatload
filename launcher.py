"""Launcher for the Streamlit app when running as a standalone executable."""

import sys
import os
from pathlib import Path


def main():
    """Launch the Streamlit app with proper runtime context."""
    # Get the directory where the executable is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = Path(sys._MEIPASS)
    else:
        # Running as script
        app_dir = Path(__file__).parent

    # Set the app path
    app_path = app_dir / "app.py"

    # Import streamlit.web.cli after determining paths
    from streamlit.web import cli as stcli

    # Set up the arguments for streamlit run
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.port=8501",
        "--server.address=localhost",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]

    # Launch Streamlit
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
