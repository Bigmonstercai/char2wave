# mysetup.py
from distutils.core import setup
import py2exe
setup(windows=[{"script": "char2wave.py"}], options={"py2exe": {"includes": ["sip"]}})
