# Native Nicht-Administrator-Teilabnahme vom 19.10.2026

Quelle: Nutzerrückmeldung zu **v10.6p1-cygwin.4**, nicht produktiver Windows
Server Build 26100, Windows PowerShell 5.1, LocalSystem-Dienst, Port 2222.
Getestet wurde ein lokales Konto ausschließlich in der Gruppe Benutzer, mit
Schlüsselanmeldung und von Hand eingerichteten Besitzer-/POSIX-Rechten.
Die externen Vorgängerberichte wurden hier nicht eingesehen. Interner Hostname
und konkrete Installationspfade werden nicht veröffentlicht.

| Prüfung | Ergebnis laut Rückmeldung |
| --- | --- |
| Schlüsselanmeldung / striktes known_hosts | erfolgreich; Home /home/sshtest |
| Passwortanmeldung | Permission denied (publickey) |
| Exitcode / TTY | Exitcode 5, interaktive Bash erfolgreich |
| SCP-Upload / SFTP-Download | 10 MB, SHA-256 identisch |
| PowerShell EncodedCommand | Admin=False |
| Token / Gruppen | Users, Medium Mandatory Level, keine Administrators |
| Schreiben nach C:\Windows | verweigert |
| Lesen von sshd_config / privaten Hostschlüsseln | verweigert |
| Dienst stoppen | verweigert |

Manuelle Einrichtung benötigte gezielte Besitzerwechsel auf Home, .ssh und
authorized_keys, Modi 700/700/600 sowie eine Änderung der lokalen AllowUsers-
Liste über Robocopy /B /COPY:DAT. Die unveränderte Paketvorlage besitzt keine
AllowUsers-Direktive; diese Liste war eine zusätzliche lokale Einschränkung.

Beobachtet: Das Windows-Profil blieb nach Abmeldung und Dienststopp geladen;
Löschen des Kontos entlud es nicht. Profilentfernung gelang erst nach Neustart.
Die Vermutung eines nicht freigegebenen S4U-Tokens ist nicht bestätigt.
PATH enthielt Einträge der SYSTEM-Umgebung und einer weiteren OpenSSH-Installation.
`which` fehlt; Bash bietet dafür `command -v`. Eine einmalige leere Ausgabe
bei korrektem Exitcode war nicht reproduzierbar und ist kein gesicherter Fehler.

Nicht geprüft: Domänenkonten, zusätzliche Gruppen, Ansible/ähnliche Werkzeuge,
gleichzeitige Sitzungen und andere db_home-Pfade. Der neue Einrichtungshelfer
der folgenden Paketrevision war nicht Bestandteil dieses Windows-Tests.
