# Paketrevision 3: Windows-Installationsrückmeldung

Stand: 19.10.2026. Vorgänger: `v10.6p1-cygwin.2`, Commit
`df6ae91ee4ddd0cc490bcbd478a58705ee3d9279`.
OpenSSH 10.6p1, Cygwin 3.6.11-1, OpenSSL 3.5.9-1 bleiben unverändert.
Alle **282 PE-Dateien sind bytegleich** zum ZIP der Revision 2. Daher wurde
gezielt neu paketiert, ohne die unveränderten Binärdateien erneut zu kompilieren.
Der ursprüngliche Cross-Build ist in `build-validation.md` dokumentiert.

## Änderungen

- Vorlagen für SSH und NSS unter `/etc/defaults/etc`; bestehende Konfigurationen
  werden gesichert und auch bei `--yes` erhalten. Explizite Portänderungen
  einschließlich Port 22 bzw. einer bisher fehlenden Port-Direktive funktionieren.
- Unterstützt wird LocalSystem. Konto-/Passwortoptionen werden vor allen
  Installationsaktionen abgewiesen, ohne übergebene Kennwörter auszugeben.
- Leere Zustandsverzeichnisse sind ZIP-Einträge. Kein pauschales `chmod` mehr am
  Installationswurzelverzeichnis; gezielte Besitzvorbereitung der Zustandsdateien.
- NSS setzt `/home/%U`; `open-shell.cmd` übernimmt das Konto-Home statt eines
  widersprechenden geerbten Windows-`HOME`.
- Neue Dienstregistrierungen nutzen `-E /var/log/sshd.log`. Bestehende Dienste
  müssen zum Ändern ihrer Argumente gestoppt, entfernt und neu registriert werden.
- Paketinterne `SHA256SUMS` und `verify-package.ps1` ohne JSON-Abhängigkeit;
  Anleitung für Besitzer, StrictModes, LF, Rotation, NTFS-ACLs und Aktualisierung.
- Weiterhin keine Man-/Info-Handbuchseiten oder kollidierenden Windows-Dateinamen.

## Prüfungen und Grenzen

Rootless Podman 4.9.3, Host-Python 3.12.3, ShellCheck 0.9.0; Cross-Werkzeuge
und vollständige RPM-Versionen stehen im Paketmanifest. Hostzeiten, Eingabehashes,
Befehle, Exitstatus und Rohlogs sind lokal unter `work/evidence/` erhalten:

| Nachweis | Ergebnis / Evidenzordner |
| --- | --- |
| Paketierung, Patch ohne Fuzz, DLL-Imports | PASS; `package-install-fixes-04` |
| ZIP-CRC, Windows-Pfade, leere Verzeichnisse, keine Handbücher | PASS; `check-install-fixes-02` |
| Vollständiges Manifest / Dateihashes | 1961 Dateien im Manifest plus Manifest selbst; PASS |
| Serverkonfiguration, NSS, Vorlagen, LF, keine Hostschlüssel | PASS; `check-install-fixes-02` |
| Regressionen | 12 Tests PASS; `regression-install-fixes-02` |
| PowerShell-Prüfer | 1960 Nutzdateien, 0 Fehler; `powershell-install-fixes-02` |
| Fehlerfälle des Prüfers | manipuliert, leer, doppelt, Pfadausbruch, fehlend jeweils abgewiesen |
| PowerShell-Laufzeit | 7.4.7 auf Linux; Syntax für 5.1, keine native 5.1-Abnahme |
| Wine-Mindestumfang | Versionen, Bash, neuer Ed25519-Schlüssel, `sshd -t`: PASS; `wine-install-fixes-03` |
| ShellCheck, Hadolint, Git-Diff-Prüfung | PASS |

Der zusätzliche Wine-Versuch der echten NSS-/Home-Auflösung endete mit Exit 139
(`wine-install-fixes-01`). Er ist **nicht bestanden** und nicht Teil des positiven
Wine-Mindestumfangs. Die Shell-Übernahme des aufgelösten Homes ist mit isolierter
Kontenabfrage getestet; die tatsächliche Windows-NSS-Auflösung bleibt offen.
Wine meldet weiterhin die bekannte `FAST_CWD`-Warnung. Frühere fehlgeschlagene
Patch-Erstellungsläufe bleiben unter `package-install-fixes-01/02` erhalten;
Lauf 03 erzeugte den ersten positiven Kandidaten. Lauf 04 berücksichtigt
zusätzlich eine bereits SYSTEM gehörende Logdatei, ohne vorher Schreibzugriff
darauf vorauszusetzen, und erzeugte die freigegebenen Archive.

Die [Nutzerrückmeldung](windows-validation-2026-10-19.md) bestätigt wesentliche
Serverfunktionen **nur für Revision 1**. Die neuen Installer-/Besitzpfade,
Warnungsfreiheit, tatsächliche Home-Auflösung und Logrotation sind noch nicht
nativ abgenommen. Neustart, Update/Rückkehr, Freigaben, Ansible und echtes Netz
ebenfalls offen. Deshalb weiterhin **Prerelease**.

## Artefakte

| Datei | Byte | SHA-256 |
| --- | ---: | --- |
| `openssh-10.6p1-cygwin-x86_64.zip` | 50693270 | `a9f72178ae1fc4f9982dbb215fecef60c568fb460d18935e72f593bc4733ba12` |
| `openssh-10.6p1-cygwin-x86_64-sources.tar` | 244295680 | `20974a8d8dbef8d3c28194ed16cc1625e1f027b5b523d790e631601610b7a8b9` |

Die Release-Assets enthalten außerdem `SHA256SUMS`. Eine Anleitung liegt im ZIP
als `INSTALLATION.md` und im Repository unter `docs/windows-installation.md`.
