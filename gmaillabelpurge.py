#!/usr/bin/env python
# -*- coding: utf8 -*-

# gmaillabelpurge
# Jürgen Geuter <tante@the-gay-bar.com>
# 2009
# Licensed under GPL-3

import imaplib
import os.path
import email.utils
import datetime
from optparse import OptionParser

CONFIGFILE="~/.gmaillabelpurge"
"""The filename and path of the config file, default is ~/.gmailpurge"""

_config=None
"""_config contains the configuration as parsed from CONFIGFILE"""

def readConf():
    """Read the configuration file and die with a helpful error message
    when the file isn't valid for some reason."""
    global _config
    _config={}
    try:
        handle = open(os.path.expanduser(CONFIGFILE),"r")
        data = handle.readlines()
    except:
        raise SystemExit("""Please set up the configuration in %s
Example:

username=myuser@gmail.com
password=MYPASSWORD
maxage=30
labels=LABEL1,LABEL2
        
""" % os.path.expanduser(CONFIGFILE))
    if len(data)<2:
        raise SystemExit("Please setup you configuration in %s!" % os.path.expanduser(CONFIGFILE))
    for line in data:
        param,value = line.split("=")
        if param.strip().lower()=="username":
            _config['username']=value.strip()
        if param.strip().lower()=="password":
            _config['password']=value.strip()
        if param.strip().lower()=="maxage":
            _config['maxage']=int(value.strip())
        if param.strip().lower()=="labels":
            labels=[]
            for label in value.split(","):
                labels.append(label.strip())
            _config['labels']=labels

    try:
        _config['username']
    except:
        raise SystemExit("Please set a username in your config file")
    try:
        _config['password']
    except:
        raise SystemExit("Please set a password in your config file")
    try:
        _config['maxage']
    except:
        raise SystemExit("Please set the maximum age of mails to keep (via 'maxage')")
    try:
        _config['labels']
    except:
        raise SystemExit("Please set labels to be purged")

def purge(verbose=False):
    global _config
    server=imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        server.login(_config['username'],_config['password'])
    except:
        raise SystemExit("Couldn't connect to Gmail server, is the name/password combination correct?")
    
    # go through the labels
    for label in _config['labels']:
        if verbose:
            print("Checking label '%s'" % label)
    
        try:
            status, count = server.select(label)
        except:
            raise SystemExit("The given label ('%s') doesn't seem to exist." % label)
        
        # mark the current date so we can compare the mail ages
        now = datetime.datetime.now()
        if verbose:
            print("Current time: %s" % now.isoformat())
        
        # get all messages
        typ, data = server.search(None, 'ALL')
        
        # get the UIDs so we can properly delete more than one
        messages=[]
        for message in data[0].split():
            status, data = server.fetch(message, "UID")
            for msg in data:
                # we just want the real UID so we throw away the rest
                messages.append(msg[msg.index("UID")+4:-1])
        
        # now go through messages
        for message in messages:
            if verbose:
                print("Loading message %s" % message)
            status, data = server.uid("fetch",message, "(UID BODY[HEADER.FIELDS (SUBJECT FROM DATE)])")
            headers={}
            for header in data[0][1].split("\n"):
                try:
                    name,value = header.strip().split(":",1)
                    headers[name.strip().lower()] = value.strip()
                except:
                    # we just don't care what went wrong here
                    pass
        
            datetuple = list(email.utils.parsedate(headers['date']))
            # delete timezoneoffsets, might have to deal with that later
            del datetuple[7]
            del datetuple[7]
            
            maildate = datetime.datetime(*datetuple)
            delta=now-maildate
            
            #check whether we wanna delete the mail
            if delta.days>_config['maxage']:
                print("Deleting '%s' from '%s'" % (headers['subject'],headers['from'])) 
                try:
                    #copy the mail to the trash
                    server.uid("copy",message,"[Google Mail]/Trash")
                    #mark the original mail deleted
                    typ, response = server.uid("store",message, '+FLAGS', r'(\Deleted)')
                except Exception, e:
                    print("There was a problem deleting '%s' from '%s' (%s)" % (headers['subject'],headers['from'],repr(e)))        
            
            else:
                if verbose:
                    print("Not Deleting '%s' from '%s'" % (headers['subject'],headers['from'])) 
        
    # close the connection
    server.close()
    server.logout()

if __name__=="__main__":
    parser = OptionParser()
    parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="print extra status messages to stdout")
    (options,args) = parser.parse_args()
    
    # read configuration
    readConf()
    
    # run purge()
    purge(options.verbose)
