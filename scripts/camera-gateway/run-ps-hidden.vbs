' MOBILMAJAK - run PowerShell script with no visible window (Task Scheduler)
Option Explicit
If WScript.Arguments.Count < 1 Then WScript.Quit 1
Dim shell
Set shell = CreateObject("Wscript.Shell")
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden " & WScript.Arguments(0), 0, False
