# Native Windows-Teilabnahme der Revision 3 vom 19.10.2026

Quelle: Nutzerrückmeldung; nicht produktiver Windows Server Build 26100,
Windows PowerShell 5.1.26100. Der externe Vorgängerbericht wurde hier nicht
eingesehen. Rechnername und interne Pfade werden nicht veröffentlicht.

Geprüft: v10.6p1-cygwin.3, ZIP 50.693.270 Byte, SHA-256
`a9f72178ae1fc4f9982dbb215fecef60c568fb460d18935e72f593bc4733ba12`.
Aktualisierung von Revision 1 nach Abschnitt 5 der Anleitung, **mit Workarounds**:
Gruppen- statt Benutzer-ACL, expliziter Prüferpfad und Robocopy-Backupmodus.
Der unveränderte Installer brach bei `setfacl -m u:18:rwx` mit Permission denied ab.

| Prüfung | Ergebnis laut Nutzerrückmeldung |
| --- | --- |
| Entpacken | 1962 Dateien, 356 Ordner, keine Fehler/Namenskollisionen |
| Paketprüfer unter PowerShell 5.1 | mit -Path PASS, 1960 Dateien, 0 Fehler |
| Konfiguration / Vorlagen | --yes erhält sshd_config, Sicherung angelegt, Defaults vorhanden |
| Home in Fernsitzung | /home/Administrator mit nsswitch.conf |
| Dienst / Dateilog | LocalSystem, sshd.log, Port 2222 |
| Hostschlüssel | unverändert übernommen, strikte Hostschlüsselprüfung bestanden |
| Anmeldung / Token | Schlüsselanmeldung, whoami, voller PowerShell-Admin-Token |
| Exitcodes / Passwort / TTY | erfolgreich, Passwort abgewiesen, TTY funktioniert |
| SCP-Upload / SFTP-Download | 30 MB, SHA-256 identisch |

Neue Befunde: SYSTEM ist in der ACL-Sicht Gruppeneintrag; `g:18` ermöglichte die
Einrichtung. Der Prüfer-Standardpfad war in nicht interaktivem PowerShell 5.1 leer;
explizites -Path funktionierte. Nur SYSTEM lesbare private Hostschlüssel fehlten
bei Robocopy /COPYALL (Exit 8); mit /B wurden sie vollständig mit Rechten kopiert.
Acht chown-Warnungen trotz bereits korrektem SYSTEM-Besitzer, danach Dienststart
erfolgreich. `ssh-keygen -A` ergänzte keine Dateien und ersetzte keine Schlüssel.

Revision 4 korrigiert diese Punkte; ihre neuen Installer-/Prüferpfade sind noch
nicht nativ abgenommen. Die übrigen Tests erfolgten über einen Sprunghost;
ohne Sprunghost, Windows-Neustart, Rückkehr, Freigaben und Ansible/ähnliche
Werkzeuge bleiben ungetestet. Logrotation ist ebenfalls nicht als geprüft belegt.
Der zusätzliche Wine-NSS-Absturz aus dem Bericht zu Revision 3 bleibt ein
separater Wine-Befund; die native Fernsitzung bestätigt nun den NSS-Homepfad.
