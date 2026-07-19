@echo off
rem Git 仅通过此 helper 获取 Jenkins 注入的受控凭据，禁止记录凭据或远端地址。
setlocal DisableDelayedExpansion
echo %~1 | findstr /I "username" >nul
if not errorlevel 1 (
  <nul set /p "=%CATALOG_GIT_PUSH_USERNAME%"
) else (
  <nul set /p "=%CATALOG_GIT_PUSH_PASSWORD%"
)
