"""
Apache mod_wsgi script for bastion

Point to this script in your apache config file.
A template config file was generated as the file `bastion` sitting
next to this file
"""
import sys

# This adds your project's root path to the PYTHONPATH so that you can import
# top-level modules from your project path.  This is how TurboGears QuickStarted
# projects are laid out by default.
import os, sys
#sys.path.append('/usr/lib/python-2.6/site-packages/bastion')

# Set the environment variable PYTHON_EGG_CACHE to an appropriate directory
# where the Apache user has write permission and into which it can unpack egg files.
os.environ['PYTHON_EGG_CACHE'] = '/var/www/.python-eggs'

# Initialize logging module from your TurboGears config file
from paste.script.util.logging_config import fileConfig
fileConfig('/etc/bastion/bastion.ini')

# Finally, load your application's ${config} file.
from paste.deploy import loadapp
application = loadapp('config:/etc/bastion/bastion.ini')
