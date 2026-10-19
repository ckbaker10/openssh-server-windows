# Build und Prüfungen vom 19. Oktober 2026

OpenSSH 10.6p1 wurde unter Linux mit rootless Podman für Windows x86_64 gebaut.
Das ZIP enthält Cygwin 3.6.11, Bash, OpenSSL und die benötigten Hilfsprogramme.
Der vollständige Buildbefehl `bash scripts/build.sh` lief erfolgreich durch.
Der letzte vollständige Lauf benötigte 60 Sekunden, gemessen mit `date +%s` auf dem Host.

| Bestandteil | Verwendeter Stand |
| --- | --- |
| OpenSSH | 10.6p1 aus dem signierten Cygwin-Quellpaket 10.6p1-1 |
| Cygwin und Entwicklungsdateien | 3.6.11-1 |
| OpenSSL | 3.5.9-1 aus dem Cygwin-Paketbestand |
| Cross-Compiler | GCC 13.4.0, Fedora Cygwin 13.4.0-1 |
| Binutils | 2.45.1 |
| Podman | 4.9.3, rootless |

Das Fedora-Basisimage ist über seinen SHA-256-Digest festgelegt, Compiler und
Binutils über ihre Paketversionen. Der Compiler verwendet die aktuellen
Cygwin-Entwicklungsdateien aus dem festgehaltenen Paketbestand statt der alten
Cygwin-Laufzeit des ursprünglichen Copr-Sysroots. Es wird kein Microsoft-SDK verwendet.

Die einzige Quellcodeanpassung ist
[`cygwin-cross-textreadmode.patch`](../patches/cygwin-cross-textreadmode.patch).
Sie macht den sonst fest auf `/usr/lib/textreadmode.o` gesetzten Pfad für den
Cross-Build über `CYGWIN_SYSROOT` einstellbar. Ein nativer Build ohne diese
Variable behält den ursprünglichen Pfad. Authentifizierung und Kryptografie
werden durch diesen Patch nicht verändert.

## Eingaben und Artefakte

