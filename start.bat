@echo off
cd /d "%~dp0"
title Compiler-AI
echo Compiler-AI
echo Abra http://127.0.0.1:5000 no navegador apos iniciar.
echo Mantenha esta janela aberta enquanto usa a aplicacao.
echo.
python api.py
pause
