# Paketrevision 5: Nicht-Administrator-Einrichtung

Stand: 19.10.2026. Vorgänger `v10.6p1-cygwin.4`, Commit
`d43972192252354633199c4df70627108d088af5`.
OpenSSH 10.6p1, Cygwin 3.6.11-1 und OpenSSL 3.5.9-1 unverändert. Alle 282
PE-Dateien sind bytegleich zum ZIP der Revision 4; gezielt neu paketiert,
kein erneuter Binärbuild und keine neuen Sicherheitsupdates.

## Einrichtungshelfer

Zusätzlich zu install-server.cmd gibt es **install-user.cmd** für ein vorhandenes
aktiviertes lokales Nicht-Administrator-Konto mit neuem Cygwin-Home:

```powershell
.\install-user.cmd sshtest 'C:\Keys\sshtest.pub'
```

Der Administrator führt den Helfer aus. Der Server bleibt LocalSystem, spätere
Benutzersitzungen erhalten ihre Benutzerrechte. Konto-/SID-/Gruppenprüfung,
öffentlicher Schlüssel, gezielte Besitzer und 700/700/600 werden eingerichtet.
Keine Windows-Konten, Kennwörter oder Gruppen werden geändert. Vorhandene Homes
werden abgewiesen und nicht überschrieben; keine privaten Schlüssel verarbeiten.

Globale bestehende AllowUsers ohne Doppeleintrag ergänzen, Match unverändert
lassen, Includes zur manuellen Prüfung ablehnen. SYSTEM-Konfiguration über
Robocopy /B /COPY:DAT sichern/zurückschreiben, Besitzer/ACL vergleichen und sichern,
Syntax prüfen. Nur die passende Dienstregistrierung stoppen/starten. Ein zuvor
gestoppter Dienst bleibt gestoppt, ebenso bei -NoRestart. Nach Mutationsfehlern
erneut stoppen, Konfiguration zurückspielen und eine manuelle Prüfung verlangen.
Ein neues Home bleibt in Fehlerfällen zur Prüfung erhalten.

Anleitung im ZIP unter **NONADMIN-USERS.md**, einschließlich Entfernen, Profil,
PATH und Prüfung des eingeschränkten Tokens. INSTALLATION.md beschreibt jetzt
auch das konkrete Bearbeiten der SYSTEM-Konfiguration, etwa für LogLevel.

## Native Teilabnahme und Grenzen

Die [Nutzerrückmeldung zu Revision 4](windows-validation-nonadmin-2026-10-19.md)
bestätigt bei manueller Einrichtung auf Windows Server Build 26100 / PowerShell
5.1 Schlüsselanmeldung mit strikter Hostschlüsselprüfung, /home/sshtest,
abgewiesene Passwortanmeldung, Exitcode 5, TTY und 10-MB-SCP/SFTP mit identischen
Hashes. PowerShell meldet Admin=False und Medium Mandatory Level; Schreiben
nach C:\Windows, Lesen privater Hostschlüssel/sshd_config und Dienststopp wurden
verweigert. Die AllowUsers-Liste war eine lokale Ergänzung zur Paketvorlage.

Der **neue Helfer selbst ist noch nicht nativ unter Windows abgenommen**.
Domänenkonten, zusätzliche Gruppen, andere Homepfade, gleichzeitige Sitzungen,
Ansible, Reboot/Rückkehr, Profilentladung und reale Last bleiben offen. Die
früheren Teilabnahmen ersetzen keine Prüfung des neuen Helfers. Prerelease.

## Profil- und Umgebungsprüfung

Die Quellprüfung des mitgelieferten Cygwin 3.6.11 findet in
`newlib-cygwin/winsup/cygwin/sec/auth.cc:220-226` einen ausdrücklichen Kommentar:
Das sichere Entladen des Profils ist ungelöst; ein Registry-Handle wird vorerst
bewusst nicht freigegeben. `load_user_profile` ruft dort in Zeile 308
LoadUserProfileW auf; der UID-Wechsel ruft die Funktion in syscalls.cc:3649 auf.
Das ist ein konkreter Cygwin-Hinweis zum beobachteten geladenen Profil,
**kein Nachweis eines S4U-Tokenlecks oder gemessenen Speicherwachstums**.
Im untersuchten Cygwin-CC/H-Bestand kein UnloadUserProfile-Aufruf gefunden.
OpenSSH setzt in session.c:496 und :617 den Impersonation-Token im Elternpfad
zurück; daraus folgt keine Garantie der Profilentladung nach Sitzungsende.
Kein ungeprüfter Runtime-Patch und kein erzwungenes reg unload eingeführt.

