from acceptance import *
pub=(ROOT/'key.pub').read_text().strip()
bash('standalone-key',"mkdir -p /home/Administrator/.ssh; printf '%s\\n' "+shlex.quote(pub)+" > /home/Administrator/.ssh/authorized_keys; chown -R \"$(id -u Administrator)\" /home/Administrator; chmod 700 /home/Administrator /home/Administrator/.ssh; chmod 600 /home/Administrator/.ssh/authorized_keys; stat -c '%u %a %n' /home/Administrator /home/Administrator/.ssh /home/Administrator/.ssh/authorized_keys")
config('standalone-config',BASE+'AllowUsers Administrator\n')
ssh('standalone-login','Administrator')
