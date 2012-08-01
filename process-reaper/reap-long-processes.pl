#!/usr/bin/env perl

$| = 1;

use strict;
use warnings;

use DBI;

sub kill_proc 
{
    my ($dbh, $pid) = @_;

    $dbh->do("SELECT pg_terminate_backend(?)", undef, $pid);
}

my ($warn, $limit, $idle) = @ARGV;
my %warn_pids;

(($warn || 0) > 0 && ($limit || 0) > 0 && ($idle || 0) > 0) or
    die "Usage: reap-long-processes.pl <warn> <limit> <idle>
<warn> and <limit> are the amount of seconds before warning/killing processes
<idle> is the amount of time before killing idle transactions
";

my $dbh = DBI->connect('dbi:Pg:dbname=postgres;host=127.0.0.1', 'postgres')
    or die 'Failed to connect';

while (1) {
    my $all_stuck = $dbh->selectall_arrayref(
        "SELECT procpid, 
                current_query, 
                query_start, 
                now() - query_start > '$limit second'::interval AS kill,
                now() - query_start > '$idle second'::interval AS idle
         FROM pg_stat_activity
         WHERE now() - query_start > '$warn second'::interval
           AND current_query != '<IDLE>'
         ORDER BY query_start ASC",
        { Slice => {} }
    ) or die 'Failed to find stuck queries';

    my %cur_pids;
    for my $stuck (@$all_stuck) {

        $cur_pids{$stuck->{procpid}} = 1;
        if (!exists $warn_pids{$stuck->{procpid}}) {
            printf "%s WARNING Process %d has been running for over %s seconds\n",
                scalar(localtime), $stuck->{procpid}, $warn;
            printf "%s Query: %s\n", scalar(localtime), $stuck->{current_query};
            $warn_pids{$stuck->{procpid}} = $stuck->{query_start};
        }

        if ($stuck->{idle} && $stuck->{current_query} eq "<IDLE> in transaction") {
            printf "%s ERROR Idle in transaction process %d has been running for over %d seconds. Killing!\n",
                   scalar(localtime), $stuck->{procpid}, $idle;
            kill_proc($dbh, $stuck->{procpid});
        }

        if ($stuck->{kill}) {
            printf "%s ERROR Process %d has been running for over %d seconds. Killing!\n",
                scalar(localtime), $stuck->{procpid}, $limit;
            printf "%s Query: %s\n", scalar(localtime), $stuck->{current_query};
            kill_proc($dbh, $stuck->{procpid});
        }
    }

    my @done_pids;
    # clean up any pids that are no longer stuck
    for my $pid (keys %warn_pids)
    {
        if (!exists $cur_pids{$pid}) {
            push @done_pids, $pid;
            delete($warn_pids{$pid});
        }
    }

    if (scalar(keys %warn_pids)) {
        my @temp;
        for my $k (keys %warn_pids) {
            push @temp, sprintf "%d (%s)", $k, $warn_pids{$k};
        }
        printf "%s STATUS Processes stuck: ", scalar(localtime);
        printf join(",", @temp) . "\n";
    }

    if (scalar(@done_pids)) {
        printf "%s STATUS Processes no longer stuck: %s\n", scalar(localtime), join(",", @done_pids);
    }

    sleep 10;
};
