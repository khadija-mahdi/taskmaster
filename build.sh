# Build script for Taskmaster
# This script sets up the environment and runs the Taskmaster application.

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

#source build.sh