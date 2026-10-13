@echo off
chcp 65001 > nul
title Atualizar Dados das APIs - Dash InfectoCast
color 0B
echo ========================================================
echo   ATUALIZAÇÃO MANUAL DAS APIS (DASH INFECTOCAST)
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/3] Sincronizando Matrículas e Tags com RD Station...
python sync_matriculas_rd.py
echo.

echo [2/3] Consultando APIs (Cativa, Vindi, Asaas, Academy, RD) e gerando Dashboard...
python gerador.py
echo.

echo [3/3] Salvando e publicando no GitHub Pages...
git add index.html dashboard_gerado.html template.html *.json
git commit -m "Manual-Sync: Atualizacao manual via ATUALIZAR_DADOS.bat [skip ci]"
git push origin main
echo.

echo ========================================================
echo   [CONCLUÍDO] Todos os dados foram consultados e salvos!
echo   Dashboard Online: https://joserand-alt.github.io/Dash_InfectoCast/
echo ========================================================
echo.
pause
