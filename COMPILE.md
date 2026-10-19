# Unter Linux bauen

Der Build erzeugt Windows-x86_64-Programme für Cygwin. Er benötigt weder Windows
als Buildsystem noch Microsoft-SDK oder Windows-OpenSSH-Komponenten.

## Voraussetzungen

- Linux x86_64 mit funktionierendem rootless Podman.
- Git, Python ab 3.11 und Netzwerkzugriff für Container- und Paketdownloads.
- Für die Prüfungen: ShellCheck und Hadolint.
- Für eine bewusste Aktualisierung der Paket-Lockdatei zusätzlich GnuPG.

Alle Container als normaler Benutzer starten. Image-Namen sind vollständig
qualifiziert; die mit `localhost/` bezeichneten Images werden selbst gebaut.

## Repository und Build

```sh
git clone https://github.com/ckbaker10/openssh-server-windows.git
cd openssh-server-windows
bash scripts/build.sh
```

Parallelität bei Bedarf einstellen:

```sh
BUILD_JOBS=8 bash scripts/build.sh
```

Das Skript lädt die in `build/inputs.lock.json` festgehaltenen Archive und prüft
Größen und Hashes. Anschließend baut es `build/Containerfile`, stellt den
Cygwin-Sysroot bereit, wendet die Cross-Build-Anpassung an, kompiliert OpenSSH
und führt `scripts/package.py` aus. Der Compiler verwendet das Ziel
`x86_64-pc-cygwin`; OpenSSL und zlib stammen aus den geprüften Cygwin-Paketen.
Kerberos, PAM, libedit und integrierter FIDO-Gerätezugriff sind deaktiviert.

## Ergebnisse

| Datei | Inhalt |
| --- | --- |
| `dist/openssh-10.6p1-cygwin-x86_64.zip` | Server, Clients, Laufzeit, Helfer und Anleitungen |
| `dist/openssh-10.6p1-cygwin-x86_64-sources.tar` | Zugehörige Quellen, signierter Paketindex und Patches |
| `dist/SHA256SUMS` | SHA-256 beider Archive |

Das ZIP enthält ein Buildmanifest mit Dateihashes, DLL-Imports, Paket- und
Werkzeugversionen, außerdem `inputs.lock.json` und eine separate Nutzdatei-
SHA256SUMS samt PowerShell-Prüfer. Jede Datei außer dem Manifest selbst ist im
Manifest erfasst. Die Nutzdateiliste schließt sich selbst und das Manifest aus.
Man-/Info-Handbuchseiten werden entfernt, Windows-Pfade und Namenskollisionen geprüft.

`work/` enthält Downloads, Sysroot und erzeugte Builddaten. Es wird wie `dist/`
nicht eingecheckt. Ein Neubau ersetzt die vom Projekt erzeugten Buildverzeichnisse.
Das Basisimage und die Cross-Toolchain sind festgelegt; die tatsächlich aufgelösten
RPM-Versionen und die Image-ID stehen im Manifest. Unterschiedliche Toolchain-
Images garantieren keine bitidentischen Ergebnisse.

## Paket und Helfer prüfen

Die ZIP-Prüfung muss vor den Tests laufen, die das entpackte Paket verwenden:

```sh
podman run --rm --name openssh-server-windows-check \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-builder:10.6p1 \
  python3 scripts/check-package.py
python3 -m unittest discover -s tests -v
shellcheck -S warning scripts/*.sh packaging/*.sh
hadolint build/Containerfile build/Containerfile.wine
```

PowerShell-Syntax, Paketprüfer und Benutzerhelfer unter Linux prüfen:

```sh
podman run --rm --name openssh-server-windows-powershell-check \
  -v "$PWD:/project:Z" mcr.microsoft.com/powershell:lts-ubuntu-22.04 \
  pwsh -NoProfile -File /project/tests/check-powershell.ps1
podman run --rm --name openssh-server-windows-user-check \
  -v "$PWD:/project:Z" mcr.microsoft.com/powershell:lts-ubuntu-22.04 \
  pwsh -NoProfile -File /project/tests/check-user-setup.ps1
```

Die Benutzerhelfer-Tests ersetzen Windows-Konten, NTFS, Dienststeuerung und
Backupmodus durch kontrollierte Testfunktionen. Sie prüfen Abläufe und Fehler,
ersetzen aber keine Ausführung auf Windows PowerShell 5.1.

## Ergänzender Laufzeittest

```sh
podman build -f build/Containerfile.wine \
  -t localhost/openssh-server-windows-wine:10.6p1 .
podman run --rm --name openssh-server-windows-wine-smoke \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-wine:10.6p1 \
  bash scripts/smoke-wine.sh
```

Wine prüft Versionen, Bash, Schlüsselerzeugung und `sshd -t`, einschließlich
eines expliziten Cygwin-PATH bei reduziertem Ausgangs-PATH. Vor einem neuen
Kandidaten einen neuen Testschlüssel verwenden. Wine ist eine ergänzende Prüfung;
Dienstbetrieb, Benutzerwechsel, NTFS, Neustart und echte Anmeldungen auf Windows
gesondert abnehmen. Releases bleiben bis dahin Prereleases.

## Eingaben aktualisieren

```sh
python3 scripts/inputs.py refresh-lock
```

Der Aufruf prüft den offiziellen festgehaltenen Cygwin-Signaturschlüssel und
aktualisiert den ausgewählten Paketbestand. Er wählt nicht automatisch eine
neue OpenSSH-Version: Versionsangaben und Quellpaketauswahl sind derzeit in den
Build-/Paket-/Prüfskripten festgelegt. Bei einem Versionswechsel Lockdatei,
Quellpfade, Skripte, Tests, Image-Tags und Dokumentation gemeinsam anpassen.
Nach Änderungen vollständig neu bauen und prüfen. Quellenarchive der tatsächlich
ausgelieferten Komponenten zusammen mit ZIP und SHA256SUMS bereitstellen.
