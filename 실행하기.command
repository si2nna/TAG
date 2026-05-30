#!/bin/bash

cd "$(dirname "$0")"

if command -v python3 &>/dev/null; then
    python3 -m pip install -q pillow customtkinter
    python3 notion_gallery.py
else
    echo "Python 3가 설치되어 있지 않습니다."
    echo "https://www.python.org/downloads/"
fi