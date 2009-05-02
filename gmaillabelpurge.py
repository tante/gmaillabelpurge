#!/usr/bin/env python

import ConfigParser
import imaplib
import os.path

CONFIGFILE="~/.gmaillabelpurge"
"""The filename and path of the config file, default is ~/.gmailpurge"""

_config=None
"""_config contains the configuration as parsed from CONFIGFILE"""

def readConf():
    global _config
    _config={}
    handle = open(os.path.expanduser(CONFIGFILE),"r")
    data = handle.readlines()
    if len(data)<2:
        raise SystemExit("Please setup you configuration in %s!" % os.path.expanduser(CONFIGFILE))
    for line in data:
        param,value = line.split("=")
        if param.strip().lower()=="username":
            _config['username']=value.strip()
        if param.strip().lower()=="password":
            _config['password']=value.strip()
    try:
        _config['username']
    except:
        raise SystemExit("Please set a username in your config file")
    try:
        _config['password']
    except:
        raise SystemExit("Please set a password in your config file")


def connect():
    global _config
    M=imaplib.IMAP4_SSL("imap.gmail.com", 993)
    M.login(_config['username'],_config['password'])
    status, count = M.select("Inbox")
    status, data = M.fetch(count[0], "(UID BODY[TEXT])")

    print data[0][1]
    M.close()
    M.logout()

readConf()
connect()
