# Unprivilegierte Benutzer einrichten

Der SSH-Dienst bleibt LocalSystem. `install-user.cmd` richtet als Administrator
ein vorhandenes Windows-Konto für spätere eingeschränkte SSH-Sitzungen ein.
Er legt keine Windows-Konten an und ändert weder Gruppen noch Kennwörter.

## Voraussetzungen

- Aktiviertes lokales Konto ohne Administratorrechte; Built-in Administrator
  und Guest werden abgewiesen.
- Genau eine öffentliche OpenSSH-Schlüsseldatei, ohne private Daten oder
  authorized_keys-Optionen.
- Neues Cygwin-Home `/home/<Kontoname>` gemäß nsswitch.conf. Bestehende Homes
  werden vor Änderungen abgewiesen und niemals überschrieben.
- Erhöhte 64-Bit-PowerShell und verfügbarer Robocopy-Backupmodus.

Kontonamen dürfen 1-20 ASCII-Zeichen aus Buchstaben, Ziffern, `_`, `.` und `-`
enthalten, nicht mit einem Punkt enden und müssen mit Buchstabe/Ziffer beginnen.
Domänenkonten und abweichende Homepfade sind im Helfer nicht unterstützt.

Ein Konto bei Bedarf vorher über Windows einrichten, zum Beispiel:

```powershell
$Password = Read-Host 'Kennwort für das neue Windows-Konto' -AsSecureString
New-LocalUser -Name sshuser -Password $Password
Remove-Variable Password
```

Keine Administratorgruppe hinzufügen. Das Kennwort wird für die vorgesehene
SSH-Schlüsselanmeldung nicht verwendet; Passwortanmeldung bleibt abgeschaltet.

## Helfer ausführen

In einer erhöhten PowerShell im Installationsordner:

```powershell
.\install-user.cmd sshuser 'C:\Keys\sshuser.pub' -Start
```

Bei einem anderen Dienstnamen `-ServiceName <Name>` ergänzen. Die Registrierung
muss zu diesem Installationsordner gehören und als LocalSystem laufen.
Eine laufende Instanz wird für die Einrichtung gestoppt; deshalb eine Konsole
nutzen, die nicht vom Fortbestand dieses SSH-Dienstes abhängt.

| Option | Verhalten nach erfolgreicher Einrichtung |
| --- | --- |
| ohne Startoption | Einen vorher laufenden Dienst wieder starten; einen gestoppten gestoppt lassen |
| `-Start` | Dienst immer starten, auch nach einem früheren Fehlversuch |
| `-NoRestart` | Dienst gestoppt lassen |

`-Start` und `-NoRestart` dürfen nicht kombiniert werden. Die Abschlussmeldung
zeigt ausdrücklich RUNNING oder STOPPED; bei STOPPED kann anschließend
`Start-Service openssh-cygwin` ausgeführt werden.

## Änderungen und Rückkehr bei Fehlern

Der Helfer prüft Windows-SID, Cygwin-Kontodaten, Home und Gruppen. Er validiert
den öffentlichen Schlüssel mit ssh-keygen. Nur Home, .ssh und authorized_keys
werden angelegt, per icacls der Benutzer-SID zugeordnet und auf 700/700/600 gesetzt.
Für spätere zusätzliche Schlüssel kann der Benutzer seine eigene authorized_keys bearbeiten.

Eine vorhandene globale AllowUsers-Liste wird ohne identischen Doppeleintrag
ergänzt. Fehlt sie, wird keine neue Liste erzeugt. Match bleibt unverändert;
globale Includes und zitierte/escapte AllowUsers-Muster brauchen manuelle Prüfung.
DenyUsers, DenyGroups, AllowGroups und andere Regeln bleiben wirksam.

Die SYSTEM-Konfiguration wird per Robocopy /B /COPY:DAT in einen geschützten
Ordner `var\backups\user-<UTC>-<ID>` gesichert. Besitzer und ACL beim
Zurückschreiben müssen gleich bleiben. Vor dem Anlegen des Homes wird mit
explizitem Cygwin-PATH `sshd -t` ausgeführt. Für manuelle Konfigurationsänderungen
den Ablauf in INSTALLATION.md nutzen; direkter Administratorzugriff kann scheitern.

Bei Fehlern nach Beginn der Änderungen stoppt der Helfer den Dienst und versucht
die ursprüngliche Konfiguration zurückzuspielen. Er startet dann nicht automatisch.
Ein eventuell angelegtes Home bleibt zur Prüfung erhalten. Backup, Konfiguration,
Besitzer und Modi prüfen, bevor der Dienst wieder gestartet wird. Eine verwaiste
`var\run\install-user.lock` erst entfernen, wenn keine Einrichtung mehr läuft.

## Eingeschränkte Anmeldung prüfen

Hostschlüssel vorab vertrauenswürdig übernehmen, dann vom Client beispielsweise:

```bash
ssh -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -i ~/.ssh/userkey -p 2222 sshuser@server.example 'id; printf "HOME=%s\n" "$HOME"'
scp -P 2222 -i ~/.ssh/userkey datei sshuser@server.example:datei
```

Erwartet: /home/sshuser, keine Administrators-Gruppe, Medium Mandatory Level,
Admin=False bei PowerShell-Tokenprüfung. Schreibzugriff auf Windows-System-
verzeichnisse, Lesen privater Hostschlüssel/sshd_config und Dienststeuerung sollen
verweigert werden. TTY, Exitcodes und Dateitransfers mit Hashvergleich prüfen;
Passwortanmeldung muss abgewiesen bleiben.

## Konto entfernen

In einem administrativen Wartungsfenster die genaue SID vor Löschung/Neustart
festhalten, Konto deaktivieren und eigenen Dienst stoppen:

```powershell
$Name = 'sshuser'
$Sid = (Get-LocalUser -Name $Name).SID.Value
$Sid
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$UserHome = Join-Path (Join-Path $Root 'home') $Name
Disable-LocalUser -Name $Name
Stop-Service openssh-cygwin
```

Sitzungen des Kontos beenden. Schlüssel entfernen und eine AllowUsers-Liste über
den Backupmodus gezielt anpassen. Keine alte Gesamtkonfiguration über spätere
Änderungen kopieren. Beim Entfernen des letzten AllowUsers-Eintrags nicht
versehentlich die gesamte Einschränkung aufheben.

Nur nach Prüfung des exakten eigenen Homepfads und ohne Reparsepoints darin:

```powershell
icacls.exe $UserHome /setowner '*S-1-5-32-544' /t /c
if ($LASTEXITCODE -ne 0) { throw 'Besitzerwechsel fehlgeschlagen' }
icacls.exe $UserHome /grant '*S-1-5-32-544:(OI)(CI)F' /t /c
if ($LASTEXITCODE -ne 0) { throw 'Rechteänderung fehlgeschlagen' }
Remove-Item -LiteralPath $UserHome -Recurse -Force
Remove-LocalUser -Name $Name
```

Syntax mit dem in INSTALLATION.md gezeigten PATH-Präfix prüfen und Dienst
gezielt starten. Windows-Profile können geladen bleiben; vor Profilentfernung
die Hinweise in TROUBLESHOOTING.md beachten. Kein erzwungenes Hive-Entladen.
