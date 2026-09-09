@echo off
chcp 65001 > nul
color 0A
title Publicar Dash_InfectoCast no GitHub
echo =======================================================
echo     PUBLICANDO DASH_INFECTOCAST NO GITHUB PAGES...
echo =======================================================
echo.
cd /d "%~dp0"

echo 1. Adicionando arquivos modificados...
git add .

echo.
echo 2. Criando commit de atualizacao...
git commit -m "atualizacao do painel InfectoCast Academy"

echo.
echo 3. Enviando para o GitHub (https://github.com/joserand-alt/Dash_InfectoCast.git)...
git push -u origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo =======================================================
    echo  [SUCESSO] Dashboard enviado ao GitHub com sucesso!
    echo  Disponivel em: https://joserand-alt.github.io/Dash_InfectoCast/
    echo =======================================================
) else (
    echo =======================================================
    echo  [ATENCAO] Ocorreu algum erro ou repositorio remoto pendente.
    echo =======================================================
)
echo.
pause
