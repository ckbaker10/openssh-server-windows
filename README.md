# OpenSSH Server für Windows

OpenSSH **10.6p1** für Windows x86_64, unter Linux mit **rootless Podman** crosskompiliert.
Das Windows-Paket enthält **Cygwin 3.6.11** und die benötigte Laufzeit. Ein Microsoft-SDK
oder das optionale Windows-OpenSSH-Feature wird nicht benötigt.

## Bauen

Voraussetzungen auf Linux: Python ab 3.11, Git, Netzwerkzugriff und funktionierendes
rootless Podman. Der erste Build lädt die Toolchain und die festgehaltenen Quell- und
Laufzeitpakete. Geschützte Hostverzeichnisse werden nicht in den Container eingebunden.

```sh
bash scripts/build.sh
```

Ergebnisse:

- `dist/openssh-10.6p1-cygwin-x86_64.zip`: Windows-Paket mit Server, Hilfsprogrammen und Laufzeit.
- `dist/openssh-10.6p1-cygwin-x86_64-sources.tar`: zugehörige Quellen, signierter Paketindex und Cross-Build-Patch.
- `dist/SHA256SUMS`: Prüfsummen der beiden Archive.

Das ZIP enthält eine `SHA256SUMS` mit Nutzdateihashes und `verify-package.ps1`
zur Prüfung ohne JSON (Syntax für Windows PowerShell 5.1). Zusätzlich enthält es
`build-manifest.json` mit Dateihashes, DLL-Imports,
Compiler- und RPM-Versionen sowie `inputs.lock.json` mit den festgehaltenen Eingaben.
`work/` enthält die erzeugten Builddaten und wird wie `dist/` nicht eingecheckt.
Das Windows-ZIP enthält keine Man- oder Info-Handbuchseiten. Alle Archivnamen
werden auf Windows-Kompatibilität geprüft; das Manifest erfasst jede ausgelieferte
Datei außer sich selbst. Lizenzhinweise und Installationsanleitung sind enthalten.

## Prüfen und installieren

```sh
podman run --rm --name openssh-server-windows-check \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-builder:10.6p1 \
  python3 scripts/check-package.py
shellcheck -S warning scripts/*.sh packaging/*.sh
hadolint build/Containerfile build/Containerfile.wine
python3 -m unittest discover -s tests -v
```

Der Cross-Build und die Prüfung des entpackten ZIPs sind erfolgreich. Die
[Windows-Installationsanleitung](docs/windows-installation.md) beschreibt die
Dienstinstallation und die noch erforderliche Abnahme auf echtem Windows.
Die Standardkonfiguration erlaubt Schlüsselanmeldung und internes SFTP; Passwortanmeldung ist deaktiviert.

Der Build verwendet OpenSSL und zlib aus dem signierten Cygwin-Paketbestand.
Kerberos, PAM, libedit und der integrierte Zugriff auf FIDO-Geräte sind in dieser
Buildkonfiguration nicht aktiviert. Normale Schlüsselanmeldung, Shell, Befehlsausführung
und SFTP sind die vorgesehenen Funktionen.

## Eingaben und ergänzende Laufzeittests

`build/inputs.lock.json` hält die Paketversionen, Größen und SHA-512-Prüfsummen fest.
Die Downloads werden vor dem Entpacken geprüft. Eine bewusste Aktualisierung des
Locks benötigt zusätzlich GnuPG und prüft den offiziellen Cygwin-Signaturschlüssel:

```sh
python3 scripts/inputs.py refresh-lock
```

Compiler, Binutils und das Fedora-Basisimage sind festgelegt. Die übrigen beim
Imagebau aufgelösten RPM-Versionen stehen im Buildmanifest; der Build garantiert
keine bitidentischen Ergebnisse über unterschiedliche Toolchain-Images hinweg.

Ein optionaler Wine-Test läuft ebenfalls ausschließlich in Podman:

```sh
podman build -f build/Containerfile.wine -t localhost/openssh-server-windows-wine:10.6p1 .
podman run --rm --name openssh-server-windows-wine-smoke \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-wine:10.6p1 \
  bash scripts/smoke-wine.sh
```

Der Wine-Test setzt die vorherige ZIP-Prüfung voraus und ersetzt keine Windows-Abnahme.
Details und Nachweise stehen im [Buildbericht](docs/build-validation.md).
Die [Korrektur der Windows-Paketierung in Paketrevision 2](docs/release-v10.6p1-cygwin.2.md)
entfernt Handbuchseiten und prüft die vollständige Dateiliste gegen das Manifest.
Die ursprüngliche [Machbarkeitsrecherche](docs/openssh-windows-recherche-2026-10-19.md)
beschreibt die Auswahl von OpenSSH mit Cygwin.

Die [native Windows-Teilabnahme von Revision 1](docs/windows-validation-2026-10-19.md)
bestätigt Anmeldung, Admin-Token, Exitcodes, TTY und Dateitransfers. Revision 3
ergänzt sichere Konfigurationsübernahme, LocalSystem-Validierung, konsistente
Homes, Dateilogs und Prüfsummen.
Details: [Prüfbericht der Paketrevision 3](docs/release-v10.6p1-cygwin.3.md).

Die [native Teilabnahme von Revision 3](docs/windows-validation-revision3-2026-10-19.md)
bestätigt Entpacken, PowerShell-5.1-Prüfung mit `-Path`, Konfigurationserhalt,
Home-Auflösung, Dateilogs und Dateitransfers mit unveränderten Hostschlüsseln.
Die Aktualisierung gelang mit Workarounds. Revision 4 korrigiert den fatalen
SYSTEM-ACL-Aufruf, die Prüfer-Pfadermittlung und unnötige Besitzerwechsel;
die Anleitung verwendet Robocopy `/B`. Neue Korrekturen, Neustart und Rückkehr
brauchen noch eine Windows-Abnahme; weiterhin Prerelease.
Details: [Prüfbericht der Paketrevision 4](docs/release-v10.6p1-cygwin.4.md).

## Wöchentliche Pflege und Releases

Die vorhandenen Prompt-Patrol-Wochen-Worker übernehmen die Updateprüfung über den
offenen Dauerplan unter
`ai-repo-plans/openssh-server-windows/002-dauerplan-wochenpflege-github-releases.md`
im lokalen Workspace. Der Plan umfasst OpenSSH, Cygwin, OpenSSL und die
ausgelieferten Laufzeitpakete sowie Build, Tests und die eigenständige
Veröffentlichung neuer GitHub-Releases. Ein neuer Zeitgeber wird dafür nicht angelegt.

[Repository-Anweisungen](AGENTS.md) halten die dauerhafte Veröffentlichungsfreigabe
und den Einstieg für neue Worker-Sitzungen fest. Ohne native Windows-Abnahme
werden geprüfte Updates weiterhin als Prerelease veröffentlicht.
