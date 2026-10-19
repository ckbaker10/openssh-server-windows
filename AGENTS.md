# Anweisungen für dieses Repository

Die Regeln aus `/opt/paseo-development/AGENTS.md` gelten zusätzlich.

## Wiederkehrende Pflege durch Prompt Patrol

Der maßgebliche offene Dauerplan liegt unter
`/opt/paseo-development/ai-repo-plans/openssh-server-windows/002-dauerplan-wochenpflege-github-releases.md`.
Vor einem automatischen Wartungslauf diesen Plan und seine letzten Laufprotokolle lesen.
Der Plan bleibt dauerhaft offen und wird nach einem Wochenlauf nicht nach `X_` umbenannt.

Der Nutzer hat am 19.10.2026 ausdrücklich die eigenständige wöchentliche Pflege
und Veröffentlichung neuer GitHub-Releases für `ckbaker10/openssh-server-windows`
autorisiert. Geeignete OpenSSH-, Cygwin-, OpenSSL- und Laufzeitupdates nach den
Prüfungen des Plans integrieren, committen, pushen und veröffentlichen; für diese
Routineaktionen keine erneute Nutzerbestätigung verlangen. Parallele Worker
über Lease, gemeinsame Reservierung und Laufprotokolle koordinieren.

Linux-Cross-Builds ausschließlich mit rootless Podman, ohne Microsoft-SDK.
Versionen aus dem geprüften Kandidaten-/Lockstand ableiten; die ursprünglichen
festen Versionsliterale bei Updates zusammenhängend anpassen oder ablösen.
Artefakte und Rohdaten bleiben in den ignorierten Verzeichnissen `dist/` und `work/`.

ZIP-Prüfung, DLL-/Versionsnachweise und ergänzende Laufzeittests vor Veröffentlichung
ausführen. Ohne belegte native Windows-Abnahme weiterhin Prereleases veröffentlichen
und diese Grenze nennen. Keine bestehenden Release-Tags verschieben oder bereits
veröffentlichte Assets ersetzen. Keine Installation auf produktiven Windows-Systemen.
