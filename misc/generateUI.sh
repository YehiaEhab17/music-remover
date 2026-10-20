#!/bin/bash

cd /home/Yehia/repos/music-remover/GUI
pyuic6 -x main.ui -o main.py
pyuic6 -x dialog.ui -o dialog.py
pyuic6 -x settings.ui -o settings.py

echo "done"
