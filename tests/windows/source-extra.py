"""Exercise the Match CIDR exemption and reverse AllowUsers entry order."""
from acceptance import *

config('config-match-cidr',BASE+'AllowUsers MACHINE+Administrator\nMatch Address *,!DENIED_SOURCE,!SOURCE_CIDR\n    DenyUsers *\n')
ssh('match-cidr-allowed')
config('config-unrestricted-first',BASE+'AllowUsers MACHINE+Administrator\nAllowUsers MACHINE+Administrator@DENIED_SOURCE\n')
ssh('unrestricted-first-allowed')
config('config-source-extra-final',BASE+'AllowUsers MACHINE+Administrator\n')
