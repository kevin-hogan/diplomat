# Setup assumes that :
#   -Microsoft VS Code is installed
#   -Python3 is installed
#   -Your dev environment is on Ubuntu and you are running as a sudoer

code --install-extension ms-python.python
sudo apt update && sudo apt install -y python3-venv python3-pip
pip3 install -r requirements.txt
pip3 install pylint