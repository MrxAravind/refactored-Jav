python -m venv myenv  # Create a virtual environment (if not already created)
source myenv/bin/activate  # Activate the virtual environment
python -m ensurepip --upgrade  # Ensure pip is installed and upgrade it
pip install -r requirements.txt
sudo apt install ffmpeg aria2 -y
aria2c --enable-rpc --rpc-listen-all=false --rpc-allow-origin-all --daemon --max-tries=50 --retry-wait=3 --continue=true && python3 main.py
