# Installation unter Windows x86_64

OpenSSH 10.6p1 mit Cygwin 3.6.11 und Bash; unter Linux ohne Microsoft-SDK gebaut.
Die optionale Windows-OpenSSH-Komponente ist nicht nötig. Der Dienst wird als
**LocalSystem** installiert. `--user`, `--pwd` und `--privileged` werden mit einem
Fehler abgewiesen; ein Konto `cyg_server` wird nicht angelegt.
Die Windows-Teilabnahmen der Revisionen 1 und 3 belegen Anmeldung, Admin-Token,
Exitcodes, TTY, SCP/SFTP, in Revision 3 auch Home-Auflösung und Dateilogs.
Die Aktualisierung auf Revision 3 gelang mit den dokumentierten Workarounds.
Die neuen Korrekturen in Revision 4 sind noch nicht nativ geprüft.

## 1. Entpacken und prüfen

Die ZIP-SHA-256 mit der Release-Seite bzw. deren `SHA256SUMS` vergleichen:

```powershell
Get-FileHash .\openssh-10.6p1-cygwin-x86_64.zip -Algorithm SHA256
```

Nach `C:\Program Files\OpenSSH-Cygwin` entpacken; `install-server.cmd` und
`bin\cygwin1.dll` müssen direkt darunter liegen. Den äußeren ZIP-Ordner bei Bedarf
umbenennen. Nur Administratoren und SYSTEM dürfen den Installationsbaum verändern.
Das ZIP enthält `/tmp`, `/var/empty`, `/var/log`, `/var/run` und `/home` auch als
leere Verzeichnisse. Man- und Info-Handbuchseiten werden nicht mitgeliefert.

