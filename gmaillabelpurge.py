#!/usr/bin/env python
# -*- coding: utf-8 -*-

# gmaillabelpurge
# Jürgen Geuter <tante@the-gay-bar.com>
# 2009
# Licensed under GPL-3

import imaplib
import os.path
import email
import datetime
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser
from optparse import OptionParser

# Python2's email lacks message_from_bytes(), but the data returned from
# imaplib's fetch() is actually a Python2 str
message_from_bytes = getattr(email, "message_from_bytes", email.message_from_string)

CONFIGFILE="~/.config/com.github.tante.gmaillabelpurge"
"""The filename and path of the config file, default is ~/.config/com.github.tante.gmaillabelpurge"""

def readConf():
    """Read the configuration file and die with a helpful error message
    when the file isn't valid for some reason."""
    _config={}
    config=ConfigParser()
    parsed_files = config.read(os.path.expanduser(CONFIGFILE))
    if not parsed_files:
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
            sectconf['labels'] = [label.strip() for label in config.get(section, "labels").split(",")]
        except:
            raise SystemExit("No labels defined for section %s" % section)
        try:
            sectconf['maxage'] = config.getint(section,"maxage")
        except:
            raise SystemExit("No maxage defined for section %s" % section)
        _config['sections'].append(sectconf)

    return _config

def purge(verbose=False,pretend=False,archive=False):
    """Purge the labels given in the config file."""

    _config = readConf()

    if archive:
        action = "archiving"
    else:
        action = "deleting"

    if pretend:
        action = "I would be " + action

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

    trash = "[%s]/%s" % (_config['folder'],_config['trashfolder'])

    # mark the current date so we can compare the mail ages
    today = datetime.date.today()
    if verbose:
        print("Current date: %s" % today.isoformat())
        print("Will use the Foldername [%s]" % _config['folder'])
        print("The Trash is in %s ." % trash)

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
                print("Checking label '%s'\n" % label)
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

            # don't do anything if we didn't find any old message at all...
            if not data[0]:
                continue

            msgsidx = b",".join(data[0].split())
            if verbose:
                # get the fetched headers for all the messages, but
                # only if we're going to print them out.
                status, data = server.fetch(msgsidx, "(UID BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")

                # data will have two hits each message, one with the
                # headers and an empty one for the body.
                for msg in data[::2]:
                    message = msg[0]

                    # get the UID out of the string in the format
                    # 1 (UID 13281 BODY[HEADER.FIELDS (SUBJECT FROM)] {97}
                    msguid = message[message.index(b"UID")+4:message.index(b" BODY")]

                    print("Loading message %s" % msguid)

                    headers = message_from_bytes(msg[1])

                    print("%s '%s' from '%s'" % (action, headers['subject'], headers['from']))

        if not pretend:
            try:
                if archive:
                    #mark the original mail deleted
                    typ, response = server.store(msgsidx, '+FLAGS', r'(\Deleted)')
                    #call expunge in order to really delete the messages marked
                    server.expunge()
                else:
                    #copy the mail to the trash
                    server.copy(msgsidx, trash)
            except Exception as e:
                print("There was a problem deleting messages from label '%s' (%s)" % (label,repr(e)))


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
