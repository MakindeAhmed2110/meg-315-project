"""Launch the AD-HTC Biogas Kinetics Streamlit app."""
import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true"], check=True)