Vor der Installation in PowerShell alle Nutzdateien prüfen:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
powershell.exe -NoProfile -File .\verify-package.ps1 -Path 'C:\Program Files\OpenSSH-Cygwin'
```

Der Prüfer liest die paketinterne `SHA256SUMS`, kein JSON, und scheitert auch an
einer leeren Prüfliste. Revision 3 wurde mit explizitem `-Path` unter Windows
PowerShell 5.1.26100 erfolgreich geprüft (1960 Dateien). Revision 4 löst den
Standardpfad erst nach Parameterbindung auf und nutzt bei leerem `$PSScriptRoot`
`$MyInvocation.MyCommand.Path`. Der neue Rückfall wurde unter PowerShell 7/Linux
getestet; für nicht interaktive Aufrufe weiterhin `-Path` ausdrücklich angeben.
Die Liste erfasst alle Nutzdateien außer sich selbst und `build-manifest.json`.
Das Manifest erfasst zusätzlich die Prüfliste, aber nicht sich selbst.
Die Release-Prüfsumme schützt das ganze ZIP einschließlich beider Metadateien.
Nach der Installation ändern sich Konfigurationen; die Paketprüfung deshalb
immer an einer unveränderten, frisch entpackten Kopie durchführen.

## 2. Dienst einrichten

PowerShell **als Administrator** öffnen, im Installationsverzeichnis:

```powershell
.\install-server.cmd --yes --name openssh-cygwin --port 2222
```

In PowerShell ist `.\` erforderlich. Ohne `--port` bleibt der bestehende Port
erhalten, im neuen Paket ist es 22. Ein ausdrückliches `--port 22` stellt auch
von einem anderen Port auf 22 zurück. Vorhandene Konfigurationen werden unter
`etc\backups\<UTC-Zeit>-<PID>` gesichert. `--yes` erhält `sshd_config`, `ssh_config`
und `nsswitch.conf`; ein ausdrücklich angegebener Port ändert die Serverkonfiguration.
Fehlende Dateien werden aus `etc\defaults\etc` ergänzt.

Einen laufenden Dienst mit diesem Namen vorher gezielt stoppen. Bei schon
registrierten Diensten bleiben Programmpfad und Argumente erhalten; für neue
Logargumente den Abschnitt Aktualisierung beachten.

```powershell
.\bin\bash.exe --noprofile --norc -c '/usr/sbin/sshd -t'
.\bin\cygrunsrv.exe -S openssh-cygwin
.\bin\cygrunsrv.exe -VQ openssh-cygwin
```

Die Firewall gezielt für den gewählten TCP-Port und erlaubte Quellen freigeben.
Die Konfiguration erlaubt Schlüsselanmeldung, deaktiviert Passwörter,
Keyboard-Interactive und X11; SFTP läuft intern. Shell und Befehle verwenden
Cygwin-Bash. Registry-Einstellungen der nativen Win32-OpenSSH-Shell gelten hier nicht.

## 3. Home und öffentliche Schlüssel

Für ein vorhandenes lokales Nicht-Administrator-Konto mit **neuem** Cygwin-Home
gibt es jetzt den separaten administrativen Helfer:
`.\install-user.cmd sshtest 'C:\Keys\sshtest.pub'`.
Er übernimmt SID-/Gruppenprüfung, Besitzer, Modi, eine bestehende globale
AllowUsers-Liste, Syntaxprüfung und Dienstneustart. Details, Grenzen und Aufräumen
stehen in `NONADMIN-USERS.md` im ZIP bzw. `docs/nonadmin-users.md` im Repository.

`etc\nsswitch.conf` setzt `db_home: /home/%U` und `db_shell: /bin/bash`.
Bei Domänenkonten kann `%U` qualifiziert sein. Vorhandene `/etc/passwd`-Einträge
haben Vorrang und müssen separat geprüft werden. `bin\bash.exe` allein kann
ein geerbtes Windows-`HOME` behalten. Deshalb als Zielbenutzer öffnen:

```powershell
.\open-shell.cmd
```

Diese Shell setzt `HOME` aus `getent passwd`, passend zur Cygwin-Kontodatenbank.
In dieser Bash den Pfad prüfen und den **öffentlichen** Schlüssel hinterlegen:

```bash
id
getent passwd "$(id -u)"
printf '%s\n' "$HOME"
mkdir -p "$HOME/.ssh"
chmod go-w "$HOME"
chmod 700 "$HOME/.ssh"
cat > "$HOME/.ssh/authorized_keys" <<'KEY'
ssh-ed25519 AAAA...hier_den_eigenen_oeffentlichen_Schluessel_einsetzen
KEY
chmod 600 "$HOME/.ssh/authorized_keys"
```

Den Beispielschlüssel ersetzen. Nur der Zielbenutzer bzw. SYSTEM darf Home,
`.ssh` und `authorized_keys` verändern. Kann ein eingeschränkter Benutzer sein
Home im geschützten Installationsbaum nicht anlegen, muss ein Administrator
vorher genau dieses Home anlegen und Besitzer/Zugriffsrechte für das Zielkonto
setzen. Die obigen Befehle anschließend als Zielbenutzer ausführen.
`StrictModes` eingeschaltet lassen.

PowerShell-Dateien können `BUILTIN\Administrators` statt dem Benutzer gehören;
Cygwin-`chmod`/`chown` scheitert dann eventuell. Für das **eigene** Home als
Administrator den Besitzer gezielt setzen (Pfad anhand der Abfrage anpassen):

```powershell
$Account = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$UserHome = 'C:\Program Files\OpenSSH-Cygwin\home\Administrator'
icacls.exe $UserHome /setowner $Account /t /c
```

Danach in `open-shell.cmd` die Modi erneut setzen und mit `ls -ld` prüfen.
Bei einem anderen Zielkonto dessen Namen ausdrücklich verwenden. Nicht den
gesamten Installationsbaum rekursiv auf einen normalen Benutzer übertragen.

An Bash übergebene Skripte brauchen **LF**-Zeilenenden. CRLF hängt unter Umständen
`\r` an Argumente oder Dateinamen. Die mitgelieferten `.sh` verwenden LF, `.cmd`
CRLF. Eigene Skripte bei Bedarf mit `sed -i 's/\r$//' datei.sh` konvertieren.

## 4. Protokollierung und Rotation

Neue Dienstregistrierungen starten `sshd` mit `-D -E /var/log/sshd.log`.
Das entspricht `var\log\sshd.log` im Installationsbaum. Der Cygwin-Helfer ordnet
Hostschlüssel, `/var/empty` und Logdatei abschließend SYSTEM zu. Der Wrapper
bereitet nur seine Zustandsverzeichnisse vor und ändert keine Modi am
Installationswurzelordner. Besitzprobleme dieser Pfade werden mit gezieltem
`icacls /setowner` behandelt. SYSTEM-Verzeichnisrechte werden als Gruppeneintrag
`g:18:rwx` gesetzt. Schlägt das fehl, erscheint eine Warnung; die Einrichtung
läuft weiter. Vor dem Start SYSTEM-Zugriff auf `/var/log` und `/var/run` prüfen.
Bereits korrekt dem Dienstkonto gehörende Dateien werden nicht erneut mit
`chown` verändert. Ein abweichender Besitzer wird weiterhin korrigiert; schlägt
das fehl, bleibt die Warnung erhalten. Die neue Warnungsfreiheit braucht einen
Windows-Test. Nach der Installation `sshd -t`,
`ls -ld /var/empty` und `ls -l /etc/ssh_host_*` prüfen.

`Ensuring SSH host keys exist (existing keys are kept)` bezeichnet `ssh-keygen -A`:
es ergänzt nur fehlende Hostschlüssel und ersetzt vorhandene nicht. Revision 3
meldete acht Besitzwarnungen bei bereits SYSTEM gehörenden übernommenen Schlüsseln;
deren Fingerprints blieben laut Windows-Test gleich. Eine Warnung nur dann als
unnötigen Besitzerwechsel einordnen, wenn die tatsächlichen Besitzer stimmen.

Standard-LogLevel ist `INFO`; für mehr Details `LogLevel VERBOSE` über den
Konfigurationsablauf unten setzen und neu starten. Die Dateiprotokollierung umgeht
fehlende Meldungstexte der Windows-Ereignisquelle `sshd`.
Es gibt keine automatische Rotation. Beispiel für manuelle Rotation mit kurzer
Dienstunterbrechung in administrativer PowerShell im Installationsverzeichnis:

```powershell
$ServiceName = 'openssh-cygwin'
$Log = Join-Path (Get-Location) 'var\log\sshd.log'
Stop-Service -Name $ServiceName -ErrorAction Stop
try {
    if (Test-Path -LiteralPath $Log) {
        Move-Item -LiteralPath $Log -Destination ($Log + '.' + (Get-Date -Format 'yyyyMMdd-HHmmss')) -ErrorAction Stop
    }
} finally {
    Start-Service -Name $ServiceName
}
```

Den neuen Logpfad und seine ACLs danach prüfen. Archive nach eigener
Aufbewahrungsfrist löschen; für regelmäßige Rotation diesen Ablauf in einem
administrativen Wartungsjob mit Fehlerprotokollierung ausführen. Logs können
Benutzernamen und Verbindungsdaten enthalten.

## 5. NTFS-Rechte, Aktualisierung und Entfernen

### SYSTEM-Konfiguration bearbeiten

Nach der Einrichtung kann `etc\sshd_config` auch für Administratoren direkt
unlesbar sein. Für Änderungen wie LogLevel oder AllowUsers eine geschützte
Arbeitskopie per Backupmodus verwenden. Besitzer und ACL des Originals behalten.
Beispiel in erhöhter PowerShell, Pfad anpassen:

```powershell
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$Edit = Join-Path $Root ('var\backups\config-' + [guid]::NewGuid().ToString('N'))
$Original = Join-Path $Edit 'original'
$Changed = Join-Path $Edit 'changed'
New-Item -ItemType Directory -Path $Original,$Changed -Force | Out-Null
icacls.exe $Edit /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'Backupordner konnte nicht geschützt werden' }
robocopy "$Root\etc" $Original sshd_config /B /COPY:DAT /R:0 /W:0
if ($LASTEXITCODE -ge 8) { throw 'Konfiguration konnte nicht gesichert werden' }
Copy-Item "$Original\sshd_config" "$Changed\sshd_config"
$Before = (Get-Acl -LiteralPath "$Root\etc\sshd_config").Sddl
Start-Process notepad.exe -ArgumentList ('"' + "$Changed\sshd_config" + '"') -Wait
$Text = [IO.File]::ReadAllText("$Changed\sshd_config").Replace("`r`n","`n")
[IO.File]::WriteAllText("$Changed\sshd_config", $Text, (New-Object Text.UTF8Encoding($false)))
robocopy $Changed "$Root\etc" sshd_config /B /COPY:DAT /IS /IT /R:0 /W:0
if ($LASTEXITCODE -ge 8) { throw 'Zurückkopieren fehlgeschlagen; Sicherung behalten' }
if ((Get-Acl -LiteralPath "$Root\etc\sshd_config").Sddl -ne $Before) { throw 'Besitzer/ACL haben sich verändert' }
& "$Root\bin\bash.exe" --noprofile --norc -c '/usr/sbin/sshd -t'
if ($LASTEXITCODE -ne 0) {
    robocopy $Original "$Root\etc" sshd_config /B /COPY:DAT /IS /IT /R:0 /W:0
    if ($LASTEXITCODE -ge 8) { throw 'Rückkehr zur Sicherung fehlgeschlagen; Dienst nicht starten' }
    throw 'Syntaxfehler; alte Konfiguration zurückgespielt'
}
Restart-Service openssh-cygwin
```

Die Sicherung behalten, bis Anmeldung und Logs geprüft sind. Eine alte
Gesamtkonfiguration später nicht über zwischenzeitliche Änderungen kopieren.
Dieser Ablauf benötigt die Rechte für Robocopy /B. Er lockert weder den
Konfigurationsbesitzer noch StrictModes. Nicht-Administrator-Konten können
und sollen diese Änderungen nicht selbst ausführen.

### Rechte sichern und aktualisieren

Cygwin bildet POSIX-Rechte auf NTFS-ACLs ab. Dabei können `NULL SID:(DENY)` und
Einträge der Gruppe `None` erscheinen. Revision 1 änderte durch pauschales
`chmod` auch den Installationswurzelordner; diese Wrapper-Aufrufe sind entfernt.
Vor Änderungen bestehende ACLs lokal sichern:

```powershell
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$Backup = 'C:\OpenSSH-Backup'
New-Item -ItemType Directory -Path $Backup -Force | Out-Null
icacls.exe $Root /save "$Backup\dacl.txt" /t /c
Get-Acl -LiteralPath $Root | Format-List Owner,Sddl | Out-File "$Backup\root-acl.txt"
```

`icacls /save` sichert DACLs, nicht die Besitzer aller Dateien. Den Backupordner
einschließlich privater Hostschlüssel nur Administratoren und SYSTEM zugänglich
machen. Blockieren alte Rechte ein Update oder Entfernen, den Besitzer nur am
betroffenen Pfad mit `icacls /setowner` setzen und die benötigten Administrator-
und SYSTEM-Rechte gezielt wiederherstellen. Kein blindes rekursives
`icacls /reset`: dadurch gehen die für SSH benötigten POSIX-Abbildungen verloren.
Eine DACL-Sicherung mit `icacls <übergeordneter-Ordner> /restore <Sicherung>`
am ursprünglichen Pfad zurückspielen; Besitzer getrennt prüfen.

Aktualisierung von Revision 1 auf 3 wurde mit einer lokalen ACL-Korrektur und
Robocopy-Backupmodus erfolgreich getestet. Die unveränderte Revision 3 brach am
ACL-Aufruf ab. Der korrigierte Ablauf der Revision 4 benötigt eine neue Abnahme:

1. Neues ZIP prüfen und in einen neuen, nur administrativ beschreibbaren Ordner
   entpacken. Den alten Baum behalten. Aktuelle Dienstregistrierung mit
   `bin\cygrunsrv.exe -VQ openssh-cygwin` lokal sichern.
2. Genau diesen Dienst stoppen. `etc`, Homes und eigene Daten mit ACLs/Besitzern
   auf ein geeignetes NTFS-Ziel sichern, etwa mit administrativem
   `robocopy <Quelle> <Ziel> /E /B /COPYALL /DCOPY:DAT`. `/B` verwendet den
   Backupmodus, damit auch nur SYSTEM lesbare private Hostschlüssel kopiert
   werden. Erhöhtes Terminal und verfügbare Sicherungs-/Wiederherstellungsrechte
   (`SeBackupPrivilege`, `SeRestorePrivilege`) sind dafür erforderlich; bei
   fehlenden Rechten nicht mit unvollständigem Backup fortfahren.
   Exitcodes ab 8 sind Fehler. Backups mit
   privaten Schlüsseln nur Administratoren/SYSTEM zugänglich machen.
3. Konfigurationen, Hostschlüssel und Homes unter Erhalt der Rechte in den neuen
   Baum übernehmen, auch hierfür `robocopy <Quelle> <Ziel> /E /B /COPYALL /DCOPY:DAT`
   verwenden. Anzahl, Hashes, Besitzer und ACLs aller privaten Hostschlüssel
   prüfen, ohne deren Inhalte auszugeben. Aktive Konfigurationen nicht durch Vorlagen ersetzen.
   `nsswitch.conf` auf den gewünschten Homepfad prüfen, neue Vorlagen separat vergleichen.
4. Den gestoppten eigenen Dienst mit dem **alten** `bin\cygrunsrv.exe -R openssh-cygwin`
   entfernen. Im neuen Ordner `.\install-server.cmd --yes --name openssh-cygwin`
   ausführen, nur bei gewünschter Portänderung zusätzlich `--port` angeben.
   Damit werden Programmpfad und `-E`-Argument neu registriert.
5. Vor dem Start `sshd -t`, Schlüsselbesitzer und Modi prüfen. Nach dem Start
   Dienstregistrierung, Hostschlüssel-Fingerprints, Anmeldung, Exitcodes, SFTP und
   Logdatei prüfen. Den alten Baum erst nach Abnahme löschen.

Für eine Rückkehr den neuen Dienst stoppen/entfernen, den alten Baum samt
Konfiguration und ACLs wiederherstellen und dessen gesicherte Dienstregistrierung
neu einrichten. Revision 1 kann mit `--yes` Konfigurationen löschen; ihren
Installer dafür nicht ohne gesonderte Sicherung verwenden.

Zum Entfernen als Administrator `bin\cygrunsrv.exe -E openssh-cygwin` und dann
`bin\cygrunsrv.exe -R openssh-cygwin` ausführen. Erst danach den eigenen Baum und
die dafür angelegte Firewallregel entfernen. Bei blockierenden ACLs die gezielte
Besitzer-/DACL-Reparatur oben verwenden.

## 6. Abnahmegrenze

Zusätzlich Dienststart nach Windows-Neustart, den korrigierten Updateablauf,
Rückkehr und echten
Netzwerkzugriff prüfen. Freigaben bei Schlüsselanmeldung können zusätzliche
Windows-Authentifizierung erfordern. Ansible/ähnliche Werkzeuge gegen Cygwin-Bash
prüfen. Grundlagen: [Cygwin-Konten und NTFS-Rechte](https://cygwin.com/cygwin-ug-net/ntsec.html),
[Microsoft icacls](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls).
Backupmodus: [Microsoft robocopy](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy).
