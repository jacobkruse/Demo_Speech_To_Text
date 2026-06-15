#!/bin/sh
# Loi tat doc chinh ta tieng Viet. Chay trong Claude Code:
#   !./d.sh                -> ghi am, im lang ~2s hoac Ctrl+C la dung
#   !./d.sh --silence 3    -> moi tham so deu chuyen tiep cho dictate.py
#   !./d.sh -o ghichu.txt
# (hoac goi:  !sh d.sh ...  neu chua co quyen thuc thi)
exec .venv/Scripts/python.exe dictate.py "$@"