`openbsd-compat/bsd-cygwin_util.c:92` führt PATH ausdrücklich als aus der
Dienstumgebung zu übernehmende Variable. Das erklärt die SYSTEM-Pfade in der
Sitzung. Globaler PATH unverändert; `command -v` statt fehlendem which dokumentiert.
Der einmalige nicht reproduzierbare Ausgabeausfall ist nur als Hinweis erfasst.

Reproduktion aus dem lokalen Quellbestand (GNU tar 1.35, sed 4.9):

```sh
tar -xOf work/downloads/src/release/cygwin/cygwin-3.6.11-1-src.tar.xz \
  cygwin-3.6.11-1.src/newlib-cygwin-3.6.11.tar.bz2 |
  tar -xOjf - newlib-cygwin/winsup/cygwin/sec/auth.cc |
  nl -ba | sed -n '216,231p;302,311p'
```

Eingabe-SHA-256 Cygwin-Quellpaket:
`21732da41e1a4eee6ec44d64edc6645ffa3df66dec671889bc9a2b8cdfa6613f`.
OpenSSH session.c: `6c913f89f5679d74c44d7a55166dd972a246cd5208a9d3416c197a7de48672e5`;
bsd-cygwin_util.c: `ff508ea2515750646093777b6fca67e8f60ad8cde28605f4f76e6d8212f1aeff`.
Exakte Kommandos, Hostzeiten und Rohbefunde: lokal unter
`work/evidence/r5-profile-source-03` und `r5-profile-proof-01`.

## Prüfungen

Rootless Podman 4.9.3, Python 3.12.3, Bash 5.2, ShellCheck 0.9.0;
vollständige Builder-RPM-/Compilerdaten im Manifest. Evidenz unter work/evidence:

| Nachweis | Ergebnis / Ordner |
| --- | --- |
| Paketierung, unveränderte 282 PE-Dateien | PASS; r5-package-06 |
| ZIP/CRC/Windows-Pfade, keine Handbücher, Vorlagen, vollständige Hashliste | PASS; r5-check-04 |
| Vollständigkeit | 1967 ZIP-Dateien, davon 1966 im Manifest, Manifest selbst ausgenommen |
| Bash-/Paketregressionen | 18 Tests PASS; r5-regression-03 |
| Benutzerhelfer, tatsächliches entpacktes Modul | 89 Checks PASS; r5-user-helper-05 |
| Helferprüfungen | Policy, Namen/Keys, SID/Home/Admin, Dienstzuordnung, Besitzerziele, Stop/Start, Fehler/Rollback |
| Prüfer unter PowerShell 7.4.7/Linux | 1965 Nutzdateien und negative Fälle PASS; r5-powershell-03 |
| Wine: Versionen, Bash, neuer Testschlüssel, sshd -t | PASS, bekannte FAST_CWD-Warnung; r5-wine-03 |
| ShellCheck und Git-Diff-Prüfung | PASS |

Die PowerShell-Helfertests ersetzen Windows-Konto-, NTFS-, Dienst- und
Backupmodus-Aufrufe durch kontrollierte Testfunktionen. Damit sind Ablauf und
Fehlerbehandlung geprüft, **nicht die tatsächlichen Windows-Rechteoperationen**.
Die Tests belegen keinen echten Nicht-Administrator-Login des neuen Helfers.
Native Exitcodes wurden zusätzlich mit echten Linux-Prozessen geprüft:
Exit 8 abweisen, Exit 7 nur bei ausdrücklicher Freigabe akzeptieren und fehlende
Programme ablehnen. Der Wrapper liest den global aktualisierten LASTEXITCODE;
eine lokale Variable würde ihn verdecken und Fehler übersehen.

## Artefakte

| Datei | Byte | SHA-256 |
| --- | ---: | --- |
| openssh-10.6p1-cygwin-x86_64.zip | 50705727 | `60b721d288d207696f51fd33a561c6758a9345fcffbba8efef086a75bda402aa` |
| openssh-10.6p1-cygwin-x86_64-sources.tar | 244295680 | `5137245b218012e3739c4c1b8075afe57b7a70feaa30883a641b3a07a46b06df` |

Dazu SHA256SUMS. Das Quellenarchiv bleibt gegenüber Revision 4 bytegleich;
die neuen Einrichtungshelfer liegen als lesbare Skripte im ZIP und im Git-Tag.
