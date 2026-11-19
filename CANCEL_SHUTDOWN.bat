@echo off
title Umbrella emergency shutdown abort
shutdown /a
if errorlevel 1 (
  echo No scheduled shutdown found, or the timeout has expired.
) else (
  echo Windows shutdown request cancelled.
)
pause
