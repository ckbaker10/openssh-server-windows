# Installation und Betrieb unter Windows

Voraussetzungen: Windows x86_64, Windows PowerShell 5.1 und erhöhte
Administratorrechte für die Einrichtung. Das Paket bringt Cygwin und Bash mit;
das optionale Windows-OpenSSH-Feature und ein Microsoft-SDK sind nicht nötig.
Der Dienst läuft als LocalSystem, Anmeldungen verwenden das jeweilige Windows-Konto.

## Entpacken und prüfen

ZIP und SHA256SUMS aus demselben Release laden. Den Hash vergleichen:

```powershell
Get-FileHash .\openssh-10.6p1-cygwin-x86_64.zip -Algorithm SHA256
```

Nach `C:\Program Files\OpenSSH-Cygwin` entpacken und gegebenenfalls den äußeren
ZIP-Ordner umbenennen. `install-server.cmd` und `bin\cygwin1.dll` müssen direkt
darunter liegen. Nur Administratoren und SYSTEM dürfen diesen Baum verändern.
Anschließend in PowerShell prüfen:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
powershell.exe -NoProfile -File .\verify-package.ps1
```

Bei Bedarf `-Path 'C:\Program Files\OpenSSH-Cygwin'` ausdrücklich angeben.
Der Prüfer liest SHA256SUMS ohne JSON. Eine leere Liste, fehlende oder geänderte
Nutzdateien führen zum Fehler. Die Nutzdateiliste schließt sich selbst und das
Manifest aus; das Manifest erfasst zusätzlich die Liste. Der ZIP-Hash umfasst alles.
Nach der Einrichtung ändern sich Konfigurationen; nur unveränderte Pakete vergleichen.

## Dienst einrichten

In einer erhöhten 64-Bit-PowerShell im Installationsordner:

```powershell
.\install-server.cmd --yes --name openssh-cygwin --port 2222
```

`--user`, `--pwd` und `--privileged` werden abgewiesen. Es wird kein zusätzliches
Dienstkonto angelegt. Ohne `--port` bleibt ein bestehender Port erhalten; bei
einer neuen Konfiguration ist es 22. `--port 22` setzt auch ausdrücklich zurück.
`--yes` erhält vorhandene sshd_config, ssh_config und nsswitch.conf; die Dateien
werden unter `etc\backups\<UTC>-<ID>` gesichert. Fehlende Dateien kommen aus
`etc\defaults\etc`. Eine ausdrückliche Portangabe ändert die Serverkonfiguration.

Einen laufenden Dienst gleichen Namens vorher stoppen. Eine bereits vorhandene
Registrierung behält Programmpfad und Argumente; beim Umzug den Updateablauf nutzen.

## Schlüssel für Administrator einrichten

Als Zielbenutzer die mitgelieferte Shell öffnen:

```powershell
.\open-shell.cmd
```

Sie setzt HOME anhand der Cygwin-Kontodaten. `etc\nsswitch.conf` legt `/home/%U`
und Bash fest. Vorhandene `/etc/passwd`-Einträge haben Vorrang. In Bash:

```bash
id
getent passwd "$(id -u)"
printf '%s\n' "$HOME"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME" "$HOME/.ssh"
cat >> "$HOME/.ssh/authorized_keys" <<'KEY'
ssh-ed25519 AAAA...hier_den_eigenen_oeffentlichen_Schluessel_einsetzen
KEY
chmod 600 "$HOME/.ssh/authorized_keys"
exit
```

Nur einen echten öffentlichen Schlüssel einsetzen, keinen privaten Schlüssel.
Für eingeschränkte Konten den separaten Helfer gemäß NONADMIN-USERS.md verwenden.

Wenn Dateien zuvor mit PowerShell angelegt wurden, kann die Besitzergruppe
Administrators Cygwin-chmod verhindern. Den Besitzer nur auf dem betroffenen
Benutzer-Home korrigieren und die Modi in Bash erneut setzen:

```powershell
$Account = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$UserHome = 'C:\Program Files\OpenSSH-Cygwin\home\Administrator'
icacls.exe $UserHome /setowner $Account /t /c
if ($LASTEXITCODE -ne 0) { throw 'Besitzerwechsel fehlgeschlagen' }
```

Das Beispiel gilt für das eigene Konto; für ein anderes Konto dessen Namen
verwenden. Niemals den ganzen Installationsbaum auf einen normalen Benutzer übertragen.
StrictModes eingeschaltet lassen.

## Prüfen, starten und verbinden

Jeder Bash-Aufruf ohne Profile benötigt den Cygwin-PATH. Aus PowerShell mit
einfachen Anführungszeichen übergeben, damit `$PATH` in Bash ausgewertet wird:

```powershell
.\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
if ($LASTEXITCODE -ne 0) { throw 'Konfigurationsprüfung fehlgeschlagen' }
Start-Service openssh-cygwin
.\bin\cygrunsrv.exe -VQ openssh-cygwin
Get-Content .\var\log\sshd.log -Tail 10
```

Firewall gezielt für den gewählten TCP-Port und gewünschte Quellen freigeben.
Hostschlüssel über einen vertrauenswürdigen Weg prüfen und beim Client speichern.
Danach beispielsweise `ssh -o StrictHostKeyChecking=yes -p 2222 Administrator@server.example`.
Schlüsselanmeldung, Passwortablehnung, TTY, Exitcodes und SFTP mit Hashvergleich prüfen.

Die Standardkonfiguration deaktiviert Passwort, Keyboard-Interactive und X11.
SFTP läuft intern; Shell und Befehle verwenden Cygwin-Bash. Win32-OpenSSH-
Registry-Einstellungen zur Default-Shell gelten hier nicht. Bash-Skripte müssen
LF-Zeilenenden besitzen. Eigene CRLF-Skripte bei Bedarf mit
`sed -i 's/\r$//' datei.sh` konvertieren.

## SYSTEM-Konfiguration bearbeiten

Nach Einrichtung kann sshd_config auch für Administratoren direkt unlesbar
sein. Änderungen, etwa LogLevel oder AllowUsers, über eine geschützte Kopie
mit Robocopy /B /COPY:DAT vornehmen. Der Besitzer und die ACL des Originals
bleiben erhalten. In einer erhöhten PowerShell:

```powershell
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$Edit = Join-Path $Root ('var\backups\config-' + [guid]::NewGuid().ToString('N'))
$Original = Join-Path $Edit 'original'
$Changed = Join-Path $Edit 'changed'
New-Item -ItemType Directory -Path $Original,$Changed -Force | Out-Null
icacls.exe $Edit /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'Backupordner konnte nicht geschützt werden' }
robocopy "$Root\etc" $Original sshd_config /B /COPY:DAT /R:0 /W:0
if ($LASTEXITCODE -ge 8) { throw 'Sicherung fehlgeschlagen' }
Copy-Item "$Original\sshd_config" "$Changed\sshd_config"
$Before = (Get-Acl -LiteralPath "$Root\etc\sshd_config").Sddl
Start-Process notepad.exe -ArgumentList ('"' + "$Changed\sshd_config" + '"') -Wait
$Text = [IO.File]::ReadAllText("$Changed\sshd_config").Replace("`r`n","`n")
[IO.File]::WriteAllText("$Changed\sshd_config", $Text, (New-Object Text.UTF8Encoding($false)))
robocopy $Changed "$Root\etc" sshd_config /B /COPY:DAT /IS /IT /R:0 /W:0
if ($LASTEXITCODE -ge 8) { throw 'Zurückkopieren fehlgeschlagen; Sicherung behalten' }
if ((Get-Acl -LiteralPath "$Root\etc\sshd_config").Sddl -ne $Before) { throw 'Besitzer/ACL verändert' }
& "$Root\bin\bash.exe" --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
if ($LASTEXITCODE -ne 0) {
    robocopy $Original "$Root\etc" sshd_config /B /COPY:DAT /IS /IT /R:0 /W:0
    if ($LASTEXITCODE -ge 8) { throw 'Wiederherstellung fehlgeschlagen; Dienst nicht starten' }
    throw 'Syntaxfehler; ursprüngliche Konfiguration wiederhergestellt'
}
Restart-Service openssh-cygwin
```

Backupmodus benötigt erhöhte Rechte und verfügbare Sicherungs-/Wiederherstellungs-
privilegien. Die Sicherung bis zur Funktionsprüfung behalten. Eine alte Gesamt-
konfiguration später nicht über zwischenzeitliche Änderungen kopieren.

## Logs und Rotation

Neue Registrierungen starten sshd mit `-D -E /var/log/sshd.log`; die Datei liegt
unter `var\log\sshd.log`. Standard ist LogLevel INFO. Für VERBOSE den obigen
Konfigurationsablauf verwenden. Zur manuellen Rotation in erhöhter PowerShell
im Installationsordner:

```powershell
$Log = Join-Path (Get-Location) 'var\log\sshd.log'
Stop-Service openssh-cygwin -ErrorAction Stop
try {
    if (Test-Path -LiteralPath $Log) {
        Move-Item -LiteralPath $Log -Destination ($Log + '.' + (Get-Date -Format 'yyyyMMdd-HHmmss')) -ErrorAction Stop
    }
} finally { Start-Service openssh-cygwin }
```

Neue Logdatei und Rechte anschließend prüfen. Für automatische Rotation einen
administrativen Wartungsjob mit Fehlerkontrolle und eigener Aufbewahrungsfrist einrichten.

## Aktualisieren

1. Neues ZIP prüfen und in einen neuen, nur administrativ beschreibbaren Ordner
   entpacken. Alten Baum behalten. Dienstregistrierung mit dem alten
   `bin\cygrunsrv.exe -VQ openssh-cygwin` sichern.
2. Eigenen Dienst stoppen. etc, home, Logs und eigene Daten auf ein NTFS-Ziel
   sichern: `robocopy <Quelle> <Ziel> /E /B /COPYALL /DCOPY:DAT /R:1 /W:1`.
   Exitcodes ab 8 sind Fehler. Backup nur Administratoren/SYSTEM zugänglich machen.
3. Aktive Konfigurationen, sämtliche privaten/öffentlichen Hostschlüssel und Homes
   mit denselben /B-/COPYALL-Optionen in den neuen Baum übernehmen. Konfigurationen
   nicht durch Vorlagen ersetzen. NSS-Homepfad und neue Vorlagen separat vergleichen.
   Anzahl, Hashes, Besitzer und Rechte der Hostschlüssel prüfen, keine Inhalte ausgeben.
4. Den gestoppten Dienst mit dem **alten** `bin\cygrunsrv.exe -R openssh-cygwin`
   entfernen. Im neuen Ordner `.\install-server.cmd --yes --name openssh-cygwin`
   ausführen. Nur bei gewünschter Änderung `--port` ergänzen.
5. Mit dem oben gezeigten PATH-Präfix `sshd -t` prüfen. Dienst starten, neue
   Registrierung und Logdatei sowie unveränderte Hostschlüssel-Fingerprints,
   Anmeldung, Exitcodes und SFTP prüfen. Alten Baum erst nach Abnahme löschen.

`/B` ermöglicht das Kopieren nur SYSTEM lesbarer privater Hostschlüssel.
Bei fehlenden Sicherungsrechten oder Kopierfehlern nicht mit unvollständigen
Daten fortfahren. Für eine Rückkehr den neuen Dienst stoppen/entfernen und den
alten Baum mit gesicherten Daten/Rechten und seiner Dienstregistrierung wieder einrichten.

## NTFS-Rechte und Entfernen

Cygwin bildet POSIX-Rechte auf NTFS-ACLs ab; NULL-SID-Deny- und None-Einträge
können dabei vorkommen. Kein blindes rekursives icacls /reset verwenden.
Vor Reparaturen DACLs mit icacls /save sichern; Besitzer werden damit nicht gesichert.
Nur betroffene eigene Pfade gezielt reparieren, Hostschlüssel und StrictModes erhalten.

Zum Entfernen als Administrator im Installationsordner:

```powershell
.\bin\cygrunsrv.exe -E openssh-cygwin
.\bin\cygrunsrv.exe -R openssh-cygwin
```

Fehlercodes prüfen; erst nach erfolgreicher Dienstentfernung den eigenen Baum
und die dafür angelegte Firewallregel löschen. Benutzerprofile und Laufzeit-
grenzen sind in TROUBLESHOOTING.md beschrieben.

Grundlagen: [Cygwin-Rechte](https://cygwin.com/cygwin-ug-net/ntsec.html),
[icacls](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls),
[Robocopy](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy).
