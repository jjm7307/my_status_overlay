conda create -n status_env python=3.10
conda activate status_env
# pip install pyinstaller pystray pillow
pyinstaller --noconsole --onefile status_overlay.py
