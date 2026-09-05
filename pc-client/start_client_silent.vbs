' Startet den PC-Client ohne sichtbares Konsolenfenster.
' Eine Verknuepfung zu DIESER Datei in den Autostart-Ordner legen (shell:startup).
Set objShell = CreateObject("WScript.Shell")
strPath = objShell.CurrentDirectory
objShell.CurrentDirectory = strPath
objShell.Run """" & strPath & "\venv\Scripts\pythonw.exe"" """ & strPath & "\client.py""", 0, False
