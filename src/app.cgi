#!/usr/bin/perl -w
#@HDR@	$Id: app.cgi,v 1.1 2020/08/12 21:23:06 chris Exp $
#@HDR@		Copyright 2020-2024 by
#@HDR@		Christopher Caldwell/Brightsands
#@HDR@		P.O. Box 401, Bailey Island, ME 04003
#@HDR@		All Rights Reserved
#@HDR@
#@HDR@	This software comprises unpublished confidential information
#@HDR@	of Brightsands and may not be used, copied or made available
#@HDR@	to anyone, except in accordance with the license under which
#@HDR@	it is furnished.
########################################################################
#	app.cgi
#
#	A web application based around Weight Watchers points.
#
#	2024-04-19 - c.m.caldwell@alumni.unh.edu - Created
########################################################################

use strict;
use lib "/usr/local/lib/perl";
use cpi_file qw(cleanup fatal write_file);
use cpi_time qw(timestr);
use cpi_cgi qw(show_vars);
use cpi_user qw(logout_select users_in_group);
use cpi_setup qw(setup);
use cpi_translate qw(trans xprint);
use cpi_db qw(DBadd DBget DBpop DBput DBwrite);
use cpi_template qw(template);
use cpi_escape qw(perl_esc);
use cpi_hash_to_string qw(hash_to_string);


my $PRETTYJS = ",";
#$PRETTYJS = ",\n\t";

my $FORMNAME = "form";

&setup(stderr=>"ww",payment_system=>1,preset_language=>"en");

$_ = $cpi_vars::BASEDIR; # Eliminate only used once error
my $JAVASCRIPT = "$cpi_vars::BASEDIR/lib/$cpi_vars::PROG.js";

my @HEADER_COLORS	= ( "#c0c0c0", "#c0ffff" );
my @DATA_COLORS		= ( "#ffffc0", "#c0ffc0" );
my @TOTAL_COLORS	= ( "#ffc0ff", "#c0c0ff" );
my @TYPE_COLORS		= ( "#ffc0c0", "#c0c0c0" );
my @GRAPH_COLORS	= ( "#d8d8d8", "#ffffff" );

$cpi_vars::TODAY		= `date +%Y%m%d`;	chomp($cpi_vars::TODAY);

my $BANK_DAYS_BACK = 7;
my $WPARTS = 30;

my $NUM_MOST_COMMON = 15;

my $do_banking = 0;

my %WEIGHT_TO_POINT_RANGES =
    (
    150,	"18-23",
    175,	"20-25",
    200,	"22-27",
    225,	"24-29",
    250,	"26-31",
    275,	"28-33",
    300,	"29-34",
    325,	"30-35",
    350,	"31-36",
    999,	"32-37"
    );

