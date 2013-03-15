gmaillabelpurge - delete old messages from GMail labels
=======================================================

gmaillabelpurge allows you to delete all messages from given gmail
labels when they reach a certain age.

it uses GMail's IMAP interface, which means you have to enable IMAP on
your account, and speaks [Google's IMAP
extensions](https://developers.google.com/google-apps/gmail/imap_extensions).

At the time of writing, we have two scripts: one written in Python,
that only requires its standard library, and a slightly faster, version in Perl
which requires a few dependencies:

 - Config::IniFiles;
 - Mail::IMAPClient;
 - IO::Socket::SSL;
 - DateTime.

The Python version is compatible with both Python2 and Python3.

How to use
----------

Open the file `~/.config/com.github.tante.gmaillabelpurge` with your
favourite text editor. Take this example as a template for what to put
in:

    [DEFAULT]
    username=myuser@gmail.com
    password=MYPASSWORD
    [30days]
    maxage=30
    labels=LABEL1,LABEL2
    [aaaa]
    maxage=15
    labels=LABEL3,LABEL4

The section `DEFAULT` has to exist, and contains `username` (put your
full gmail username here) and `password` (your password).

After that you can add as many `[sections]` as you want, calling them
however you want.

For each of them, `maxage` is the maximum age in days for a mail in
order for it not to be moved to the trash folder. All mail sent
`maxage+1` days ago is then deleted.  If you enter `-1` it will move
all your mail in that given label to the trash.

Finally `labels` is a comma-delimited list of the labels you want
purged.

To run the scripts, you can either call them directly, if executable,
or as `python gmaillabelpurge.py` and `perl
gmaillabelpurge.pl`.

Both scripts respond to the `-h` option to get help on the parameters,
and use `-v` or `--verbose` for printing more runtime details, and
`-p` or `--pretend` to just run a dry-run before actually executing
any operation.

Contacts
--------

If anything breaks, you find bugs, or have feature requests you can
contact us.

For the Python script:
Mail: <tante@the-gay-bar.com>
jabber: tante@jabber.org
GitHub: http://github.com/tante/gmaillabelpurge

For the Perl script:
Mail: <flameeyes@flameeyes.eu>
GitHub: https://github.com/Flameeyes/gmaillabelpurge
