"""Enable lab-only WinRM HTTPS and trust only the exported public leaf certificate."""
import base64
import json
from pathlib import Path
import ssl
import sys
from lab import ROOT, CONFIG, ps, close_shells

machine=sys.argv[1]
script=Path(__file__).with_suffix('.ps1')
result=ps(machine,script.read_text())
output=ROOT/'https-setup'
output.mkdir(mode=0o700,exist_ok=True)
(output/(machine+'.stdout')).write_bytes(result.std_out)
(output/(machine+'.stderr')).write_bytes(result.std_err)
if result.status_code:
    sys.exit('HTTPS setup failed; inspect the private setup logs')
record=json.loads(result.std_out.decode('utf-8-sig'))
certificate=ssl.DER_cert_to_PEM_cert(base64.b64decode(record['Certificate']))
relative=machine+'/management-certificate.pem'
(ROOT/relative).write_text(certificate)
close_shells()
CONFIG[machine+'_url']='https://127.0.0.1:'+('57985' if machine=='client' else '57986')+'/wsman'
CONFIG[machine+'_ca']=relative
(ROOT/'config.json').write_text(json.dumps(CONFIG,indent=2)+'\n')
print(machine+': HTTPS configured; public certificate saved and required for validation')
