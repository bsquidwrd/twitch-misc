@echo off
cls

set FLASK_APP=main.py
set FLASK_ENG=development

python -m flask run --host=0.0.0.0