Der Paketindex wurde mit dem offiziellen Cygwin-Schlüssel
`56405CF6FCC81574682A5D561A698DE9E2E56300` geprüft. Alle 85 Archive wurden auf Größe
und SHA-512 geprüft; ihre SHA-256-Werte stehen zusätzlich im Buildmanifest.
Die Referenz für den Schlüssel ist die [offizielle Cygwin-Installationsseite](https://cygwin.com/install.html).

| Eingabe oder Ergebnis | SHA-256 |
| --- | --- |
| OpenSSH-Quellpaket `openssh-10.6p1-1-src.tar.xz` | `9866c2ccdfd01593ce04c6dbac6a7a3f4e5a909d126a17d916d4accf9917fc1e` |
| Cygwin-Quellpaket `cygwin-3.6.11-1-src.tar.xz` | `21732da41e1a4eee6ec44d64edc6645ffa3df66dec671889bc9a2b8cdfa6613f` |
| Windows-ZIP | `3caa6aeeda2d5c674d7d4c29f0ec3d7716720fc5f6424ddf31bb4fa7b4a076a0` |
| Quellenarchiv | `8deede693842f2c39b6493d7ddb53d9fb343744fcc0d73e31b9cd85f55b64773` |

Die Dateien liegen lokal unter `dist/`:

- `openssh-10.6p1-cygwin-x86_64.zip`: 52.575.356 Bytes.
- `openssh-10.6p1-cygwin-x86_64-sources.tar`: 244.285.440 Bytes.
- `SHA256SUMS`: maschinenlesbare Prüfsummen.

Das Quellenarchiv enthält die passenden Cygwin-Quellpakete, das originale
OpenSSH-Quellpaket, den signierten Index, dessen öffentlichen Schlüssel und den
Cross-Build-Patch. Die jeweiligen Lizenztexte sind in den Quellen beziehungsweise
den mitgelieferten Paketdokumentationen enthalten.

## Erfolgreiche Prüfungen

- Der vollständige Build samt Paketierung hat Exitstatus 0.
- Die Prüfung des tatsächlich entpackten ZIPs hat Exitstatus 0: CRC, Archivhashes,
  Dateihashes und 282 PE-Dateien mit x86_64-Architektur wurden geprüft.
- Alle statisch importierten DLLs sind im Suchpfad des Pakets enthalten oder
  explizit als Windows-Systembibliotheken eingeordnet.
- `sshd.exe`, `sshd-session.exe`, `sshd-auth.exe`, `sftp-server.exe`,
  `ssh-keygen.exe`, Bash und `cygrunsrv.exe` sind enthalten.
- Die ZIP-Paketierung benötigt keine POSIX-Symlinks auf Windows; benötigte
  Aliasdateien und die Terminfo-Daten sind als reguläre Dateien enthalten.
- Es sind keine privaten SSH-Hostschlüssel im Paket enthalten. Die Vorgabe für
  Schlüsselanmeldung und internes SFTP wurde geprüft.
- ShellCheck mit `-S warning` und Hadolint bestehen für die eigenen Skripte und Containerfiles.

Compilerwarnungen betreffen überwiegend die von Upstream verwendeten, in
OpenSSL 3 als veraltet markierten APIs; hinzu kommen Format- und Vorzeichenwarnungen.
Die für einen Cross-Build nicht ausführbaren Configure-Laufzeittests werden im
Buildlog als solche ausgewiesen. Ein erfolgreicher Build ersetzt diese Laufzeittests nicht.

## Laufzeittests und Nachweise

Der ergänzende Test mit Wine 11.0 Staging in Podman besteht
(`work/evidence/wine-smoke-09/`, Exitstatus 0). Client und Server melden
`OpenSSH_10.6p1, OpenSSL 3.5.9 29 Sep 2026`. Die Bash findet die paketierten
Serverdateien. Die Ed25519-Schlüsselgenerierung gelang im vorherigen Testlauf;
`sshd -t` akzeptiert die mitgelieferte Konfiguration mit diesem Testschlüssel.
Die Berechtigungen des ausschließlich lokal erzeugten Testschlüssels werden
im Linux-Testverzeichnis auf 0600 gesetzt.

Das Wine-Testimage enthält LDAP-Unterstützung und ein virtuelles Display. Es
verwendet die Wine-System-DLLs direkt aus der Fedora-Installation; ein vorheriger
Versuch mit `wineboot --update` blieb in dieser Umgebung hängen. Cygwin meldet
unter Wine eine `FAST_CWD`-Kompatibilitätswarnung. Diese ergänzenden Tests sind
keine Abnahme des Windows-Dienstbetriebs.
Dienstinstallation, Windows-Benutzerwechsel, SSH-Anmeldung, interaktive Sitzung,
SFTP und Neustartverhalten sind auf echtem Windows noch zu prüfen. Die
[Installationsanleitung](windows-installation.md) enthält die dafür vorgesehenen Schritte.

Die vollständigen lokalen Rohdaten liegen ausschließlich im ignorierten
`work/evidence/`. Je Lauf enthält `metadata.json` den exakten Befehl,
Eingabe-SHA-256, Werkzeugversionen, Hostzeitstempel und Exitstatus; daneben
liegen `stdout.log` und `stderr.log`.

| Nachweis | Befehl |
| --- | --- |
| `work/evidence/cross-build-04/` | `bash scripts/build.sh` |
| `work/evidence/zip-check-04/` | `podman run --rm --name openssh-server-windows-zip-check -v /opt/paseo-development/openssh-server-windows:/project:Z localhost/openssh-server-windows-builder:10.6p1 python3 scripts/check-package.py` |
| `work/evidence/wine-smoke-09/` | `podman run --rm --name openssh-server-windows-wine-smoke -v /opt/paseo-development/openssh-server-windows:/project:Z localhost/openssh-server-windows-wine:10.6p1 bash scripts/smoke-wine.sh` |

Zum Wiederholen der Prüfungen und des optionalen Wine-Tests siehe [README](../README.md).
