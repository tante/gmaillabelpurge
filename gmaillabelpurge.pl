#!/usr/bin/perl -wT
# -*- perl -*-

=head1 NAME

gmaillabelpurge - delete old messages from GMail labels

=head1 SYNOPSIS

gmaillabelpurge.pl [--help] [--verbose] [--pretend] [--archive]

=head1 OPTIONS

=over 8

=item B<--verbose>, B<-v>

Print status messages when selecting labels, and include a list of the
messages that will be deleted, or archived.

=item B<--pretend>, B<-p>

Do not actually delete or archive messages, simply print which
messages would be deleted.

=item B<--archive>, B<-a>

Do not delete messages, simply archive them by removing the label they
are found under.

=back

=head1 AUTHORS

Copyright © 2009-2013 Jürgen Geuter <tante@the-gay-bar.com>
Copyright © 2012-2013 Diego Elio Pettenò <flameeyes@flameeyes.eu>

=head1 LICENSE

Licensed under GPL-3

=cut

use strict;
use warnings;

use Getopt::Long;
use Pod::Usage;
use Config::IniFiles;
use Mail::IMAPClient;
use IO::Socket::SSL;
use DateTime;

# Use globbing to expand the user's home directory.
my $CONFIGFILE = <~/.config/com.github.tante.gmaillabelpurge>;

my ($help, $verbose, $pretend, $archive);

GetOptions('help|h'    => \$help,
	   'verbose|v' => \$verbose,
	   'pretend|p' => \$pretend,
	   'archive|a' => \$archive
    ) or pod2usage(1);

pod2usage(1) if $help;

my $action = ($pretend ? "I would be " : "") . ($archive ? "archiving" : "deleting");

my $cfg = Config::IniFiles->new( -file => $CONFIGFILE );

my @sections = grep($_ ne "DEFAULT", $cfg->Sections);

my $socket = IO::Socket::SSL->new(
    PeerAddr => "imap.gmail.com",
    PeerPort => "993",
    SSL_verify_mode => SSL_VERIFY_PEER,
    SSL_ca_path => "/etc/ssl/certs",
    ) or die "socket(): $@";

my $server = Mail::IMAPClient->new(
    Socket => $socket,
    User   => $cfg->val('DEFAULT', 'username'),
    Password => $cfg->val('DEFAULT', 'password'),
    Peek   => 1,
    Ranges => 1,
    ) or die "client: $@";

# While the XLIST method is deprecated at this point (replaced by
# RFC6154's Special-Use Extension), Mail::IMAPClient up to 3.31 does
# not support it, while GMail still support XLIST for compatibility.
my $trashfolder = $server->xlist_folders->{Trash} or
    die "Unable to identify trash folder";

if ( $verbose ) {
    print
	"Using ", $trashfolder, " as trash folder.\n",
	"Current date: ", DateTime->today->strftime("%d-%b-%Y"), "\n";
}

foreach my $section (@sections) {
    my $maxage = $cfg->val($section, "maxage", -1);
    my @labels = split(/,/, $cfg->val($section, "labels", ""));
    if ( $maxage == "-1" ) {
	print STDERR "No maxage defined for section ", $section, "\n";
	next;
    }
    if ( !scalar(@labels) ) {
	print STDERR "No labels defined for section ", $section, "\n";
	next;
    }

    my $oldest = DateTime->today->subtract( days => $maxage+1 )->strftime("%d-%b-%Y");
    if ( $verbose ) {
	print
	    "Doing section [", $section, "]\n",
	    "Maxage for this section: ", $maxage, " days\n",
	    "Searching for messages older than ", $oldest, "\n";
    }

    foreach my $label (@labels) {
	if ( $verbose ) {
	    print
		"Checking label '", $label, "'\n";
	}

	if ( !$server->select($label) ) {
	    print STDERR "Unable to select label '", $label, "': ", $@, "\n";
	    next;
	}

	my $msgs = $server->sentbefore($oldest);
	if ( $@ ) {
	    print STDERR "Unable to search in '", $label, "': ", $@, "\n";
	    next;
	}

	# do not enter the parsing/moving if there are no messages in
	# the search result, just output a note in that case.
	if ( scalar(@$msgs) > 0 ) {
	    if ( $verbose ) {
		# get the fetched headers for all the messages, but
		# only if we're going to print them out.
		my $messages = $server->parse_headers($msgs, "Subject", "From");

		while (my ($uid, $headers) = each $messages) {
		    printf
			"%s '%s' from '%s'\n",
			$action,
			$headers->{Subject}[0],
			$headers->{From}[0];
		}
	    }

	    # act only if we're not doing a dry-run
	    unless ( $pretend ) {
		if ( $archive ) {
		    $server->delete_message($msgs);
		    if ( $@ ) {
			print STDERR "Unable to archive messages from '", $label, "': $@\n";
		    }
		    # Even if the expunge fail it's not like we can do
		    # anything about it, so just run it through.
		    $server->expunge();
		} else {
		    $server->copy($trashfolder, $msgs);
		    if ( $@ ) {
			print STDERR "Unable to move messages from '", $label, "' to trash: $@\n";
		    }
		}
	    }
	} else {
	    if ( $verbose ) {
		print "$action no message on '$label'\n";
	    }
	}
    }
}

$server->logout();
