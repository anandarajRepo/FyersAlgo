#!/bin/bash
cd /root/FyersAlgo
source venv/bin/activate
python main_enhanced_scalping.py scalping >> /var/log/scalping.log 2>&1