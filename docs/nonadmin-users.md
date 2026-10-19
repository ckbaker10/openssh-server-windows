# Lokales Nicht-Administrator-Konto einrichten

`install-user.cmd` ist ein **administrativer Einrichtungshelfer für eine später
unprivilegierte SSH-Sitzung**. Der Serverdienst bleibt LocalSystem. Der Helfer
legt kein Windows-Konto an und ändert keine Windows-Gruppen oder Kennwörter.

## Erstinstallation

Ein vorhandenes aktiviertes lokales Konto verwenden, das kein Mitglied von
Administrators ist. Built-in Administrator und Guest werden abgewiesen. Für ein
neues Konto kann ein Administrator beispielsweise `New-LocalUser` mit einem
über `Read-Host -AsSecureString` eingegebenen Kennwort verwenden. Dieses Kennwort
wird für die vorgesehene SSH-Schlüsselanmeldung nicht verwendet; Passwortauthentifizierung
bleibt in der Paketkonfiguration abgeschaltet. Keine leeren Kennwörter anlegen.

In einer **erhöhten 64-Bit-PowerShell**, vorzugsweise an der lokalen Konsole:

```powershell
Set-Location 'C:\Program Files\OpenSSH-Cygwin'
.\install-user.cmd sshtest 'C:\Keys\sshtest.pub'
```

Für einen anderen bereits eingerichteten Dienst:

```powershell
.\install-user.cmd sshtest 'C:\Keys\sshtest.pub' -ServiceName openssh-cygwin
```

Nur die öffentliche OpenSSH-Schlüsseldatei übergeben, keinen privaten Schlüssel.
Die Datei darf genau einen Schlüssel ohne authorized_keys-Optionen enthalten.
`ssh-keygen` prüft den Schlüssel. Der Kontoname darf 1-20 ASCII-Zeichen aus
Buchstaben, Ziffern, `_`, `.` und `-` enthalten und nicht mit einem Punkt enden.
Domänenkonten und abweichende NSS-Homepfade werden vom Helfer nicht unterstützt.

Der Helfer prüft die lokale SID, die Cygwin-Kontodaten und Gruppen sowie
`/home/<Kontoname>`. Das Home wird **neu** erstellt. Existiert bereits ein Home,
bricht er vor Änderungen ab, statt Schlüssel oder Daten zu überschreiben. Für
weitere Schlüssel kann der Benutzer seine eigene authorized_keys bearbeiten;
vorhandene Homes nach der manuellen Anleitung in INSTALLATION.md einrichten.

Der Helfer sichert die aktive SYSTEM-Konfiguration per Robocopy-Backupmodus in
einem nur Administratoren/SYSTEM zugänglichen Ordner unter
`var\backups\user-<UTC>-<ID>\original`. `/B` braucht verfügbare Sicherungs- und
Wiederherstellungsrechte. Backupfehler und Robocopy-Exitcodes ab 8 brechen ab.
Eine vorhandene **globale** AllowUsers-Liste wird um das Konto ergänzt, ohne
einen bereits identischen Eintrag zu duplizieren. Die Paketvorlage selbst besitzt
keine AllowUsers-Liste; fehlt sie, wird keine neue Einschränkung eingeführt.
Match-Blöcke werden nicht bearbeitet. Globale Include-Direktiven benötigen eine
manuelle Prüfung und werden abgewiesen. AllowUsers-Muster mit Anführungszeichen
oder Escape-Sequenzen benötigen ebenfalls
eine manuelle Prüfung. DenyUsers, DenyGroups, AllowGroups und
andere Zugriffsbeschränkungen bleiben wirksam und müssen zum Konto passen.

Ein laufender Dienst wird vor den Änderungen gestoppt; der Helfer prüft, dass
die LocalSystem-Dienstregistrierung genau zu diesem Installationsordner gehört.
`sshd_config` wird mit `/COPY:DAT` zurückkopiert, ihr Besitzer und ihre ACL
müssen gleich bleiben. Nach erfolgreichem `sshd -t` werden Home, `.ssh` und die
LF-/UTF-8-Schlüsseldatei angelegt. `icacls /setowner` setzt nur diese drei Pfade
auf die Benutzer-SID, Bash prüft den Besitzer und setzt 700/700/600.

Ein vorher laufender Dienst wird nach Erfolg wieder gestartet. Ein bereits
gestoppter Dienst bleibt gestoppt. Mit `-NoRestart` bleibt er auch nach Erfolg
gestoppt. Das Stoppen unterbricht die Verfügbarkeit; den Helfer nicht über eine
Verbindung ausführen, deren Fortbestand vom betroffenen Dienst abhängt.

Bei einem Fehler nach Beginn der Änderungen wird die ursprüngliche Konfiguration
zurückkopiert und der Dienst **nicht** automatisch gestartet. Ein eventuell neu
angelegtes Home bleibt zur Prüfung erhalten. Erst Konfiguration, Schlüssel,
Besitzer und Modi prüfen, dann gezielt starten. Misslingt die Rückkopie, die
ausgegebene Sicherung zur Wiederherstellung verwenden. Ein nach einem Abbruch
übrig gebliebener `var\run\install-user.lock` darf erst entfernt werden, wenn
keine andere Einrichtung mehr läuft.

