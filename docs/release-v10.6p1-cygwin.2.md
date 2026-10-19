# Paketrevision 2 ohne Handbuchseiten

Die erste Windows-ZIP-Datei enthielt `usr/share/man/man1/:.1.gz`. Der Doppelpunkt
verhindert das Entpacken dieser Datei mit üblichen Windows-Werkzeugen. Gemäß
Nutzeranforderung enthält das Windows-Paket ab `v10.6p1-cygwin.2` keine Man- oder
Info-Handbuchseiten mehr. Lizenzhinweise und Installationsanleitung sind enthalten;
die separaten Original-Quellpakete bleiben vollständig.

Vor der Manifest-Erzeugung werden `usr/share/man`, `usr/share/info`, `share/man`
und `share/info` entfernt. Gegenüber Paketrevision 1 entfallen 271 Man-Dateien
und 17 Info-Dateien. Zusätzlich wird ein inhaltsgleicher Alias
`usr/share/doc/grep/readme` neben `README` entfernt, da Windows diese beiden Namen
nicht zuverlässig als unterschiedliche Dateien behandelt. Unterschiedliche Inhalte
bei einer Namenskollision führen zu einem Fehler statt zu einem Überschreiben.

Alle Archivpfade werden auf ungültige Windows-Zeichen, reservierte Gerätenamen,
abschließende Punkte/Leerzeichen und Namenskollisionen geprüft. Der ZIP-Test
vergleicht die komplette Dateiliste mit dem Manifest und prüft alle Dateihashes.
`inputs.lock.json` wird nun vor der Hash-Erfassung kopiert und ist ebenfalls im
Manifest enthalten. Nur `build-manifest.json` selbst hat keinen eigenen Hash.

## Ergebnisse

- 1.954 Dateien im ZIP: 1.953 erfasste Nutzdateien und das Manifest selbst.
- Keine Man-/Info-Dateien; alle Archivnamen bestehen die Windows-Pfadprüfung.
- Archiv-CRC, Artefakt-Prüfsummen, sämtliche Dateihashes und vollständige
  Manifest-Dateiliste geprüft.
- Alle 282 PE-Programme und DLLs sind bytegleich mit Paketrevision 1; Architektur
  und DLL-Imports wurden erneut geprüft. Die vorhandenen erfolgreichen
  Cross-Build-Nachweise gelten für diese unveränderten Binärdateien weiter.
- Fünf Regressionstests bestehen, darunter der konkrete Doppelpunktname,
  reservierte Namen sowie sichere Behandlung von README-Namenskollisionen.
- Wine-Test mit neu erzeugtem Ed25519-Testschlüssel besteht: Client-/Serverstart,
  Bash-Zugriff auf die Paketdateien und `sshd -t`.

Die native Windows-Abnahme von Dienstbetrieb und Anmeldung steht weiterhin aus;
Paketrevision 2 wird als Prerelease veröffentlicht.

| Artefakt | Größe | SHA-256 |
| --- | --- | --- |
| `openssh-10.6p1-cygwin-x86_64.zip` | 50.540.980 Bytes | `53da2697f4a5cf015610f2964642a7849bb223ea4309c9f23785442e572954ac` |
| `openssh-10.6p1-cygwin-x86_64-sources.tar` | 244.285.440 Bytes | `8deede693842f2c39b6493d7ddb53d9fb343744fcc0d73e31b9cd85f55b64773` |

## Reproduzierbare Nachweise

Die Rohdaten liegen ausschließlich im ignorierten `work/evidence/`. Jeweils
`metadata.json` mit Eingabe-SHA-256, exaktem Befehl, Werkzeugversionen,
Hostzeitstempeln und Exitstatus sowie `stdout.log`/`stderr.log`:

| Lauf | Ergebnis |
| --- | --- |
| `no-manuals-regression-01` | Neue Prüfung weist das alte ZIP zurück. |
| `package-no-manuals-02` | Neue Paketierung erfolgreich mit Python 3.14.8 und Binutils 2.45.1 in Podman. |
| `zip-no-manuals-01` | Vollständiger ZIP-, Pfad-, Manifest- und PE-Test erfolgreich. |
| `wine-no-manuals-01` | Wine 11.0 Staging: ergänzender Laufzeittest erfolgreich. |

Befehle aus dem Repository:

```sh
podman run --rm --name openssh-server-windows-package \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-builder:10.6p1 \
  python3 scripts/package.py
podman run --rm --name openssh-server-windows-zip-check \
  -v "$PWD:/project:Z" localhost/openssh-server-windows-builder:10.6p1 \
  python3 scripts/check-package.py
python3 -m unittest discover -s tests -v
```

Die Paketierung verwendet die vorhandenen geprüften Builddaten unter `work/`.
Für einen vollständigen Build von Anfang an gilt weiterhin `bash scripts/build.sh`.
