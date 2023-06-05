sudo apt-get update
sudo apt-get install -y --no-install-recommends ffmpeg
pip3 install --user -r requirements.txt
playwright install
playwright install-deps
