# Repository-Anweisungen

## Build und Paket

Linux-Cross-Build ausschließlich mit rootless Podman, ohne Microsoft-SDK.
Build- und Prüfbefehle stehen in COMPILE.md. Eingaben in build/inputs.lock.json
prüfen; Versionswechsel in allen Skripten, Image-Tags, Tests und Dokumenten
zusammenhängend durchführen. Keine Signatur- oder Hashprüfungen abschalten.
Erzeugte Artefakte und Diagnose-Rohdaten nur in den ignorierten Verzeichnissen
dist/ und work/ ablegen. Fremde Änderungen erhalten, eigene Dateien gezielt stagen.

ZIPs ohne Man-/Info-Handbuchseiten, mit Windows-kompatiblen Dateinamen,
vollständigem Manifest, SHA256SUMS und Prüfer ausliefern. Lizenzhinweise,
Installations-, Benutzer- und Fehlerhilfe erhalten. Keine privaten Schlüssel,
Kennwörter oder Umgebungskonfigurationen paketieren.

## Installation

Nur LocalSystem-Dienste unterstützen; wirkungslose Konto-/Passwortoptionen
ohne Geheimnisausgabe abweisen. Defaultvorlagen erhalten; --yes darf bestehende
Konfigurationen nicht löschen. Explizite Ports einschließlich 22 prüfen.
SYSTEM-ACL als Gruppe g:18 setzen; sichtbare nicht fatale Warnung erhalten.
Bereits korrekte Besitzer anhand UID nicht erneut ändern. Keine pauschalen
NTFS-Rechteänderungen am Installationsstamm.

Jeder Bash-Aufruf ohne Profile braucht einen expliziten Cygwin-PATH, entweder
im Skript oder vor dem Kommando. Native Exitcodes anhand des global aktualisierten
LASTEXITCODE prüfen. Konfiguration mit Robocopy /B /COPY:DAT unter Erhalt von
Besitzer/ACL bearbeiten, Sicherung/Übernahme mit /B /COPYALL beschreiben.

install-user.cmd unterstützt vorhandene aktivierte lokale Nicht-Administratoren
mit neuem /home/NAME. Bestehende Homes nicht überschreiben; keine Konten,
Kennwörter oder Gruppen ändern. SID, Gruppen, Schlüssel, 700/700/600 und globale
AllowUsers prüfen. Match nicht ändern, Include und komplexe Muster manuell prüfen.
Nur eigenen Dienst steuern. Bei Mutationsfehlern Konfiguration zurückspielen,
Dienst gestoppt lassen. -Start und -NoRestart sind gegenseitig ausgeschlossen.

## Prüfungen und Veröffentlichung

Geänderte Shellskripte vor jedem Commit mit shellcheck -S warning prüfen.
Paket-/DLL-/Versionsnachweise, Regressionen, PowerShell und Wine vor Release
ausführen. Windows-Mocks und Wine nicht als native Windows-Abnahme ausgeben.
Grenzen neuer Skriptpfade benennen; bis zur vollständigen Abnahme Prereleases.
Geprüfte eigene Änderungen committen und pushen. Neue Release-Tags und Assets
verwenden; bestehende veröffentlichte Tags/Assets nicht ersetzen.

Öffentliche Dokumentation portabel halten: keine privaten Hostnamen, absoluten
Workspace-Pfade, Betriebsberichte, Automatisierungspläne oder Testumgebungen.
README kurz mit Zweck und beiden Installationswegen; Builddetails in COMPILE.md.
Bekannte Runtime-Grenzen allgemein in docs/troubleshooting.md dokumentieren.
Keine ungeprüften Profil-/Hive-/PATH-Eingriffe oder Eingriffe auf fremden Systemen.
