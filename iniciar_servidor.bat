@echo off
chcp 65001 > nul
title Servidor Local Dash_InfectoCast
color 0A
echo ========================================================
echo   INICIANDO SERVIDOR LOCAL DO PAINEL INFECTOCAST...
echo   Porta: 8085 (Backend de Atualizacoes das APIs)
echo ========================================================
echo.
cd /d "%~dp0"
python server.py
pause
