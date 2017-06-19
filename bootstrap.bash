#!/usr/bin/env bash
command -v conda >/dev/null 2>&1 || { echo >&2 "The command 'conda' is not installed. Aborting."; exit 1; }

conda env create -f environment.yml

# Install chromedriver
if ! command -v chromedriver; then
    echo "'chromedriver' is not installed. Installing..."
    command -v git >/dev/null 2>&1 || { echo >&2 "The command 'git' is not installed. Aborting."; exit 1; }
    git clone https://github.com/peterhudec/chromedriver_installer.git /tmp/chromedriver_installer
    cd /tmp/chromedriver_installer
    python setup.py install
    cd -
fi

