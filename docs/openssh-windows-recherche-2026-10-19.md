# OpenSSH unter Linux für Windows bauen

Historischer Stand vor der Umsetzung. Der erfolgreiche Cross-Build ist im
[Buildbericht](build-validation.md) beschrieben; Einstieg und Buildbefehle stehen in der [README](../README.md).

Stand: 19. Oktober 2026. Vorgaben: Linux als Buildsystem, kein Microsoft-SDK, modernes Windows; Cygwin darf als Laufzeit mitgeliefert werden. Architektur zunächst Windows x86_64; ARM64 wurde nicht untersucht.

**Empfehlung: aktuelles OpenSSH Portable für das Cygwin-Ziel crosskompilieren und mit einer passenden Cygwin-Laufzeit ausliefern.** Dafür gibt es eine konkrete Linux-Toolchain als Ausgangspunkt. Ein erfolgreicher Build und Funktionstest von OpenSSH mit dieser Toolchain wurde in dieser Recherche noch nicht durchgeführt. Die Kombination ist technisch plausibel und durch die getrennt vorhandenen Bausteine gestützt, aber noch kein verifiziertes Buildrezept.

## Welche Möglichkeiten passen?

| Weg | Linux ohne Microsoft-SDK | Ergebnis | Bewertung |
| --- | --- | --- | --- |
| OpenSSH Portable für Cygwin | Eine passende Cross-Toolchain existiert; OpenSSH-Build noch zu erproben | Windows-Programme mit Cygwin-DLL und weiteren Abhängigkeiten | Beste Grundlage für deine Vorgaben |
| PowerShell/Win32-OpenSSH unverändert bauen | Dokumentierter Build benötigt Visual Studio und Windows-SDK | Native Windows-Portierung | Passt zum geforderten Buildsystem nicht |
| Win32-OpenSSH auf MinGW-w64 oder LLVM-MinGW portieren | Als eigenes Entwicklungsprojekt denkbar | Native Windows-Portierung ohne Cygwin | Deutlich größerer Aufwand; kein fertiger aktueller Buildweg gefunden |
| SSH-Server auf Basis einer anderen Implementierung | Je nach Bibliothek möglich | SSH-kompatibler eigener Server | Nur interessant, wenn OpenSSH selbst keine feste Anforderung ist |