Der neue Helfer wurde auf Linux mit isolierten Windows-/NTFS-Schnittstellen
geprüft; seine vollständige Ausführung auf Windows steht noch aus. Die manuelle
[Nicht-Administrator-Teilabnahme der Revision 4](windows-validation-nonadmin-2026-10-19.md)
belegt die zugrunde liegenden Anmeldeschritte und den eingeschränkten Token.

## Anmeldung prüfen

Hostschlüssel vorab über einen vertrauenswürdigen Weg übernehmen, nicht die
Hostschlüsselprüfung abschalten. Von einem SSH-Client zum Beispiel:

```bash
ssh -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -i ~/.ssh/testkey -p 2222 sshtest@server.example 'id; printf "HOME=%s\n" "$HOME"'
scp -P 2222 -i ~/.ssh/testkey datei sshtest@server.example:datei
```

Erwartet sind `/home/sshtest`, keine Administrators-Gruppe, Medium Mandatory
Level, `IsInRole(Administrator) = False` in PowerShell sowie verweigerte
Schreibrechte nach Windows/System32 und verweigerter Zugriff auf private
Hostschlüssel und Dienststeuerung. Passwortanmeldung muss abgewiesen bleiben.
Dateitransfer mit Hashvergleich, Exitcode und TTY prüfen. Zusätzliche Gruppen,
Domänenkonten, parallele Sitzungen und Ansible sind noch nicht nativ abgenommen.

## Zugang und Konto entfernen

Der Einrichtungshelfer löscht keine Konten oder Profile. Für eine Entfernung in
einem administrativen Wartungsfenster zuerst die SID festhalten:

```powershell
$Name = 'sshtest'
$Sid = (Get-LocalUser -Name $Name).SID.Value
$Sid # Vor Kontoloeschung/Neustart lokal festhalten; danach genau diese SID verwenden.
$Root = 'C:\Program Files\OpenSSH-Cygwin'
$UserHome = Join-Path (Join-Path $Root 'home') $Name
Disable-LocalUser -Name $Name
Stop-Service -Name openssh-cygwin
```

Alle Sitzungen dieses Kontos beenden. Öffentliche Schlüssel entfernen und eine
vorhandene AllowUsers-Liste über den Konfigurationsablauf in INSTALLATION.md
gezielt anpassen. Nicht blind eine alte Gesamtkonfiguration zurückspielen;
dadurch würden spätere Änderungen verloren gehen. Beim Entfernen des letzten
AllowUsers-Eintrags nicht versehentlich die gesamte Einschränkung aufheben.

Nach Prüfung des exakten Homepfads und ohne darin enthaltene Reparsepoints
können dessen Rechte zur gezielten Entfernung übernommen werden:

```powershell
icacls.exe $UserHome /setowner '*S-1-5-32-544' /t /c
icacls.exe $UserHome /grant '*S-1-5-32-544:(OI)(CI)F' /t /c
Remove-Item -LiteralPath $UserHome -Recurse -Force
Remove-LocalUser -Name $Name
```

Native Fehlercodes der icacls-Aufrufe prüfen; bei Fehlern nicht mit dem Löschen
fortfahren. Niemals den gesamten Installationsbaum auf das Benutzerkonto übertragen.
Anschließend Konfigurationssyntax prüfen und nur den gewählten Dienst wieder starten.

## Geladenes Windows-Profil

Im nativen Test blieb das Profil nach der SSH-Abmeldung und Dienststopp geladen.
Das ist ein beobachteter Befund; ein S4U-Tokenleck oder Speicherleck ist bisher
nicht bewiesen. `reg unload` nicht erzwingen und keine fremden Prozesse beenden.
Nach einem geplanten Neustart ausschließlich das zuvor festgehaltene Konto prüfen:

```powershell
$Profile = Get-CimInstance Win32_UserProfile -Filter "SID='$Sid'"
$Profile | Select-Object SID,LocalPath,Loaded
if ($Profile -and -not $Profile.Loaded) {
    $Profile | Remove-CimInstance
}
```

Bei `Loaded=True` nicht entfernen. Profilverzeichnis und Registry-Hives nicht
pauschal manuell löschen. Eine native Diagnose mit wiederholten Sitzungen,
Handle-/Tokenzahlen und Profilzustand ist noch offen; Details der begrenzten
Quellprüfung stehen im Releasebericht.

## Sitzungsumgebung

Cygwin-OpenSSH übernimmt ausdrücklich Teile der Dienstumgebung, darunter PATH.
Dadurch können SYSTEM-Profilpfade und andere SSH-Installationen auftauchen.
Der Helfer ändert weder den globalen PATH noch die Shell-Vorgabe. Für Skripte
`command -v ssh`, `command -v powershell.exe` bzw. absolute Pfade verwenden;
`command -v` ist in Bash eingebaut und benötigt kein zusätzliches `which`.
Eine globale PATH-Bereinigung ist ohne Tests der Windows-Befehle und Werkzeuge
nicht Teil dieser Änderung. Eigene Skripte können ihren PATH gezielt festlegen.

Grundlagen: [AllowUsers und Match](https://man.openbsd.org/sshd_config#AllowUsers),
[Robocopy-Backupmodus](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy).
