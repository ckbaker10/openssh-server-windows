# Fehlerhilfe und Cygwin-Grenzen

## Exitcode 127 bei Bash-Aufrufen

Mit --noprofile --norc übernimmt Bash den umgesetzten Windows-PATH. Für
Cygwin-Programme und deren Abhängigkeiten /usr/bin, /bin und /usr/sbin ergänzen:

```powershell
.\bin\bash.exe --noprofile --norc -c 'export PATH=/usr/bin:/bin:/usr/sbin:$PATH; /usr/sbin/sshd -t'
```

In eigenen .sh-Dateien den Export an den Anfang setzen und LF-Zeilenenden
verwenden. Keine dauerhafte Änderung des globalen Windows-PATH ist dafür nötig.
Der Benutzerhelfer setzt diesen PATH für seine Syntaxprüfung selbst.

## SYSTEM-Konfiguration lässt sich nicht lesen

sshd_config kann nach Einrichtung ausschließlich SYSTEM gehören und für
Administratoren unlesbar sein. Über Robocopy /B /COPY:DAT in einen geschützten
Arbeitsordner kopieren, dort bearbeiten und mit /IS /IT zurückkopieren.
Exitcodes prüfen, Besitzer/ACL erhalten und vor Neustart sshd -t ausführen.
Der vollständige Ablauf steht in INSTALLATION.md. StrictModes nicht abschalten.

## Benutzerhelfer endet mit gestopptem Dienst

Nach einem Mutationsfehler wird die Konfiguration zurückgespielt und der Dienst
zur Prüfung gestoppt gelassen. Konfiguration und eventuell angelegtes Home
prüfen. Für einen erfolgreichen neuen Einrichtungslauf `-Start` verwenden;
zum anschließenden manuellen Start `Start-Service openssh-cygwin` ausführen.
Ein vorhandenes Home wird auch nach einem Fehlversuch nicht überschrieben.

## Sporadischer fork-Fehler oder Verbindungsabbruch

`fork of unprivileged child failed` bedeutet, dass ein Cygwin-Kindprozess nicht
erstellt werden konnte. Die Cygwin-FAQ nennt unter anderem DLL-Adressraumkonflikte
und störende Drittsoftware als mögliche Ursachen. Serverlog und Windows-
Ereignisse zum gleichen Zeitpunkt sichern, freien Speicher und Runtime-Version
prüfen und die Kompatibilität installierter Schutz-/Hooksoftware untersuchen.
Eine konkrete Ursache lässt sich aus der sshd-Meldung allein nicht ableiten.
[Cygwin: fork failures](https://cygwin.com/faq/faq.html#faq.using.fixing-fork-failures).

Wiederholbare Operationen können nach einem einzelnen Abbruch erneut versucht
werden; nach Transfers Zieldatei und Hash prüfen. Befehle mit unbekannter
Teilwirkung nicht blind wiederholen. MaxStartups steuert parallele noch nicht
authentifizierte Verbindungen und ist kein belegter Fix für diesen fork-Fehler.
Keine pauschalen Virenscanner-Ausnahmen oder globalen Sicherheitsänderungen vornehmen.

## Windows-Profil bleibt geladen

Das Profil eines per Schlüssel angemeldeten Kontos kann nach Sitzungsende,
Dienststopp oder Kontolöschung geladen bleiben. Cygwin dokumentiert in
`winsup/cygwin/sec/auth.cc`, Funktion load_user_profile, einen vorerst behaltenen
Registry-Handle und einen offenen TODO zum zuverlässigen Profilentladen.
Das belegt keine konkrete S4U-Tokenursache und kein gemessenes Speicherwachstum.

SID vor Kontolöschung festhalten. Nach einem geplanten Neustart anhand genau
dieser SID prüfen und nur ein nicht mehr geladenes Profil entfernen:

```powershell
$Sid = '<zuvor festgehaltene Benutzer-SID>'
$Profile = Get-CimInstance Win32_UserProfile -Filter "SID='$Sid'"
$Profile | Select-Object SID,LocalPath,Loaded
if ($Profile -and -not $Profile.Loaded) { $Profile | Remove-CimInstance }
```

Bei Loaded=True nicht erzwingen: kein reg unload und kein pauschales Löschen
von HKEY_USERS, ProfileList oder Profilverzeichnissen. Eine Runtime-Korrektur
benötigt reproduzierbare Handle-/Profilmessungen und Windows-Abnahme.

## PATH und Werkzeuge in SSH-Sitzungen

Cygwin-OpenSSH übernimmt Teile der Dienstumgebung einschließlich PATH.
Dadurch können Systemprofilpfade oder weitere SSH-Installationen auftauchen.
In Skripten absolute Pfade oder `command -v ssh` beziehungsweise
`command -v powershell.exe` verwenden. command -v ist in Bash eingebaut;
ein zusätzliches which ist nicht erforderlich. Die Einrichtung ändert weder
den globalen PATH noch die Shell-Vorgabe für andere Anwendungen.

## Umfang der Abnahme

Linux-/Wine-Prüfungen und simulierte Windows-Schnittstellen ersetzen keine
native Windows-Abnahme. Neue Helferpfade, Dienststart nach Neustart, Rückkehr,
Domänen-/Zusatzgruppen, parallele Sitzungen, Netzfreigaben und Ansible gesondert
prüfen. Schlüsselanmeldung kann für Netzfreigaben zusätzliche Windows-
Authentifizierung benötigen. Bis zur vollständigen Abnahme bleiben Releases Prereleases.
