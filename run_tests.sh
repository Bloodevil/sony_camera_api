#!/bin/sh

pip install -r test-requirements.txt
python -m unittest discover
