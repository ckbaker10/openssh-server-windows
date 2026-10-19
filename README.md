# OpenSSH Server für Windows

Ein eigenständig verteilbares **OpenSSH 10.6p1 für Windows x86_64**, mit
Cygwin-Laufzeit, Bash, SCP und SFTP. Es ermöglicht Fernzugriff und Dateitransfers
per SSH-Schlüssel, auch mit eingeschränkten Windows-Konten.

Das Projekt stellt ein unter Linux baubares Paket bereit, das unabhängig vom
optionalen Windows-OpenSSH-Feature installiert und aktualisiert werden kann.
Ein Microsoft-SDK wird nicht benötigt. Der Dienst läuft als LocalSystem;
angemeldete Benutzer erhalten die Rechte ihres jeweiligen Windows-Kontos.
Passwortanmeldung ist standardmäßig abgeschaltet. Releases sind derzeit Prereleases.

## Installation als Administrator

Das Windows-ZIP und `SHA256SUMS` von den [Releases](https://github.com/ckbaker10/openssh-server-windows/releases)
laden, den ZIP-Hash vergleichen und nach `C:\Program Files\OpenSSH-Cygwin`
entpacken. `install-server.cmd` muss direkt in diesem Ordner liegen.
Eine **64-Bit-PowerShell als Administrator** öffnen:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
powershell.exe -NoProfile -File .\verify-package.ps1
.\install-server.cmd --yes --name openssh-cygwin --port 2222
.\open-shell.cmd
```

In der geöffneten Bash den eigenen **öffentlichen** Schlüssel eintragen:

```bash
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME" "$HOME/.ssh"
cat >> "$HOME/.ssh/authorized_keys" <<'KEY'
ssh-ed25519 AAAA...hier_den_eigenen_oeffentlichen_Schluessel_einsetzen
KEY
chmod 600 "$HOME/.ssh/authorized_keys"
exit
```

Zurück in PowerShell Konfiguration prüfen und Dienst starten:

```powershell
.\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
Start-Service openssh-cygwin
```

Den gewählten TCP-Port gezielt in der Firewall freigeben. Anmeldung vom Client:
`ssh -p 2222 Administrator@server.example`.
Details zu Schlüsseln, SYSTEM-Konfiguration, Logs und Updates:
[Installationsanleitung](docs/windows-installation.md).

## Einrichtung eines unprivilegierten Benutzers

Ein vorhandenes, aktiviertes **lokales Windows-Konto ohne Administratorrechte**
und dessen öffentliche Schlüsseldatei verwenden. Die einmalige Einrichtung
führt ein Administrator aus; die spätere SSH-Sitzung bleibt eingeschränkt:

```powershell
.\install-user.cmd sshuser 'C:\Keys\sshuser.pub' -Start
```

Der Helfer prüft Konto und SID, erstellt ein neues `/home/sshuser`, setzt
Besitzer und Modi und ergänzt eine vorhandene globale `AllowUsers`-Liste.
Bestehende Homes werden nicht überschrieben. `-Start` startet den Dienst nach
Erfolg auch dann, wenn er vorher gestoppt war.
Anmeldung: `ssh -p 2222 sshuser@server.example`.
Siehe [Benutzer einrichten und entfernen](docs/nonadmin-users.md).

## Selbst bauen

Die [COMPILE.md](COMPILE.md) beschreibt den Linux-Cross-Build mit rootless
Podman, Eingaben, Prüfungen und erzeugte Archive.
Bekannte Cygwin-Grenzen und Diagnose: [Fehlerhilfe](docs/troubleshooting.md).