OpenSSH Portable nennt Cygwin ausdrücklich als unterstützte Plattform. Das ist die entscheidende Grundlage: Die Windows-Anpassung der POSIX-Funktionen übernimmt bereits Cygwin. Ein bloßer Wechsel des Compilers auf MinGW ersetzt diese Laufzeitfunktionen nicht. [OpenSSH-Repository](https://github.com/openssh/openssh-portable)

## Wie aktuell sind die Varianten?

Upstream ist bei **OpenSSH 10.6p1 vom 6. Oktober 2026**. [Offizielle Release Notes](https://www.openssh.org/releasenotes.html)

Das Cygwin-Paket führt **10.5p1-1 als stable** und **10.6p1-1 als test**. Damit gibt es eine aktuelle Windows-Portierung außerhalb der optionalen Windows-Komponente. Für einen Buildversuch würde ich 10.6p1 untersuchen und dessen Teststatus im Cygwin-Paket berücksichtigen. [Cygwin-Paketübersicht](https://cygwin.com/packages/summary/openssh.html)

Bei PowerShell/Win32-OpenSSH ist das jüngste veröffentlichte Paket **10.0.0.0p2-Preview vom 27. Oktober 2025**. Der Release-Text bezeichnet es ausdrücklich als noch nicht produktionsreif. Dein Eindruck eines Release-Rückstands ist daher nachvollziehbar. Das Projekt pauschal als aufgegeben einzuordnen wäre allerdings nicht belegt: Das Quellrepository zeigte bei der Abfrage einen Push vom 12. Oktober 2026. Der Name „PowerShell“ bezeichnet hier die GitHub-Organisation; der Server ist eine Windows-Portierung von OpenSSH. [Release](https://github.com/PowerShell/Win32-OpenSSH/releases/tag/10.0.0.0p2-Preview), [Quellrepository](https://github.com/PowerShell/openssh-portable), [Repository-Metadaten](https://api.github.com/repos/PowerShell/openssh-portable)

Der dokumentierte Win32-Build benötigt MSVC v143 und das Windows-SDK. Auch die untersuchten Projektdateien für `sshd` und `sshd-session` verwenden diese Toolchain. Die alte MinGW-Anleitung stammt von 2015; sie belegt keinen funktionierenden Build aktueller Quellen. [Aktuelle Buildanleitung](https://github.com/PowerShell/Win32-OpenSSH/wiki/Building-OpenSSH-for-Windows-%28using-LibreSSL-crypto%29), [sshd-Projektdatei](https://github.com/PowerShell/openssh-portable/blob/latestw_all/contrib/win32/openssh/sshd.vcxproj), [Historische MinGW-Anleitung](https://github.com/PowerShell/Win32-OpenSSH/wiki/OpenSSH-32-bit-Build-and-Installation-Instructions)

## Konkreter Ansatz mit Cygwin

Als Ausgangspunkt eignet sich **[palves/cygwin-cross](https://github.com/palves/cygwin-cross)**. Das Projekt stellt eine Linux-Containerumgebung mit einer Cygwin-Cross-Toolchain bereit. Der Compiler heißt `x86_64-pc-cygwin-gcc`. Die Umgebung verwendet Fedora-Copr-Pakete aus `yselkowitz/cygwin` und wurde ursprünglich für GDB zusammengestellt. Für OpenSSH müssen deshalb weitere Zielbibliotheken ergänzt werden. Das Projekt ist ein Ausgangspunkt, kein fertiges OpenSSH-Buildsystem; sein letzter ermittelter Push stammt vom November 2024.

Die sinnvolle Buildkette wäre:

1. Linux-Buildumgebung mit Cygwin-Cross-Compiler und passendem Sysroot festlegen. Hier auf dem Host wäre dafür rootless Podman zu verwenden; das vorhandene Projekt ist auf Docker ausgerichtet und müsste entsprechend angepasst werden.
2. Cygwin-Header, Importbibliotheken und Laufzeit auf einen zueinander passenden Versionsstand bringen. Eine alte Containerumgebung ungeprüft mit aktuellen Paketen zu mischen wäre keine belastbare Grundlage.
3. Die benötigten Bibliotheken ebenfalls für **Cygwin** bereitstellen, zunächst insbesondere OpenSSL/libcrypto und die vom gewählten Build benötigten weiteren Bibliotheken. MinGW-Bibliotheken haben ein anderes Laufzeitmodell und sind kein Ersatz.
4. Aktuelles OpenSSH mit dem Hostziel `x86_64-pc-cygwin` konfigurieren und bauen. Die genauen Optionen und eventuelle Cross-Compile-Anpassungen müssen am konkreten Quellstand ermittelt werden.
5. Alle erzeugten Server-Hilfsprogramme und deren DLL-Abhängigkeiten paketieren. Bei aktuellen Versionen reicht es nicht, allein `sshd.exe` zu übernehmen.
6. Dienstinstallation, Hostschlüssel, Benutzerzuordnung und Dateirechte auf einem sauberen Windows-Testsystem prüfen.

Das offizielle Cygwin-Paket enthält neben OpenSSH unter anderem Abhängigkeiten auf `cygwin`, `cygrunsrv`, `bash`, `csih`, `libssl3`, `zlib0` und weitere Bibliotheken. Diese vollständige Paketliste umfasst auch Clients und Installationshilfen. Welche Dateien ein eigenes Serverpaket tatsächlich braucht, muss anhand des Builds und der vorgesehenen Funktionen bestimmt werden. [Paketabhängigkeiten](https://cygwin.com/packages/summary/openssh.html)

`cygwin1.dll` bleibt zur Laufzeit erforderlich. Eine vollständig eigenständige EXE durch statisches Einlinken dieser Laufzeit ist laut Cygwin-FAQ nicht möglich. Für deine inzwischen bestätigte Vorgabe ist das kein Hindernis. Ein abgegrenztes Installationsverzeichnis mit den benötigten Dateien ist das passende Paketierungsziel. [Cygwin-FAQ](https://cygwin.com/faq/faq.html#faq.programming.static-linking)

## Was auf Windows zu prüfen ist

Cygwin bildet Windows-Konten und Dateirechte auf das POSIX-Modell ab. Benutzerwechsel sind vorgesehen, benötigen aber einen geeigneten Dienstkontext. Eine SSH-Schlüsselanmeldung erzeugt außerdem nicht automatisch dieselben Netzwerk-Anmeldedaten wie eine Passwortanmeldung. Zugriff auf SMB-Freigaben sollte deshalb separat getestet werden, falls die Projektidee ihn benötigt. [Cygwin: Konten, Rechte und Benutzerwechsel](https://cygwin.com/cygwin-ug-net/ntsec.html)

Ein aussagekräftiger Machbarkeitsnachweis sollte mindestens zeigen:

- Start des Servers und seiner Hilfsprogramme auf Windows ohne installierte Entwicklerwerkzeuge.
- Schlüsselanmeldung, korrekte Windows-Benutzeridentität und erwartete Dateirechte.
- Befehlsausführung, Exitcodes und SFTP.
- Interaktive Sitzung samt Terminalverhalten, falls benötigt; native Windows-Programme dabei eigens prüfen.
- Dienststart nach einem Neustart und vollständige Abhängigkeiten des ausgelieferten Pakets.

Ein erfolgreicher Linux-Build oder ein Start unter Wine allein würde diese Punkte nicht nachweisen.

## Einordnung für die Projektidee

Mit akzeptierter Cygwin-Laufzeit würde ich **keine neue native OpenSSH-Portierung beginnen**. Der nächste sinnvolle Schritt ist ein begrenzter Buildversuch mit der vorhandenen Cross-Toolchain, aktuellem OpenSSH und einem sauberen Windows-Testsystem. Das größte offene technische Risiko liegt zunächst bei der Aktualität und Zusammenstellung von Toolchain und Sysroot; anschließend bei Dienstrechten und den tatsächlich benötigten Sitzungsfunktionen.

Falls später nur ein eingebetteter SSH-Endpunkt für einzelne Befehle oder Dateitransfer gebraucht wird, wäre auch ein eigener Server mit Go `golang.org/x/crypto/ssh` und gegebenenfalls `pkg/sftp` zu prüfen. Diese Bibliotheken stellen SSH beziehungsweise SFTP bereit; Windows-Anmeldung, Benutzerwechsel und Prozess-/Terminalintegration wären zusätzlich umzusetzen. Das wäre eine andere Architektur und kein OpenSSH-Build. [Go-SSH-Dokumentation](https://pkg.go.dev/golang.org/x/crypto/ssh), [SFTP-Projekt](https://github.com/pkg/sftp)

Diese Datei dokumentiert eine Quellenrecherche und eine daraus abgeleitete Empfehlung. Es wurden keine Toolchains installiert, keine Container gestartet und keine Windows-Binaries gebaut.
