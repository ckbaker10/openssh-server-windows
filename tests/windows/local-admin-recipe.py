"""Execute the documented key recipe against the disposable member's local admin."""
from acceptance import *

pub=(ROOT/'key.pub').read_text().strip()
script="""getent passwd Administrator
getent passwd 'MACHINE+Administrator'
id 'MACHINE+Administrator'
mkdir -p /home/Administrator/.ssh
cat >> /home/Administrator/.ssh/authorized_keys <<'KEY'
PUBLIC_KEY
KEY
chown -R "$(id -u 'MACHINE+Administrator')" /home/Administrator
chmod 700 /home/Administrator /home/Administrator/.ssh
chmod 600 /home/Administrator/.ssh/authorized_keys
stat -c '%u %a %n' /home/Administrator /home/Administrator/.ssh /home/Administrator/.ssh/authorized_keys
""".replace('PUBLIC_KEY',pub)
bash('documented-local-key',script)
ssh('documented-local-login')