my @DAY_NAMES = ("Sun","Mon","Tue","Wed","Thu","Fri","Sat");
my @MONTH_NAMES = (
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December");

my @timetypes
    =("XL(Morning)","XL(Noon)","XL(Evening)","XL(Exercize)");

my %PRETTY_REQUIREMENTS =
    (
    "milk"	=> "XL(Milk)",
    "water"	=> "XL(Water)",
    "fruveg"	=> "XL(Fruits and Veggies)",
    );

my $restaurant_href = "http://www.healthdiscovery.net/restaurants";

#########################################################################
#	Return list of files in directory.				#
#########################################################################
sub slurp_dir
    {
    opendir( DFD, $_[0] ) || &fatal("Cannot opendir($_[0]):  $!");
    my( @dirlist ) = grep( ! /^\./, readdir(DFD) );
    closedir( DFD );
    return sort @dirlist;
    }

#########################################################################
#       Use binary search to convert min,hour,day,month,year to         #
#       seconds from the epoch.                                         #
#########################################################################
sub str_to_time
    {
    #my( @alist ) = @_;
    my( $t ) = @_;
    my(@alist)=(10,10,10,substr($t,6,2)+0,substr($t,4,2)-1,substr($t,0,4)%100);
    $alist[5] += 100 if( $alist[5] < 90 );	# Y2K hack
    my( $base ) = 0;
    my( $bit ) = 0x40000000;
    my( $i, $res );
    while( $bit )
        {
        my $try = $base | $bit;
        my @compare = localtime( $try );
        for( $i=5; $i>=0; $i-- )
            {
            last if( $res = ( $alist[$i] <=> $compare[$i] ) );
            }
        if( $res >= 0 )
            {
            $base = $try;
            last if( $res == 0 );
            }
        $bit >>= 1;
        }
    return $base;
    }

#########################################################################
#	Return day of week from date.					#
#########################################################################
sub day_from_date
    {
    return (localtime( &str_to_time($_[0]) ) )[ 6 ];
    }

#########################################################################
#	Print a "bar" of specified size and color.  If color code	#
#	is of num,num form, print a character in the bar.		#
#	We use this to show exercize.					#
#########################################################################
sub print_color
    {
    my( $num, $colcode ) = @_;
    my @toprint;
    if( $num > 0 )
        {
	my( $bgcolor, $fgcolor, $chr );
	if( $colcode =~ /(.*),(.*)/ )
	    { $bgcolor=$1; $fgcolor=$2; $chr="-"; }
	else
	    { $bgcolor=$colcode; $fgcolor=$colcode; $chr=" "; }
	push(@toprint,
	    "<span style=\"background:$bgcolor\"><font color=$fgcolor>",
	    ( $chr x $num ),
	    "</font></span>" );
	}
    return join("",@toprint);
    }

#########################################################################
#	Print a string making sure that spaces take up correct amount	#
#	of space in HTML.						#
#########################################################################
sub fixed
    {
    my( $fmt, @args ) = @_;
    $_ = sprintf( $fmt, @args );
    s/ /\&nbsp;/g;
    return $_;
    }

#########################################################################
#	Return minimum and maximum values from an array.		#
#########################################################################
sub minmax
    {
    my( $minv, $maxv, @args ) = @_;
    foreach $_ ( @args )
        {
	$minv = $_ if( $_ < $minv );
	$maxv = $_ if( $_ > $maxv );
	}
    #print "minmax($minv,$maxv) from (".join(",",@_).")\n";
    return ( $minv, $maxv );
    }

#########################################################################
#	Does not assume there are <input type= vars in form, but	#
#	simply puts them in the querystring.  Not compatible with	#
#	method=post.							#
#########################################################################
sub sfget
    {
    my $href="$ENV{SCRIPT_NAME}?SID=$cpi_vars::SID&USER=$cpi_vars::USER";
    my( @vals ) = @_;
    my @toprint = ( "window.location=\"$href" );
    unshift( @vals, "func" );
    while ( defined($_ = shift(@vals) ) )
        { push( @toprint, '&', $_, "=", shift(@vals) ); }
    push( @toprint, "\";" );
    return join("",@toprint);
    }

#########################################################################
#	Assumes variables are specified in form.  Compatible with	#
#	method=post.							#
#########################################################################
sub sfpost
    {
    return join("", 'submit_func("', join('","',@_), '");');
    }

#sub sfcall { return &sfget(@_); }
sub sfcall { return &sfpost(@_); }

#########################################################################
#	Returns a traditional link string.				#
#########################################################################
sub sflink
    {
    my( $txt, @vals ) = @_;
    return join("",
	"<a href='javascript:",
	&sfcall(@vals),
	"'>", $txt, "</a>" );
    }

#########################################################################
#	Returns a traditional button string.				#
#########################################################################
sub sfbutton
    {
    my( $txt, @vals ) = @_;
    return join("",
	#"<input type=button help='button-$vals[0]' onClick='",
	"<input type=button",
	" help='button-$vals[0]'",
	" onClick='", &sfcall(@vals), "'",
	" value='", $txt, "'>");
    }

#########################################################################
#	Print consistant footer at bottom of page.			#
#########################################################################
sub footer
    {
    &xprint(
	"<p><center><table width=60% border=4 $cpi_vars::TABLE_TAGS><tr>\n",
	"<th>",&sfbutton("XL(Today)","today"),"</th>",
	"<th>",&sfbutton("XL(Directory)","dir"),"</th>",
	"<th>",&sfbutton("XL(Graph)","graph","ndays",1),"</th>",
	"<th>",&sfbutton("XL(Week graph)","graph","ndays",7),"</th>",
	"<th>",&sfbutton("XL(Total report)","fullreport"),"</th>",
#	"<th><a href=$restaurant_href target=restaurants>XL(Restaurants index)</a></th>",
        "<th>",&logout_select("form"),"</th>",
	"</tr></table></center></form></body>");
    &cleanup(0);
    }

#########################################################################
#########################################################################
sub sum_form
    {
    my( $curday, $l4 ) = @_;
    my( $sum ) = 0;
    my $ev;
    foreach $ev ( split(/,/,&DBget("users",$cpi_vars::USER,"days",$curday,"events")) )
        {
	if( $ev =~ /(\d+)\|(\d+)/ )
	    {
	    if( ($2!=3) ^ ($l4 eq "exercize") )
	        {
		if( &DBget("text",$1) =~ /(.*)\|(.*)/ )
		    {
		    $sum += $2;
		    }
		}
	    }
	}
    return $sum;
    }

#########################################################################
#	Return standardized HTML for the top of the page.		#
#########################################################################
sub top_of_page
    {
    my ( $title ) = @_;
    return <<EOF;
<title>$title</title>
<script>
function submit_func()
    {
    with ( window.document )
        {
        var i=0;
	form.func.value = arguments[i++];
	while( i < arguments.length )
	    {
	    var name = arguments[i++];
	    form[name].value = arguments[i++];
	    }
	form.submit();
	}
    }
</script>
</head><body $cpi_vars::BODY_TAGS>
<form name=form method=post>
<input type=hidden name=SID value='$cpi_vars::SID'>
<input type=hidden name=USER value='$cpi_vars::USER'>
<input type=hidden name=ndays>
<input type=hidden name=day>
<input type=hidden name=weekdays>
<input type=hidden name=user>
<input type=hidden name=func>
$cpi_vars::HELP_IFRAME
EOF
    }
#########################################################################
#	Print out a graph of all days and points.			#
#########################################################################
sub graph_page
    {
    my( $sample_size ) = @_;
    my @toprint = (&top_of_page("XL(Overall performance against goals)") );
    my @daylist = &DBget("users",$cpi_vars::USER,"days");
    my $maxp = 0;
    my $minp = 1000000;
    my $maxw = 0;
    my $minw = 1000000;
    my ( $i, $di );
    my %nsamples = ();
    my %comment = ();
    my %points = ();
    my %epoints = ();
    my %weight = ();
    my %ming = ();
    my %maxg = ();
    my ( $p, $ep, $w, $mingt, $maxgt, $wdiff, $epdiff, $istart, $pdiff );
    my( $lastcolor, $numincolor, $pind, $colcode );
    my( $colind, $bgcolor );
    my( @colors, @numincolors );
    my( $ci, $gw );
    my %paidtable = ();
    my $paidlen = 0;

    my( %daytable ) = ();

    for( $i=0; $daylist[$i]; $i++ )
        {
	my($d) = $daylist[$i];
	$di = int($i/$sample_size);
	$nsamples{$di}++;
	$daytable{$di} = 0 if( ! defined($daytable{$di}) );
	$daytable{ "$di-$daytable{$di}" } = $d;
	$daytable{$di}++;
	my $com = &DBget("users",$cpi_vars::USER,"days",$d,"comment");
	if( $com ne "" )
	    {
	    $comment{$di} .= "; " if( $comment{$di} );
	    $comment{$di} .= &trans($com);
	    }
	$p = &sum_form( $d, "food" );
	$ep = -&sum_form( $d, "exercize" );
	$points{$di} += $p;
	$epoints{$di} += $ep;
	$w = &calculate_weight( $d );
	$weight{$di} += $w;
	($mingt,$maxgt) = &calculate_range($w);
	$ming{$di} += $mingt;
	$maxg{$di} += $maxgt;
	($minp,$maxp) = &minmax($minp,$maxp,$mingt,$maxgt);
	my $pi;
	foreach $pi ( &DBget("users",$cpi_vars::USER,"days",$d,"payments") )
	    {
	    my $payment =
		&DBget("users",$cpi_vars::USER,"days",$d,"payments",$pi,"paid");
	    my $note =
		&DBget("users",$cpi_vars::USER,"days",$d,"payments",$pi,"note");
	    $paidtable{$di} .= ", " if( $paidtable{$di} ne "" );
	    $paidtable{$di} .= "${note}\$$payment";
	    }
	}

    for( $i=0; $i<=$di; $i++ )
        {
	$p = int( $points{$i} / $nsamples{$i} );
	$epdiff = int($epoints{$i}/$nsamples{$i}+0.5);
	$ep = $p - $epdiff;
	($minp,$maxp) = &minmax($minp,$maxp,$p,$ep);
	$w = $weight{$i} / $nsamples{$i};
	($minw,$maxw) = &minmax( $minw, $maxw, $w );
	$_ = length($paidtable{$i});
	$paidlen = $_ if( $_ > $paidlen );
	}

    $wdiff = $maxw - $minw;
    $wdiff = 1 if( $wdiff <= 0 );

    $pdiff = $maxp - $minp;
    $pdiff = 1 if( $pdiff <= 0 );

    push( @toprint, "<table cellpadding=0 cellspacing=0>" );
    if( $daytable{"0"} <= 1 )
        { push( @toprint, "<th>XL(Date)</th>" ); }
    else
        { push( @toprint, "<th>XL(Dates)</th>" ); }
    push( @toprint, <<EOF );
<th>XL(Points)</th>
<th>XL(Permissible points)</th>
<th>XL(Point distribution)</th>
<th colspan=2>XL(Weight)</th>
EOF
    push(@toprint,"<th>XL(Payments)</th>") if( $paidlen > 0 );
    push(@toprint,"<th align=left>XL(Comments)</th></tr>\n");

    $colind=0;
    for( $i=0; $i<=$di; $i++ )
        {
	push(@toprint, "<tr><td nowrap>" );
	if( $sample_size <= 1 )
	    {
	    $colind= 1 - $colind if( &day_from_date( $daytable{"$i-0"} ) == 0 );
	    }
	$bgcolor = $GRAPH_COLORS[ $colind ];
	$p = int($points{$i}/$nsamples{$i}+0.5);
	$epdiff = int($epoints{$i}/$nsamples{$i}+0.5);
	$ep = $p - $epdiff;
	$w = $weight{$i} / $nsamples{$i};
	$ming{$i} = int($ming{$i} / $nsamples{$i} + 0.5);
	$maxg{$i} = int($maxg{$i} / $nsamples{$i} + 0.5);
	$istart = $daytable{"$i-0"};
	if( ($_ = $daytable{"$i"}) <= 1 )
	    {
	    push( @toprint, &sflink($istart,"show","day",$istart) );
	    }
	else
	    {
	    my( @dayinds ) = ();
	    my( $dtind );
	    $_ = $daytable{$i} - 1;
	    foreach $dtind ( 0..$_ )
		{
		push( @dayinds, $daytable{"$i-$dtind"} );
		}
	    push( @toprint,
		&sflink(
		    "$istart-".$daytable{"$i-$_"},
		    "show",
		    "weekdays", join(",",@dayinds) ) );
	    }
	push(@toprint, "</td><td nowrap align=right>");
	if( $epoints{$i} == 0 )
	    { push(@toprint, &fixed("%2d",$p) ); }
	else
	    { push(@toprint, &fixed("%2d-%-2d", $p, $epdiff ) ); }
	push(@toprint, "</td><td nowrap align=right>");
	push(@toprint, &fixed( "%2d-%2d", $ming{$i}, $maxg{$i} ) );
	$lastcolor = "";
	$numincolor = 0;
	@colors = ();
	@numincolors = ();
	push( @toprint, "</td><td nowrap><pre>" );
	for( $pind=$minp; $pind<=$maxp; $pind++ )
	    {
	    if( $pind >= $p && $pind < $ming{$i} )
	        { $colcode = "blue"; }
	    elsif( $pind <= $p && $pind > $maxg{$i} )
	        { $colcode = "red"; }
	    elsif( ($pind >= $p) && ($pind <= $p) )
	        { $colcode = "#80ff80"; }
	    elsif( $pind >= $ming{$i} && $pind <= $maxg{$i} )
	        { $colcode = "green"; }
	    else
	        { $colcode = $bgcolor; }

	    $colcode .= ",black" if( $pind >= $ep && $pind < $p );

	    if( $colcode eq $lastcolor )
	        { $numincolor++; }
	    else
		{
		if( $numincolor > 0 )
		    {
		    push( @colors, $lastcolor );
		    push( @numincolors, $numincolor ) ;
		    }
		$numincolor = 1;
		$lastcolor = $colcode;
		}
	    }
	push( @colors, $lastcolor );
	push( @numincolors, $numincolor );

	for( $ci=0; $colors[$ci] ne ""; $ci++ )
	    {
	    push(@toprint, &print_color( $numincolors[$ci], $colors[$ci]));
	    }

	$gw = int( $WPARTS*($w-$minw)/$wdiff ) + 1;
	push(@toprint, "</td><td nowrap>");
	push(@toprint, &fixed( "%7.1f ", $w, $gw ));
	push(@toprint, "</td><td nowrap><pre>");
	push(@toprint, &print_color( $gw, $bgcolor ));
	push(@toprint, &print_color( 1, "black" ));
	$_ = $WPARTS + 1 - $gw;
	push(@toprint, &print_color( $_, $bgcolor ));
	push(@toprint, "</pre></td>");
	push(@toprint, "<td nowrap>",
	    &fixed(" %-${paidlen}s",$paidtable{$i}),"</td>")
	    if( $paidlen > 0 );
	push(@toprint, "<td nowrap>".$comment{$i}."</td></tr>" );
	}
    push( @toprint, "</table>" );
    &xprint( @toprint );
    }

#########################################################################
#	Print out a list of all days to allow user to modify a day.	#
#########################################################################
sub dir_page
    {
    my @daylist = &DBget("users",$cpi_vars::USER,"days");
    my $curdayind = 0;
    my $lastyearmon = -1;
    my $needtoprintyearmon = 0;
    my( $ind, $day, $yearmon, $yearmonstr, $colind, $dayind, $bind, $bday );
    my( $weekdays );
    my @ndaylist = ();
    my @toprint =
        (
	&top_of_page("XL(Select date or report for [[$cpi_vars::FULLNAME]])"),
	"<center><table border=1 cellspacing=1 cellpadding=1 $cpi_vars::TABLE_TAGS>\n<tr>");
    push( @daylist, $cpi_vars::TODAY ) if( $daylist[$#daylist] ne $cpi_vars::TODAY );
    for( $_=0; $_<7; $_++ )
        { push(@toprint, "<th>$DAY_NAMES[$_]</th>"); }
    push( @toprint, "</tr>\n" );
    #for( $ind=0; $daylist[$ind] ne ""; $ind++ )
    for( $ind=0; $ind <= $#daylist; $ind++ )
        {
	$day = $daylist[$ind];
	$yearmon = int($day/100);
	if( $yearmon != $lastyearmon )
	    {
	    $yearmonstr = sprintf("%s %d",
	        $MONTH_NAMES[$yearmon%100-1],
		int($yearmon/100));
	    $colind = $DATA_COLORS[ $yearmon % 2 ];
	    $needtoprintyearmon = 1;
	    $lastyearmon = $yearmon;
	    }
	$dayind = &day_from_date( $day );
	while( 1 )
	    {
	    if( $curdayind > 6 )
		{
		push(@toprint, "</tr>\n");
		$curdayind = 0;
		}
	    push(@toprint, "<tr>") if( $curdayind == 0 );
	    last if( $curdayind++ == $dayind );
	    push(@toprint, "<td>&nbsp;</td>");
	    }
	$bind = $ind - 6;
	$bind = 0 if( $bind < 0 );
	$bday = $daylist[$bind];
	@ndaylist = ();
	while( $bind <= $ind )
	    {
	    push( @ndaylist, $daylist[$bind++] );
	    }
	$weekdays = join(",",@ndaylist);
	push(@toprint,
	    "<td bgcolor=$colind>",
	    &sflink($bday,"show","weekdays",$weekdays),
	    "-",
	    &sflink($day,"show","day",$day),
	    "</td>");
	if( $curdayind == 7 )
	    {
	    push(@toprint, "<td>$yearmonstr</td>") if( $needtoprintyearmon );
	    $needtoprintyearmon = 0;
	    }
	$lastyearmon = $yearmon;
	}
    push(@toprint, "</tr>\n") if( $curdayind <= 6 );
    push(@toprint, "</table>");
    &xprint(@toprint);
    }

#########################################################################
#########################################################################
sub goal_range
    {
    my( $user, $day ) = @_;
    my( $curweight ) = &calculate_weight($day);
    my( $i );
    my @weights = sort { $a <=> $b } keys %WEIGHT_TO_POINT_RANGES;
    my $w = 0;
    for( $i=0; $weights[$i]; $i++ )
        {
	last if( $curweight >= $w && $curweight < $weights[$i] );
	$w = $weights[$i];
	}
    my( $goalweight ) = &DBget("users",$user,"goalweight");
    if( $WEIGHT_TO_POINT_RANGES{$w} =~ /(.*)-(.*)/ )
        {
        my( $bot, $top ) = ( $1, $2 );
        return ($bot+0,$top+0) if( $goalweight < $curweight-5.0 );
        return ($bot+2,$top+2) if( $goalweight < $curweight );
	return ($bot+6,$top+6) if( $goalweight > $curweight+5.0 );
        return ($bot+4,$top+4) if( $goalweight >= $curweight );
	}
    }

#########################################################################
#	Print out a week's worth of days (in pretty colors).		#
#########################################################################
my $page_counter = 0;
sub week_report
    {
    my( $needheader, @daylist ) = @_;
    my %TBL = ();
    my( $d, $k, $i, $nwidth, $colind, $col );
    my @toprint;
    if( $needheader )
        {
	push(@toprint, &top_of_page("XL(Information for [[$cpi_vars::FULLNAME]])"));
	}
    if( $page_counter++ <= 0 )
        {
	push(@toprint, "<center><h1>XL(Information of [[$cpi_vars::FULLNAME]])</h1>\n");
	}
    else
        {
	push(@toprint, "<div style=\"page-break-before: always\">&nbsp;</div>");
	}
    push(@toprint, "<table border=0><tr bgcolor=#d0d0d0>\n");
    $nwidth = ($#daylist + 1) * 2;
    $colind = 0;
    my %timetable = ();
    my %rowspertime = ();
    foreach $d ( @daylist )
        {
	$col = $HEADER_COLORS[$colind++ %2];
	push( @toprint,
	    "<th colspan=2 bgcolor=$col>",
	    $DAY_NAMES[ &day_from_date($d) ] . "<br>",
	    &sflink($d,"show","day",$d),
	    "</th>");
	my $cats = &DBget("users",$cpi_vars::USER,"days",$d,"cats");
	($TBL{"milk-$d"},$TBL{"water-$d"},$TBL{"fruveg-$d"}) = split(/,/,$cats);
	my $ev;
	foreach $ev ( split(/,/,&DBget("users",$cpi_vars::USER,"days",$d,"events")) )
	    {
	    if( $ev =~ /(\d+)\|(\d+)/ )
	        {
		push( @{$timetable{$2}{$d}}, $1 );
		$_ = scalar( @{$timetable{$2}{$d}} );
		$rowspertime{$2} = $_
		    if( !defined($rowspertime{$2}) || ($_ > $rowspertime{$2}) );
		}
	    }
	}
    
    my $mealtime;
    foreach $mealtime ( 0 .. 3 )
	{
	push(@toprint, "<tr><th colspan=$nwidth bgcolor=ffc0c0>",
	    $timetypes[$mealtime]."</th></tr>\n" );
	#foreach $i ( @{ $MEAL_RANGES{$mealtime} } )
	for( $i=0; $i<$rowspertime{$mealtime}; $i++ )
	    {
	    push(@toprint, "<tr>");
	    $colind = 0;
	    foreach $d ( @daylist )
		{
		my $ind = $timetable{$mealtime}{$d}[$i];
		my( $nf, $np );
		if( $ind ne "" )
		    {
		    my $ans = &DBget("text",$ind);
		    if( $ans =~ /^(.*)\|([\d\.\-]*)$/ )
		       {
		       $np = $2;
		       $nf = &trans($1);
		       }
		    }
		$TBL{"ctotal-$d"} += $np;
		$col = $DATA_COLORS[$colind++ %2];
		$nf = "&nbsp;" if( $nf eq "" );
		push(@toprint, "<td align=right bgcolor=$col>$nf</td>");
		$np = "&nbsp;" if( $np eq "" );
		push(@toprint, "<td align=right bgcolor=$col>$np</td>\n");
		}
	    push(@toprint, "</tr>\n");
	    }
	}
    
    my $thing;
    my @thinglist = ("Total", "Goal", "Difference", keys %PRETTY_REQUIREMENTS);
    push( @thinglist, "Previously banked", "Banked" ) if( $do_banking );
    push( @thinglist, "Weight" );
    foreach $thing ( @thinglist )
	{
	push(@toprint, "<tr>");
	my $label = "XL($thing)";
	$colind = 0;
	foreach $d ( @daylist )
	    {
	    my $res;
	    $col = $TOTAL_COLORS[$colind++ %2];
	    if( $thing eq "Total" )
	        { $res = $TBL{"ctotal-$d"}; }
	    elsif( $thing eq "Goal" )
	        {
		my( $ming, $maxg ) = &goal_range( $cpi_vars::USER, $d );
		$res = "$ming-$maxg";
		$TBL{"maxg-$d"} = $maxg;
		}
	    elsif( $thing eq "Difference" )
	        {
		$res = $TBL{"currentdiff-$d"}=$TBL{"maxg-$d"}-$TBL{"ctotal-$d"};
		}
	    elsif( $thing eq "Previously banked" )
	        {
		$res = $TBL{"previouslybanked-$d"} = &calculate_bank($d);
		}
	    elsif( $thing eq "Banked" )
		{
		$res = $TBL{"tobank-$d"} = $TBL{"currentdiff-$d"}
		    + $TBL{"previouslybanked-$d"};
		}
	    elsif( $thing eq "Weight" )
	        {
		$res = &calculate_weight( $d );
		$label = "lbs";
		}
	    else
	        {
	        $col = $TYPE_COLORS[$colind++ %2];
		$label = "$PRETTY_REQUIREMENTS{$thing}";
		$res = $TBL{"$thing-$d"};
		}
	    push(@toprint,
		"<td align=right bgcolor=$col>$label</td>",
		"<td align=right bgcolor=$col>$res</td>");
	    }
	push(@toprint, "</tr>");
	}
    #push(@toprint, "<tr><th colspan=$nwidth><br></th></tr>");
    push(@toprint, "</table></center>\n");
    return join("",@toprint);
    }

#########################################################################
#	Print out all weeks.						#
#########################################################################
sub full_report
    {
    my(@daylist) = &DBget("users",$cpi_vars::USER,"days");
    my( @ndaylist ) = ();
    my $ind;
    my(@toprint) =
	(
	"<head>",
	# "<style media=\"print\" type=\"text/css\">\n",
	# "hr.newpage {page-break-before:always}\n",
	# "</style><style media=\"screen\" type=\"text/css\">",
	# "hr.newpage {height:10px;color:#111;background-color:#111}\n</style>",
	&top_of_page("XL(Full report for $cpi_vars::FULLNAME)")
	);
    push( @daylist, $cpi_vars::TODAY ) if( $daylist[$#daylist] ne $cpi_vars::TODAY );
    for( $ind=0; $daylist[$ind] ne ""; $ind++ )
        {
	my $day = $daylist[$ind];
	push( @ndaylist, $day );
	if( &day_from_date( $day ) == 6 )
	    {
	    push( @toprint, &week_report( 0, @ndaylist ) );
	    @ndaylist = ();
	    }
	}
    push( @toprint,  &week_report( 0, @ndaylist ) ) if( @ndaylist );
    return join("",@toprint);
    }

#########################################################################
#	Print out all known users so user can select his data.		#
#########################################################################
sub user_page
    {
    my $user;
    my @toprint = ( &top_of_page("XL(Who are you?)"), <<EOF );
<center><table border=1><tr><td>
<table border=0 cellspacing=1 cellpadding=1>
<tr><th bgcolor=#d0d0d0><font color=white>Select User</font></th></tr>
EOF
    foreach $user ( &users_in_group() )
        {
	push( @toprint, "<tr><td>",
	    &sflink($user,"showuser","user",$user),
	    "</td></tr>\n" );
	}
    push( @toprint, "</table></table></center></form>\n" );
    &xprint(@toprint);
    exit(0);
    }

#########################################################################
#	Go through all days to calculate points banked to specified	#
#	day.								#
#########################################################################
sub calculate_bank
    {
    my( $today ) = @_;
    my( @flist ) = sort &DBget("users",$cpi_vars::USER,"days");
    my( $eind, $ind );
    my( $diffpnt ) = 0;

    for( $eind=0; $eind < $#flist; $eind++ )
        {
	last if( $flist[$eind] eq $today );
	}
    if( $flist[$eind] eq $today )
	{
	my $bind = $eind - $BANK_DAYS_BACK;
	$bind = 0 if( $bind < 0 );
	for( $ind=$bind; $ind<$eind; $ind++ )
	    {
	    $diffpnt +=
		( &DBget("users",$cpi_vars::USER,"days",$flist[$ind],"maxg")
		- &DBget("users",$cpi_vars::USER,"days",$flist[$ind],"total") );
	    }
	}
    #return "$diffpnt($today)";
    return $diffpnt;
    }

#########################################################################
#	Go through previous days to find a day where weight was		#
#	specified.							#
#########################################################################
sub calculate_weight
    {
    my( $today ) = @_;
    my( @flist ) = sort &DBget("users",$cpi_vars::USER,"days");
    my( $eind, $ind );

    for( $eind=0; $eind <= $#flist; $eind++ )
        {
	last if( $flist[$eind] >= $today );
	}
    $eind = $#flist if( $eind > $#flist );
    $eind-- if( $flist[$eind] > $today );
    while( $eind >= 0 )
	{
	my $w = &DBget("users",$cpi_vars::USER,"days",$flist[$eind],"weight");
	return $w if( $w > 0 );
	$eind--;
	}
    return "";
    }

#########################################################################
#	Remember points associated with activity/food so that we can	#
#	keep most common on hand for easy recall.			#
#########################################################################
sub add_in
    {
    my( $arrayp, $txt, $txtp ) = @_;
    return if( $txt eq "" );
    my( $ind ) = "$txtp-$txt";
    ${$arrayp}{$ind}++;
    }

#########################################################################
#	Go through previous days to find most common foods & exercizes.	#
#########################################################################
sub most_common
    {
    my( $FIELD ) = @_;
    my( $d, $ind, $topic );
    my %activities = ();
    foreach $d ( &DBget("users",$cpi_vars::USER,"days") )
        {
	my $mealtime;
	#foreach $mealtime ( @MEAL_TIMES )
	foreach $mealtime ( 1 )
	    {
	    #foreach $ind ( @{ $MEAL_RANGES{$mealtime} } )
	    foreach $ind ( 1 )
		{
		&add_in( \%{$activities{$mealtime}},
		    &DBget("users",$cpi_vars::USER,"days",$d,"desc",$ind),
		    &DBget("users",$cpi_vars::USER,"days",$d,"point",$ind) );
		}
	    }
	}
    #foreach $topic ( @MEAL_TIMES )
    foreach $topic ( 1 )
        {
	my @temparray =
	    sort	{	${ $activities{$topic}}{$b}
		    	<=>	${ $activities{$topic}}{$a}
			}	keys %{ $activities{$topic} };
	@temparray = @temparray[ 0..$NUM_MOST_COMMON-1 ]
	    if( scalar(@temparray) >= $NUM_MOST_COMMON );
	${$FIELD}{$topic} = "<option value=new>XL([New])\n";
	${$FIELD}{$topic} .= "<option value=delete>XL([Remove])\n";
	foreach $_ ( @temparray )
	    {
	    if( /^([^\-]*)-(.*)/ )
	        {
		my( $pts, $activity ) = ( $1, $2 );
		my( $text ) = "$activity ($pts ".($pts==1?"XL(point)":"XL(points)").")";
		${$FIELD}{$topic} .= "<option value=\"$_\">$text\n";
		}
	    }
	}
    }

#########################################################################
#	Calculate range of points based on weight.			#
#########################################################################
sub calculate_range
    {
    my( $w ) = @_;
    foreach $_ ( sort keys %WEIGHT_TO_POINT_RANGES )
        {
	return split(/-/,$WEIGHT_TO_POINT_RANGES{$_}) if( $w < $_ );
	}
    &fatal("XL(Weight out of range!)");
    }

#########################################################################
#########################################################################
sub check_boxes
    {
    my( $curday, $vname, $num, $title ) = @_;
    my( $ind );
    my $nchecks = &DBget("users",$cpi_vars::USER,"days",$curday,$vname);
    my @toprint = ( "<tr><th align=left>$title</th><td>" );
    for( $ind=0; $ind<$num; $ind++ )
        {
	push(@toprint, "<input type=checkbox name=${vname}$ind value=checked");
	push(@toprint, " checked") if( $ind < $nchecks );
	push(@toprint, " onClick='trigger();'>");
	}
    push(@toprint, "</td>");
    return join("",@toprint);
    }

#########################################################################
#	Print out data for a user's day and allow him to change it.	#
#	Lots of javascript to make calculations easy.			#
#########################################################################
sub day_page
    {
    my( $curday ) = @_;
    #&most_common(\%FIELD);	# Go find out most common entries

    $curday = $cpi_vars::TODAY if( $curday eq "" );
    my( $offset ) = &calculate_bank( $curday );

    my $todaysec = &str_to_time( $curday );
    my( $yesterday ) = &timestr( $todaysec - 24*60*60 );
    $yesterday = &sfbutton($yesterday."&larr;", "show", "day", $yesterday );
    $yesterday =~ s+"+\\"+g;
    my( $tomorrow ) = &timestr( $todaysec + 24*60*60 );
    $tomorrow = &sfbutton("&rarr;".$tomorrow, "show", "day", $tomorrow );
    $tomorrow =~ s+"+\\"+g;

    my $w = &calculate_weight( $curday );

    my $current_weight_sub = &calculate_weight( $curday );

    my $goal_weight_sub = &DBget("users",$cpi_vars::USER,"goalweight");

    my @structs = ();

    my $numentries = &DBget("lastind");
    my $ind;
    for( $ind=0; $ind<$numentries; $ind++ )
        {
	$_ = &DBget("text",$ind);
	if( /^(.*)\|([\d\.\-]*)$/ )
	    {
	    my( $pet ) = &perl_esc( &trans($1) );
	    my $pt = $2;
	    $pt = 0 if( $pt eq "" );
	    push( @structs, "{p:$pt,t:\"$pet\"}" )
	    }
	}
    my $answers_sub = join($PRETTYJS,@structs);

    @structs = ();
    my $pr = 
        &DBget("users",$cpi_vars::USER,"days",$curday,"events");
    if( $pr )
	{
	foreach $_ ( split( /,/,$pr) )
	    {
	    if( /(\d+)\|(\d+)/ )
		{ push(@structs,"{u:1,e:$2,i:$1}") }
	    }
	}
    my $entries_sub = join($PRETTYJS,@structs);

    @structs = ();
    foreach $_ ( sort { $a <=> $b } keys %WEIGHT_TO_POINT_RANGES )
        {
	push( @structs, "{ weight:$_, minp:$1, maxp:$2 }" )
	    if( $WEIGHT_TO_POINT_RANGES{$_} =~ /(\d+)-(\d+)/ );
	}
    my $weight_ranges = join($PRETTYJS,@structs);

    my $total_in_category =
	join(",",&DBget("users",$cpi_vars::USER,"days",$curday,"cats"));
    $total_in_category = "0,0,0" if( $total_in_category eq "" );

    my $comment_sub = &trans(
        &DBget("users",$cpi_vars::USER,"days",$curday,
	    "comment") );
    $comment_sub = "" if( ! defined($comment_sub) );

    my $timetypes_sub = '"' . join("\",\"",@timetypes) . '"';

    $_ = $cpi_vars::THIS; 	# Eliminate only used once error

    &xprint(&top_of_page($curday),
        &template( $JAVASCRIPT,
	    "%%BODY_TAGS%%",		$cpi_vars::BODY_TAGS,
	    "%%TABLE_TAGS%%",		$cpi_vars::TABLE_TAGS,
	    "%%SID%%",			$cpi_vars::SID,
	    "%%USER%%",			$cpi_vars::USER,
	    "%%THIS%%",			$cpi_vars::THIS,
	    "%%CURRENT_WEIGHT%%",	$current_weight_sub,
	    "%%GOAL_WEIGHT%%",		$goal_weight_sub,
	    "%%day%%",			$curday,
	    "%%YESTERDAY%%",		$yesterday,
	    "%%TOMORROW%%",		$tomorrow,
	    "%%ANSWERS%%",		$answers_sub,
	    "%%ENTRIES%%",		$entries_sub,
	    "%%WEIGHT_RANGES%%",	$weight_ranges,
	    "%%TOTAL_IN_CATEGORY%%",	$total_in_category,
	    "%%COMMENT%%",		$comment_sub,
	    "%%TIMETYPES%%",		$timetypes_sub));
    }

#########################################################################
#	Take data from day page and write it out to day file.		#
#########################################################################
sub do_update
    {
    my( $ind );
    
    my $today = ($cpi_vars::FORM{day}||$cpi_vars::TODAY);
    my $lastcomment = &trans(
	&DBget("users",$cpi_vars::USER,"days",
	    $today,"comment") );
    my %seentxt = ();
    for( $ind = &DBget("lastind"); --$ind >= 0; )
        {
	my $str = &DBget("text",$ind);
	if( $str =~ /(.*)\|(\d+)$/ )
	    {
	    my( $txt, $pts ) = ( $1, $2 );
	    $txt =~ s/^[a-z][a-z]\|//;
	    $seentxt{ &trans($txt)."|$pts" } = $ind;
	    }
	}
    &DBwrite( );
    my $ev;
    my @structs = ();
    #print "CATS=$cpi_vars::FORM{cats}.<br>\n";
    #print "EVENTS=$cpi_vars::FORM{events}.<br>\n";
    #print "COMMENT=$cpi_vars::FORM{comment}.<br>\n";
    #print "WEIGHT=$cpi_vars::FORM{weight}.<br>\n";
    foreach $ev ( split(/\|/,$cpi_vars::FORM{events}) )
        {
	if( $ev =~ /^(.*),([\d\-]+),([\d\-]+)$/ )
	    {
	    my( $txt, $pts, $et ) = ( $1, $2, $3 );
	    my( $lup ) = "${txt}|$pts";
	    if( defined($seentxt{$lup}) )
	        { $ind = $seentxt{$lup}; }
	    else
	        {
		$lup = "$cpi_vars::LANG|$txt|$pts";
		$ind = &DBget("lastind");
		&DBput("lastind",$ind+1);
		&DBput("text",$ind,$lup);
		&DBput("ind",$lup,$ind);
		}
	    &DBput("used",$ind,
		&DBget("used",$ind)+1 );
	    push( @structs, "$ind|$et" );
	    }
	}
    $_ = join(",",@structs);
    &DBput("users",$cpi_vars::USER,"days",$today,"events",$_);
    &DBput("users",$cpi_vars::USER,"days",$today,"cats",
        $cpi_vars::FORM{cats});
    &DBput("users",$cpi_vars::USER,"days",$today,"comment",
        "$cpi_vars::LANG|$cpi_vars::FORM{comment}")
	if( $cpi_vars::FORM{comment} ne $lastcomment );
    &DBput("users",$cpi_vars::USER,"days",$today,"weight",
        $cpi_vars::FORM{weight});
    &DBadd("users",$cpi_vars::USER,"days",$today);
    &DBpop();
    &day_page($today);
    }

sub fixup_db
    {
    print "Fixup_db...\n";
    &DBwrite( );
    my( $user, $day, $entry, $ind );
    my %answers = ();
    foreach $user ( &users_in_group() )
	{
        foreach $day ( &DBget("users",$user,"days") )
	    {
	    foreach $entry ( 0 .. 17 )
	        {
		my $txt =
		    &DBget("users",$user,"days",$day,"desc",$entry);
		next if( $txt eq "" );
		my $pts =
		    &DBget("users",$user,"days",$day,"point",$entry);
		my $rpts = $pts;
		$rpts = 15 if( $txt eq "McDonalds Quarter Pounder with Cheese" );
		$rpts = 16 if( $txt eq "McDonalds steak, egg and cheese bagel" );
		$rpts = 7 if( $txt eq "D\'Angelos Steak D\'lite" );
		$rpts = 5 if( $txt eq "bowl of Life Cereal with 1% milk" );
		$rpts = 2 if( $txt eq "2 Boca Burgers" );
		$rpts = -$rpts if( $entry >= 15 );
		$answers{"${txt}|$rpts"}++;
		&DBput("users",$user,"days",$day,"point",$entry,$rpts)
		    if( $rpts != $pts );
		}
	    }
	}
    my @sorted_keys = ( sort { $answers{$b}<=>$answers{$a} } keys %answers );
    my $ctr = 0;
    foreach $ind ( @sorted_keys )
        {
	&DBput("text",$ctr,$ind);
	&DBput("ind",$ind,$ctr);
	&DBput("used",$ctr,$answers{$ind});
	$answers{$ind} = $ctr++;
	}
    &DBput("lastind",$ctr);
    foreach $user ( &users_in_group() )
	{
        foreach $day ( &DBget("users",$user,"days") )
	    {
	    my @events = ();
	    foreach $entry ( 0..17 )
	        {
		my $txt =
		    &DBget("users",$user,"days",$day,"desc",$entry);
		next if( $txt eq "" );
		my $etype = int( $entry / 5 );
		my $pts =
		    &DBget("users",$user,"days",$day,"point",$entry);
		&DBput("users",$user,"days",$day,"point",$entry,"");
		&DBput("users",$user,"days",$day,"desc",$entry,"");
		my $ind = $answers{"${txt}|$pts"};
		push( @events, "${ind}|$etype" );
		}
	    &DBput("users",$user,"days",$day,"events",
	        join(",",@events) );
	    &DBput("users",$user,"days",$day,"point","");
	    &DBput("users",$user,"days",$day,"desc","");
	    &DBput("users",$user,"days",$day,"Total cereal","");
	    &DBput("users",$user,"days",$day,"maxg","");
	    &DBput("users",$user,"days",$day,"currentdiff","");
	    &DBput("users",$user,"days",$day,"user","");
	    &DBput("users",$user,"days",$day,"day","");
	    &DBput("users",$user,"days",$day,"func","");
	    &DBput("users",$user,"days",$day,"tobank","");
	    my @struct = ();
	    my $thing;
	    foreach $thing ( "milk", "water", "fruveg" )
	        {
	        $_ = &DBget("users",$user,"days",$day,$thing);
		$_ = "0" if( ! $_ );
		push( @struct, $_ );
	        &DBput("users",$user,"days",$day,$thing,"");
		}
	    &DBput("users",$user,"days",$day,"cats",
	        join(",",@struct));
	    }
	}
    $_ = \%cpi_vars::databases; # Get rid of "only used once" error
    &write_file( "/tmp/fixed.db", &hash_to_string( \%{$cpi_vars::databases{$cpi_vars::DB}} ) );
    &DBpop( );
    exit(0);
    }

#########################################################################
#	Main								#
#########################################################################
#&show_vars();

&fixup_db() if( ($ARGV[0]||"") eq "fix" );

&fatal("XL(Usage):  $cpi_vars::PROG.cgi (dump|dumpaccounts|dumptranslations|undump|undumpaccounts|undumptranslations) [ dumpname ]",0)
    if( ($ENV{SCRIPT_NAME}||"") eq "" );

$cpi_vars::FORM{day} ||= "";

if( $cpi_vars::FORM{func} eq "Update" )
    { &do_update(); }
elsif( $cpi_vars::FORM{func} eq "graph" )
    { &graph_page($cpi_vars::FORM{ndays}); }
elsif( ($cpi_vars::FORM{weekdays}||"") ne "" )
    { &xprint(&week_report( 1, split(/,/,$cpi_vars::FORM{weekdays}) ) ); }
elsif( $cpi_vars::FORM{func} eq "fullreport" )
    { &xprint(&full_report()); }
elsif( $cpi_vars::FORM{func} eq "dir" )
    { &dir_page(); }
elsif( $cpi_vars::FORM{day} eq "" )
    { &day_page( $cpi_vars::FORM{day} ); }
elsif( $cpi_vars::FORM{day} !~ /^\d+$/ )
    { &fatal("XL(Illegal day specified.)"); }
else
    { &day_page( $cpi_vars::FORM{day} ); }

&footer();
