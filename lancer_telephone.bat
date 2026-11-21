@echo off
REM Boussoles accessibles depuis le telephone (meme Wi-Fi, ou Tailscale)
cd /d "%~dp0"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo Sur le telephone, ouvre http://ADRESSE:8501 avec ADRESSE =%%a
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
