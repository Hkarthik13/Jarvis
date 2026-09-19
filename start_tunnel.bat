@echo off
title JARVIS Cloudflare HTTPS Tunnel
cls
echo ======================================================================
echo           ⚡ JARVIS AI - CLOUDFLARE HTTPS TUNNEL EXPOSER ⚡
echo ======================================================================
echo.
echo [+] Exposing Local Backend (http://localhost:8000) with Secure HTTPS...
echo [+] Automatic Free SSL Certificate by Cloudflare
echo [+] Microphone will work natively on all Mobile Browsers without flags!
echo.
echo ======================================================================
echo.
.\cloudflared.exe tunnel --url http://localhost:8000
pause
