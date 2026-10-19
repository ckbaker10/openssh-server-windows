# Installation unter Windows x86_64

Dieses Paket enthält OpenSSH 10.6p1 mit Cygwin 3.6.11 und einer Bash-Laufzeit.
Es benötigt weder das optionale Windows-OpenSSH-Feature noch ein Microsoft-SDK.
Die Programme wurden unter Linux crosskompiliert. Dienstbetrieb, Anmeldung und
interaktive Sitzungen müssen auf Windows geprüft werden, bevor der Server produktiv verwendet wird.

1. ZIP nach `C:\Program Files\OpenSSH-Cygwin` entpacken. Die Dateien `install-server.cmd`
   und `bin\cygwin1.dll` müssen direkt darunter liegen; gegebenenfalls den äußeren
   ZIP-Ordner entsprechend umbenennen. Das Installationsverzeichnis darf nur von
   Administratoren und SYSTEM verändert werden.
2. Eine Eingabeaufforderung als Administrator öffnen und `install-server.cmd` ausführen.
   Der enthaltene offizielle Cygwin-Helfer `ssh-host-config` führt durch Dienstkonto,
   Hostschlüssel und Dienstinstallation. Einen eigenen Dienstnamen, beispielsweise
   `openssh-cygwin`, wählen, damit vorhandene SSH-Dienste nicht überschrieben werden:
   `install-server.cmd --name openssh-cygwin`.
3. Die Firewall gezielt für den gewünschten Zugriff auf TCP-Port 22 freigeben.
   Falls bereits ein Server diesen Port verwendet, zuvor `etc\sshd_config` anpassen.
4. Den öffentlichen SSH-Schlüssel für das gewünschte Windows-Konto in dessen
   Cygwin-Home unter `/home/<Kontoname>/.ssh/authorized_keys` hinterlegen.
   In der gebündelten Bash als dieser Benutzer `mkdir -p ~/.ssh`,
   `chmod 700 ~/.ssh` und anschließend `chmod 600 ~/.ssh/authorized_keys` ausführen.
   Die Bash wird über `bin\bash.exe` geöffnet. Mit `id` und `echo "$HOME"` das
   tatsächlich aufgelöste Konto und Home prüfen; auf Domänenrechnern können Namen abweichen.
5. Als Administrator `bin\bash.exe -c '/usr/sbin/sshd -t'` ausführen und den
   konfigurierten Dienst mit `bin\cygrunsrv.exe -S openssh-cygwin` starten.

Die mitgelieferte Konfiguration erlaubt Schlüsselanmeldung und deaktiviert
Passwortanmeldung, Keyboard-Interactive und X11-Weiterleitung. SFTP läuft intern.
Shell und Befehlsausführung verwenden die Cygwin-Umgebung. Das ist keine native
Win32-OpenSSH-Installation; deren Registry-Einstellungen für die Default-Shell gelten hier nicht.

Bei Schlüsselanmeldung kann der Zugriff auf Windows-Netzfreigaben zusätzliche
Authentifizierung benötigen. Den Dienstkontext und die tatsächlich benötigten
Datei- und Netzwerkrechte getrennt prüfen. Keine privaten Schlüssel mit dem Paket verteilen.

Zur Abnahme Anmeldung, `whoami`, Befehls-Exitcodes, SFTP-Upload/Download, interaktive
Sitzung und Dienststart nach Windows-Neustart prüfen. Bei Problemen zuerst
`sshd -t`, Dienststatus und lokale Logdateien prüfen.

Zum Entfernen als Administrator `bin\cygrunsrv.exe -E openssh-cygwin` und danach
`bin\cygrunsrv.exe -R openssh-cygwin` ausführen. Erst anschließend das eigene
Installationsverzeichnis und gegebenenfalls die dafür angelegte Firewallregel entfernen.
