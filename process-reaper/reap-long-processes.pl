#!/usr/bin/env perl

$| = 1;

use strict;
use warnings;

use DBI;

my ($warn, $limit) = @ARGV;

(($warn || 0) > 0 && ($limit || 0) > 0) or
    die "Usage: reap-long-processes.pl <warn> <limit>
<warn> and <limit> are the amount of seconds before warning/killing processes
";

my $dbh = DBI->connect('dbi:Pg:dbname=postgres;host=127.0.0.1', 'postgres')
    or die 'Failed to connect';

while (1) {
    my $all_stuck = $dbh->selectall_arrayref(
        "SELECT procpid, current_query, query_start, now() - query_start > '$limit second'::interval AS kill
         FROM pg_stat_activity
         WHERE now() - query_start > '$warn second'::interval
           AND current_query != '<IDLE>'
         ORDER BY query_start ASC",
        { Slice => {} }
    ) or die 'Failed to find stuck queries';

    for my $stuck (@$all_stuck) {
        printf "%s WARNING Process %d has been running for over %s seconds\n",
            scalar(localtime), $stuck->{procpid}, $warn;
        printf "%s Query: %s\n", scalar(localtime), $stuck->{current_query};

        if ($stuck->{kill}) {
            printf "%s ERROR Process %d has been running for over %d seconds. Killing!\n",
                scalar(localtime), $stuck->{procpid}, $limit;
            printf "%s Query: %s\n", scalar(localtime), $stuck->{current_query};
        }
    }

    sleep 10;
};
