# Paketrevision 4: Aktualisierung unter Windows

Stand: 19.10.2026. Vorgänger `v10.6p1-cygwin.3`, Commit
`7f806529e354211cd5560e576a15f2e592d9d7d4`.
OpenSSH 10.6p1, Cygwin 3.6.11-1 und OpenSSL 3.5.9-1 unverändert.
Alle 282 PE-Dateien sind bytegleich zur Revision 3; erneut paketiert, ohne
die unveränderten Binärdateien neu zu kompilieren. Keine neuen Sicherheitsupdates.

## Korrekturen

- SYSTEM-Verzeichnis-ACL als `g:18:rwx` statt `u:18:rwx`; Fehler werden sichtbar
  gemeldet, brechen die Einrichtung aber nicht mehr ab. SYSTEM-Zugriff vor Start prüfen.
- Der Prüfer ermittelt den Defaultpfad erst nach Parameterbindung; bei leerem
  PSScriptRoot dient MyInvocation.MyCommand.Path als Rückfall. Fehlen beide,
  folgt eine verständliche Aufforderung zu -Path statt GetFullPath mit leerem Wert.
- Der Cygwin-Helfer prüft vor jedem Dienstdatei-chown die numerische Besitzer-UID.
  Stimmt sie mit dem Dienstkonto überein, bleiben Besitzer und Gruppe unverändert.
  Bei abweichendem Besitzer erfolgt weiterhin chown auf Dienstkonto/Gruppe 544;
  Fehler bleiben Warnungen. Schlüssel werden nicht gelockert oder neu erzeugt.
- Die Schlüsselerzeugungsmeldung beschreibt das idempotente `ssh-keygen -A`
  ausdrücklich als Prüfung/Ergänzung fehlender Schlüssel.
- Robocopy `/B` für Sicherung **und** Übernahme, benötigte Rechte und Prüfung
  privater Hostschlüssel dokumentiert. PowerShell-Beispiele verwenden -Path.

## Nachweise

Rootless Podman 4.9.3, Python 3.12.3, ShellCheck 0.9.0. Vollständige Cross-
Werkzeug-/RPM-Versionen stehen im Manifest. Lokale Evidenz unter `work/evidence/`
enthält genaue Befehle, Eingabe-SHA-256, Hostzeiten, Exitstatus und Rohlogs:

| Prüfung | Ergebnis | Evidenz |
| --- | --- | --- |
| Paketierung / Patch ohne Fuzz | PASS | r4-package-01 |
| ZIP, Windows-Pfade, keine Man-/Info-Seiten, vollständiges Manifest | PASS | r4-check-01 |
| 282 x86_64-PE-Dateien / vollständige DLL-Imports | PASS | r4-check-01 |
| Vorlagen, Konfiguration, NSS, LF, keine privaten Schlüssel im Paket | PASS | r4-check-01 |
| 14 Regressionstests | PASS | r4-regression-01 |
| ACL-Fehler ohne Abbruch; UID gleich/abweichend/chown fehlgeschlagen | PASS, isolierte Befehlsstubs | r4-regression-01 |
| PowerShell 7.4.7/Linux, 1960 Nutzdateien | PASS | r4-powershell-01 |
| Defaultpfad aus anderem CWD und nicht interaktiv per EncodedCommand | PASS | r4-powershell-01 |
| Erzwungen leerer ScriptRoot, MyInvocation-Rückfall | PASS | r4-powershell-01 |
| Prüfer: manipuliert, leer, doppelt, Pfadausbruch, fehlend | jeweils abgewiesen | r4-powershell-01 |
| Wine: Versionen, Bash, neuer Ed25519-Schlüssel, sshd -t | PASS, bekannte FAST_CWD-Warnung | r4-wine-01 |
| ShellCheck / Git-Diff-Prüfung | PASS | lokale Prüfungen |

Die [native Teilabnahme von Revision 3](windows-validation-revision3-2026-10-19.md)
bestätigt unter Windows Server Build 26100 und PowerShell 5.1.26100 die
Paketprüfung mit -Path, Home, Dateilogs, unveränderte Hostschlüssel und die
Funktionstests über einen Sprunghost. Der unveränderte Installer scheiterte;
die Aktualisierung gelang erst mit ACL-/Robocopy-Workarounds. Diese Korrekturen
der Revision 4 sind lokal geprüft, aber **noch nicht nativ unter Windows**.
Der frühere Wine-NSS-Exit 139 bleibt dokumentiert; er ersetzt nicht den jetzt
positiven nativen Fernsitzungsbefund zur Home-Auflösung.

Offen: unveränderter Installer der Revision 4, Standardpfad ohne -Path unter
Windows PowerShell 5.1, Warnungsfreiheit, Rotation, Neustart, Rückkehr, Netzwerk
ohne Sprunghost, Freigaben und Ansible. Deshalb weiterhin **Prerelease**.

## Artefakte

| Datei | Byte | SHA-256 |
| --- | ---: | --- |
| openssh-10.6p1-cygwin-x86_64.zip | 50694409 | `b8b85e224065031450889fe7a77ae1d12b796e3076912a507975b209233852dc` |
| openssh-10.6p1-cygwin-x86_64-sources.tar | 244295680 | `5137245b218012e3739c4c1b8075afe57b7a70feaa30883a641b3a07a46b06df` |

Dazu SHA256SUMS. Anleitung im ZIP als INSTALLATION.md sowie unter
`docs/windows-installation.md`. Originalquellen und Buildpatches im Quellenarchiv.
