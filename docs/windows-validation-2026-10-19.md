# Native Windows-Teilabnahme vom 19.10.2026

Quelle: Nutzerrückmeldung WINSSH-004, Windows Server Build 26100, nicht produktiv,
LocalSystem, Port 2222. Die vom Nutzer referenzierten externen Befunddateien
wurden hier nicht eingesehen. Getestet wurde ausschließlich **v10.6p1-cygwin.1**:

- ZIP: `openssh-10.6p1-cygwin-x86_64.zip`, 52.575.356 Byte.
- SHA-256: `3caa6aeeda2d5c674d7d4c29f0ec3d7716720fc5f6424ddf31bb4fa7b4a076a0`.
- 2241 Manifest-Dateien: 2239 identisch, keine Hashabweichung. Zwei Dateien konnten
  wegen Doppelpunkt bzw. Groß-/Kleinschreibungskollision nicht angelegt werden.

| Prüfung | Ergebnis laut Rückmeldung |
| --- | --- |
| Schlüsselanmeldung Administrator | erfolgreich; whoami korrekt, voller Admin-Token |
| Exitcodes | 7 und 3 korrekt weitergereicht |
| Passwortanmeldung | abgewiesen |
| TTY | ssh -tt erfolgreich |
| SCP-Upload / SFTP-Download | 30 MB mit identischer SHA-256 |
| PowerShell | EncodedCommand erfolgreich |
| Hostschlüssel | inklusive mldsa44-ed25519; SYSTEM, Modus 600 |

Gemeldete Probleme: `--yes` löscht Konfigurationen bei fehlenden Defaultvorlagen;
Kontoargumente sind wirkungslos; `/tmp` fehlt und Besitzwechsel warnen;
geerbtes HOME und Kontodatenbank widersprechen sich; Windows-Dateibesitzer
verhindern StrictModes; ZIP-Namen und JSON-Schlüssel sind problematisch;
Dateilogs und Hinweise zu LF, PowerShell-Aufruf und NTFS-ACLs fehlen.

Revision 2 entfernte Handbuchseiten und die kollidierende Dokumentationsdatei
und prüft Windows-Pfade. Revision 3 ergänzt Vorlagen, Konfigurationserhalt und
Sicherung, explizite Portänderung einschließlich 22, LocalSystem-Validierung,
ZIP-Verzeichnisse, NSS-/Shell-Homeauflösung, Dateilogs, SHA256SUMS samt Prüfer und
die Anleitung. Diese Änderungen haben **noch keine native Windows-Abnahme**.
Automatisierte Prüfungen stehen getrennt im Bericht der Revision 3.
Der Release bleibt ein Prerelease.

Offen: Windows-Neustart, Aktualisierung/Rückkehr, Netzwerkfreigaben bei
Schlüsselanmeldung, Ansible/ähnliche Werkzeuge und echtes Netzwerk. Die bisherige
Anmeldung erfolgte per Loopback über einen Sprunghost. Das Ergebnis ist keine
vollständige Betriebs- oder Sicherheitsabnahme.
