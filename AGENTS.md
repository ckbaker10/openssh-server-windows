# Anweisungen für dieses Repository

Die Regeln aus `/opt/paseo-development/AGENTS.md` gelten zusätzlich.

## Wiederkehrende Pflege durch Prompt Patrol

Der maßgebliche offene Dauerplan liegt unter
`/opt/paseo-development/ai-repo-plans/openssh-server-windows/002-dauerplan-wochenpflege-github-releases.md`.
Vor einem automatischen Wartungslauf diesen Plan und seine letzten Laufprotokolle lesen.
Der Plan bleibt dauerhaft offen und wird nach einem Wochenlauf nicht nach `X_` umbenannt.

Der Nutzer hat am 19.10.2026 ausdrücklich die eigenständige wöchentliche Pflege
und Veröffentlichung neuer GitHub-Releases für `ckbaker10/openssh-server-windows`
autorisiert. Geeignete OpenSSH-, Cygwin-, OpenSSL- und Laufzeitupdates nach den
Prüfungen des Plans integrieren, committen, pushen und veröffentlichen; für diese
Routineaktionen keine erneute Nutzerbestätigung verlangen. Parallele Worker
über Lease, gemeinsame Reservierung und Laufprotokolle koordinieren.

Linux-Cross-Builds ausschließlich mit rootless Podman, ohne Microsoft-SDK.
Versionen aus dem geprüften Kandidaten-/Lockstand ableiten; die ursprünglichen
festen Versionsliterale bei Updates zusammenhängend anpassen oder ablösen.
Artefakte und Rohdaten bleiben in den ignorierten Verzeichnissen `dist/` und `work/`.

Windows-ZIPs ohne Man- und Info-Handbuchseiten ausliefern. Alle Archivpfade auf
Windows-kompatible Namen prüfen und jede ausgelieferte Datei außer dem Manifest
selbst mit ihrem Hash im Manifest erfassen. Lizenzhinweise und die Installationsanleitung mitliefern.

Defaultvorlagen unter `/etc/defaults/etc` erhalten. `--yes` darf bestehende
Konfigurationen nicht löschen; Portänderungen einschließlich 22 prüfen.
Nur LocalSystem unterstützen, Konto-/Passwortargumente ohne Geheimnisausgabe
abweisen. NSS-Home und Shell-HOME konsistent halten, Zustandsverzeichnisse im ZIP
erhalten, Dateilogs und Rotation dokumentieren. Nutzdatei-SHA256SUMS samt
PowerShell-Prüfer mitliefern. Bestehende NTFS-/Benutzerrechte nicht pauschal ändern.
Den nativen Teilbefund in `docs/windows-validation-2026-10-19.md` nicht als
vollständige Abnahme neuer Installer, Neustarts oder Aktualisierungen auslegen.
Revision 3 hat eine Teilabnahme mit Workarounds unter
`docs/windows-validation-revision3-2026-10-19.md`. SYSTEM-ACL als Gruppe `g:18`
setzen und Fehler sichtbar, aber nicht fatal behandeln. Bereits korrekte
Dienstdateibesitzer erhalten; echte chown-Fehler nicht verschweigen.
PowerShell-Standardpfad erst nach Parameterbindung mit MyInvocation-Rückfall
auflösen; explizites `-Path` dokumentieren. Robocopy-Sicherung und Übernahme
mit `/B` beschreiben, damit private Hostschlüssel vollständig erhalten bleiben.

Nicht-Administrator-Konten über `install-user.cmd` für bestehende lokale,
aktivierte Konten mit neuem /home/NAME einrichten. Vorhandene Homes nicht
überschreiben, keine Konten/Passwörter/Gruppen automatisch ändern. SID- und
Gruppenprüfung, gezielte Besitzer/700/700/600, Backupmodus und ACL-Erhalt für
SYSTEM-Konfiguration, globale vorhandene AllowUsers ohne Duplikate erhalten.
Include-Konfigurationen manuell prüfen; Match-Blöcke nicht verändern. Nur eigenen
Dienst steuern, bei Mutationsfehlern Konfiguration zurückspielen und Dienst
gestoppt lassen. Tests/check-user-setup.ps1 mit Windows-Mocks ist keine native
Abnahme. Native manuelle Teilabnahme unter docs/windows-validation-nonadmin-2026-10-19.md.
Geladenes Windows-Profil nicht als bewiesenes Tokenleck darstellen: Cygwin hat
in sec/auth.cc einen offenen TODO zum zuverlässigen Profilentladen. Keine
erzwungenen Hive-/Profil-/PATH-Änderungen ohne eigene Prüfung.

ZIP-Prüfung, DLL-/Versionsnachweise und ergänzende Laufzeittests vor Veröffentlichung
ausführen. Ohne belegte native Windows-Abnahme weiterhin Prereleases veröffentlichen
und diese Grenze nennen. Keine bestehenden Release-Tags verschieben oder bereits
veröffentlichte Assets ersetzen. Keine Installation auf produktiven Windows-Systemen.
