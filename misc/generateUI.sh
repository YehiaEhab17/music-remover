#!/bin/bash

cd ~/music-remover/GUI
pyuic6 -x main.ui -o main.py
pyuic6 -x dialog.ui -o dialog.py

echo "done"
