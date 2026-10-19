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

Das ZIP enthält zusätzlich `build-manifest.json` mit Dateihashes, DLL-Imports,
Compiler- und RPM-Versionen sowie `inputs.lock.json` mit den festgehaltenen Eingaben.
`work/` enthält die erzeugten Builddaten und wird wie `dist/` nicht eingecheckt.

## Prüfen und installieren

```sh
podman run --rm --name openssh-server-windows-check \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-builder:10.6p1 \
  python3 scripts/check-package.py
shellcheck -S warning scripts/*.sh packaging/*.sh
hadolint build/Containerfile build/Containerfile.wine
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
Die ursprüngliche [Machbarkeitsrecherche](docs/openssh-windows-recherche-2026-10-19.md)
beschreibt die Auswahl von OpenSSH mit Cygwin.
