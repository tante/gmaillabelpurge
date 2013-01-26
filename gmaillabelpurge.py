#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gmaillabelpurge
# Jürgen Geuter <tante@the-gay-bar.com>
# 2009
# Licensed under GPL-3

import imaplib
import os.path
import email.utils
import datetime
import string
try:
	from configparser import ConfigParser
except ImportError:
	from ConfigParser import ConfigParser
from optparse import OptionParser

CONFIGFILE="~/.config/com.github.tante.gmaillabelpurge"
"""The filename and path of the config file, default is ~/.config/com.github.tante.gmaillabelpurge"""

_config=None
"""_config contains the configuration as parsed from CONFIGFILE"""

def readConf():
    """Read the configuration file and die with a helpful error message
    when the file isn't valid for some reason."""
    global _config
    _config={}
    config=ConfigParser()
    try:
        data = config.read(os.path.expanduser(CONFIGFILE))
    except:
        raise SystemExit("""Please set up the configuration in %s
Example:

[DEFAULT]
username=myuser@gmail.com
password=MYPASSWORD
[set1]
maxage=30
labels=LABEL1,LABEL2
[set2]
maxage=15
labels=LABEL4,LABEL5
        
""" % os.path.expanduser(CONFIGFILE))

    try:
        _config['username'] = config.get("DEFAULT","username")
    except:
        raise SystemExit("Please set a username in your config file")
    try:
        _config['password'] = config.get("DEFAULT","password") 
    except:
        raise SystemExit("Please set a password in your config file")

    _config['sections']=[]
    for section in config.sections():
        sectconf = {}
        sectconf['name']   = section
        try:
            sectconf['labels'] = map(str.strip,config.get(section,"labels").split(","))
        except:
            raise SystemExit("No labels defined for section %s" % section)
        try:
            sectconf['maxage'] = config.getint(section,"maxage")
        except:
            raise SystemExit("No maxage defined for section %s" % section)
        _config['sections'].append(sectconf)
    
def purge(verbose=False,pretend=False,archive=False):
    """Purge the labels given in the config file."""
    
    readConf()
    global _config
    
    server=imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        server.login(_config['username'],_config['password'])
    except:
        raise SystemExit("Couldn't connect to Gmail server, is the name/password combination correct?")

    # Seems that Locales also determine the "Root" Folder
    # so we try guessing it.
    # default is "Gmail" but for some locales (Germany and EN/GB)
    # it's "Google Mail"
    # We try looking up the "Spam" subfolder cause the actual rootfolder 
    # cannot be selected
    _config['folder'] = "Gmail"
    try:
        status, count = server.select("[%s]/Spam" % _config['folder'])
        if status=="NO":
            _config['folder'] = "Google Mail"
    except:
        pass

    # now find out how the TRASH is called
    # it's usually "Trash" but with a EN/GB Locale it seems to be "Bin"
    # we just try to select the /Bin Folder and if it doesn't exist
    # use the /Trash option as default
    _config['trashfolder'] = "Trash"
    try:
        status, count = server.select("[%s]/Bin" % _config['folder'])
        if status!="NO":
            _config['trashfolder'] = "Bin"
    except:
        pass
        
    # mark the current date so we can compare the mail ages
    today = datetime.date.today()
    if verbose:
        print("Current date: %s" % today.isoformat())
        print("Will use the Foldername [%s]" % _config['folder'])
        print("The Trash is in [%s]/%s ." % (_config['folder'], _config['trashfolder']))

    # iterate over the sections
    for section in _config['sections']:
        oldest = (today - datetime.timedelta(section['maxage'] +1)).strftime("%d-%b-%Y")
        if verbose:
            print("Doing section [%s]" % section)
            print("Maxage for this section: %s days." % section['maxage'])
            print("Searching for messages older than %s" % oldest)
        # go through the labels
        for label in section['labels']:
            if verbose:
                print("Checking label '%s'" % label)
                print
            try:
                status, count = server.select(label)
            except:
                raise SystemExit("The given label ('%s') doesn't seem to exist." % label)
            
            # get all messages
            try:
                status, data = server.search(None, '(SENTBEFORE {date})'.format(date=oldest))
            # might be too generic but gmail seems to allow select-ing unexisting labels
            except:
                print("The given label ('%s') doesn't seem to exist, there were at least problems with it. (Status: %s)" % (label,status))
                # break out of this iteration cause the label doesn't exist
                break
            
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
                status, data = server.uid("fetch", message, "(UID BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
                headers={}
                for header in data[0][1].split("\n"):
                    try:
                        name,value = header.strip().split(":",1)
                        headers[name.strip().lower()] = value.strip()
                    except:
                        # we just don't care what went wrong here
                        pass
                
                if pretend:
                    if archive:
                        print("I would archive '%s' from '%s'" % (headers.get('subject'),headers.get('from')))

                    else:
                        print("I would delete '%s' from '%s'" % (headers.get('subject'),headers.get('from')))

                else:
                    if archive:
                        print("Archiving '%s' from '%s'" % (headers.get('subject'),headers.get('from')))
                        try:
                            #mark the original mail deleted
                            typ, response = server.uid("store",message, '+FLAGS', r'(\Deleted)')
                            #call expunge in order to really delete the messages marked
                            server.expunge()
                        except Exception as e:
                            print("There was a problem deleting '%s' from '%s' (%s)" % (headers.get('subject'),headers.get('from'),repr(e)))

                    else:
                        print("Deleting '%s' from '%s'" % (headers.get('subject'),headers.get('from')))
                        try:
                            #copy the mail to the trash
                            server.uid("copy",message,"[%s]/%s" % (_config['folder'],_config['trashfolder']))
                            #mark the original mail deleted
                            typ, response = server.uid("store",message, '+FLAGS', r'(\Deleted)')
                            #call expunge in order to really delete the messages marked
                            server.expunge()
                        except Exception as e:
                            print("There was a problem deleting '%s' from '%s' (%s)" % (headers.get('subject'),headers.get('from'),repr(e)))


    # close the connection to the server
    try:
        server.close()
        server.logout()
    except:
        # we just do not care enough
        pass

if __name__=="__main__":
    parser = OptionParser()
    parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="print extra status messages to stdout")
    parser.add_option("-p", "--pretend",
                  action="store_true", dest="pretend", default=False,
                  help="just do a dry run and don't actually delete or move messages")
    parser.add_option("-a", "--archive",
                  action="store_true", dest="archive", default=False,
                  help="Instead of deleting archive messages.")

    (options,args) = parser.parse_args()
    
    # run purge()
    purge(options.verbose,options.pretend,options.archive)
