<script>
//
//indx#	ww.js - Javascript support for Weight Watchers tool
//@HDR@	$Id: ww.js,v 1.1 2020/08/12 21:23:09 chris Exp chris $
//@HDR@
//@HDR@	Copyright (c) 2020-2026 Christopher Caldwell (Christopher.M.Caldwell0@gmail.com)
//@HDR@
//@HDR@	Permission is hereby granted, free of charge, to any person
//@HDR@	obtaining a copy of this software and associated documentation
//@HDR@	files (the "Software"), to deal in the Software without
//@HDR@	restriction, including without limitation the rights to use,
//@HDR@	copy, modify, merge, publish, distribute, sublicense, and/or
//@HDR@	sell copies of the Software, and to permit persons to whom
//@HDR@	the Software is furnished to do so, subject to the following
//@HDR@	conditions:
//@HDR@	
//@HDR@	The above copyright notice and this permission notice shall be
//@HDR@	included in all copies or substantial portions of the Software.
//@HDR@	
//@HDR@	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
//@HDR@	KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
//@HDR@	WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
//@HDR@	AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
//@HDR@	HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
//@HDR@	WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
//@HDR@	FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
//@HDR@	OR OTHER DEALINGS IN THE SOFTWARE.
//
//hist#	2026-02-19 - Christopher.M.Caldwell0@gmail.com - Created
////////////////////////////////////////////////////////////////////////
//doc#	ww.js - Javascript support for Weight Watchers tool
////////////////////////////////////////////////////////////////////////

// Values substituted by .cgi script
var goal_weight = %%GOAL_WEIGHT%%;
var current_weight = %%CURRENT_WEIGHT%%;
var ranges = new Array( %%WEIGHT_RANGES%% );	// .weight, .minp, .maxp
var answers = new Array( %%ANSWERS%% );		// .p, .t
var entries = new Array( %%ENTRIES%% );		// .u, .e, .i
var cattot = new Array( %%TOTAL_IN_CATEGORY%% );
var comment = "%%COMMENT%%";
var sections = new Array( %%TIMETYPES%% );
// End of values coming in from .cgi script

var categories = new Array(
    { text:"XL(Milk)",				needed:2 },
    { text:"XL(Water)",				needed:6 },
    { text:"XL(Fruits and vegetables)",		needed:4 }
    );

var openone = -1;
var opensect = 0;

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function setcomment()
    {
    var newcomment = prompt("XL(New comment):",(comment?comment:""));
    if( newcomment )
        {
	comment = newcomment;
	draw_day_page();
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function get_points()
    {
    while( 1 )
	{
	var res = prompt("XL(Enter points or hit return to calculate):","");
	if( isNaN(res) || res == "" )
	    {
	    return res;
	    }
	if( res >= 0 && res <= 100 )
	    {
	    return res;
	    }
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function askfloat(str,minv,defv,maxv)
    {
    while( 1 )
	{
	var res = prompt(str+" ("+minv+"-"+maxv+"):",defv);
	var v = parseFloat(res);
	if( v >= minv && v <= maxv )
	    {
	    return v;
	    }
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function exerpoints()
    {
    var total_points = get_points();
    if( ! isNaN(total_points) && (total_points != "") )
	{ return total_points; }
    else
	{
	var minutes = askfloat("XL(Minutes exercized)",1,60,240);
	var intensity = askfloat("XL(Intensity)",1,3,10);
	total_points = weight * minutes * intensity / 11538.0;
	return Math.floor(total_points);
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function foodpoints()
    {
    var total_points = get_points();
    if( ! isNaN(total_points) && (total_points != "") )
	{ return total_points; }
    else
	{
	var calories = askfloat("XL(Calories)",0,"",550);
	var fibergrams = askfloat("XL(Dietary fiber grams)",0,"",4);
	var totalgrams = askfloat("XL(Total grams of fat)",0,"",20);
	var servings = askfloat("XL(Number of servings)",0.1,1,100);
	var effective_calories = calories - (fibergrams * 10);
	var points_wo_fat = effective_calories / 50.0 + 0.5;
	var points_per_serving = points_wo_fat + totalgrams / 12.0;
	total_points = points_per_serving * servings;
//		alert(
//		    "\\n\\rXL(Calories): " + calories +
//		    "\\n\\rXL(Fibergrams): " + fibergrams +
//		    "\\n\\rXL(totalgrams): " + totalgrams +
//		    "\\n\\rXL(servings): " + servings +
//		    "\\n\\rXL(effective_calories): " + effective_calories +
//		    "\\n\\rXL(points_wo_fat): " + points_wo_fat +
//		    "\\n\\rXL(points_per_serving): " + points_per_serving +
//		    "\\n\\rXL(total_points): " + total_points );
	return Math.floor(total_points);
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function done()
    {
    with( window.document )
	{
	form.func.value = "Update";
	form.cats.value = cattot[0] + "," + cattot[1] + "," + cattot[2];
	var e, i;
	form.events.value = "";
	for( e=0; e<entries.length; e++ )
	    {
	    if( entries[e].u && (i=entries[e].i)>=0 )
		{
		if( e > 0 ) { form.events.value += "|"; }
		form.events.value += answers[ i ].t;
		form.events.value += ",";
		form.events.value += answers[ i ].p;
		form.events.value += ",";
		form.events.value += entries[ e ].e;
		}
	    }
	form.comment.value = comment;
	form.weight.value = current_weight;
	form.submit();
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function doadd( n, et )
    {
    var is_exercize = ( et == (sections.length-1) );
    with( window.document.form )
        {
	if( useval.value )
	    {
	    var p;
	    if( usepts.value )
	        { p = ( is_exercize ? -usepts.value : usepts.value ); }
	    else
		{ p = ( is_exercize ? -exerpoints() : foodpoints() ); }
	    if( p != "" )
		{
		var i = answers.length++;
		answers[i] = { t:useval.value, p:p };
		if( n < 0 )
		    { n = entries.length++; }
		entries[n] = { i:i, u:1, e:et };
		draw_day_page();
		}
	    }
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function dodelete( n )
    {
    entries[n].u = 0;
    draw_day_page();
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function add_to_sect( sect )
    {
    openone = -1;
    opensect = sect;
    draw_entry_page();
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function modify( n )
    {
    openone = n;
    opensect = entries[n].e;
    draw_entry_page();
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function setto( n )
    {
    //if( openone < 0 )
    //    { openone = entries.length++; }
    // entries[ openone ] = { i:n, u:1, e:opensect };
    // draw_day_page();
    with ( window.document.form )
        {
	if( useval.value==answers[n].t && usepts.value==answers[n].p )
	    {
	    if( openone < 0 )
		{ openone = entries.length++; }
	    entries[openone] = { i:n, u:1, e:opensect };
	    draw_day_page();
	    }
	else
	    {
	    useval.value = answers[n].t;
	    usepts.value = answers[n].p;
	    }
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function add_to_category( catnum, inc )
    {
    cattot[catnum] += inc;
    if( cattot[catnum] < 0 ) { cattot[catnum] = 0; }
    draw_day_page();
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function setgoal()
    {
    var v = prompt("XL(Enter goal weight):",goal_weight);
    if( v ) { goal_weight = v; }
    draw_day_page();
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function setweight()
    {
    var v = prompt("XL(Enter current weight):",current_weight);
    if( v ) { current_weight = v; }
    draw_day_page();
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function make_answertable( l4, is_exercize )
    {
    var res = "";
    var p;
    var l4re = new RegExp( l4, "i" );
    var numfound = 0;
    var addres = "";
    for( p=0; p<answers.length; p++ )
	{
	// if( (answers[p].p>0) ^ is_exercize )
	if( l4re.test(answers[p].t) && (answers[p].p>0) ^ is_exercize )
	    {
	    if( numfound++ < 20 )
		{
		res += "<tr><td><a href='javascript:setto("+p+");'>";
		res += ( answers[p].t + "</a></td><td align=right>" );
		res += ( answers[p].p + "</td></tr>" );
		}
	    }
	}
    if( numfound < 1 || numfound >= 20 )
        { return "XL([["+numfound + "]] entries match)"; }
    else
        { return "<table width=100%>" + res + "</table>"; }
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function update_answertable( l4, is_exercize )
    {
    if( answertableptr )
        {
	answertableptr.innerHTML = make_answertable( l4, is_exercize );
	}
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function draw_entry_page()
    {
    var is_exercize = ( opensect==(sections.length-1) );
    var s = "<table border=0 style='border:solid 1px' %%TABLE_TAGS%%><tr><th>\n";
    var eind = ( (openone >= 0) ? entries[openone].i : -1 );
    if( eind >= 0 )
	{
	s += "<a href='javascript:dodelete("+openone+");'>";
	s += "[XL(REMOVE)]</a>&nbsp;&nbsp;";
	}
    var prettyname = ( is_exercize ? "XL(Exercize):" : "XL(Food):" );
    s += prettyname;
    s += "</td><td nowrap><input type=text name=useval size=40";
    s += " placeholder='XL(Set) "+prettyname+"'";
    if( eind >= 0 )
	{ s += " value=\"" + answers[eind].t + "\" "; }
    s += " onKeyUp='update_answertable(this.value,"+is_exercize+");'>";
    s += "<input name=usepts type=text size=2";
    s += " placeholder='XL(Set points)'";
    if( eind >= 0 )
        { s += " value=\"" + answers[eind].p + "\""; }
    s += " onChange='doadd("+openone+","+opensect+");'>";
    s += "<input type=button value=\"XL(Modify entry)\" onClick='doadd("+openone+","+opensect+");'";
    s += "</td></tr><tr><td colspan=2 width=100%><div id=answertable>";
    s += make_answertable(
	((eind>=0)?answers[eind].t:""),
	is_exercize );
    s += "</div></td></tr></table>";
    document.getElementById("REPLACE_ID").innerHTML = s;
    answertableptr = document.getElementById("answertable");
    }

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
function draw_day_page()
    {
    var i;
    var s = "<table border=0 style='border:solid 1px' %%TABLE_TAGS%%>\n";
    s += "<tr><td align=left>%%YESTERDAY%%</td>\n";
    s += "<td align=center>%%day%%</td>";
    s += "<td align=right>%%TOMORROW%%</td></tr>\n";
    s += "<tr><td colspan=3>\n";
    s += "<table border=0 cellspacing=0 cellpadding=0>";
    var sectlist = new Array( sections.length );
    var total = 0;
    for( e=0; e<entries.length; e++ )
        {
	if( entries[e].u )
	    {
	    var t = entries[e].e;
	    if( ! sectlist[t] )
		{ sectlist[t] = new Array(); }
	    sectlist[t].length++;
	    sectlist[t][sectlist[t].length-1] = e;
	    }
	}
    s += "<tr><th align=left><a href='javascript:setgoal();'>";
    s += "XL(Goal weight): "+goal_weight+"</a></th>";
    s += "<th align=right><a href='javascript:setweight();'>";
    s += "XL(Current weight):</a></th><td align=left>";
    s += "<a href='javascript:setweight();'>"+current_weight+"</a></td></tr>";
    s += "<tr><th colspan=3><hr></td></tr>";

    for( i=0; i<sections.length; i++ )
        {
	var sectlen = ( sectlist[i] ? sectlist[i].length : 0 );
	var is_exercize = ( i == (sections.length-1) );
	s += "<tr><th align=left valign=top rowspan="+(sectlen+1)+">";
	s += sections[i]+":</th><td>";
	s += "<input type=button onClick='add_to_sect("+i+");'";
	s += " help='button-add-section'";
	s += " value='XL(Add)'>";
	s += "</td><td></td></tr>";
	var j;
	for( j=0; j<sectlen; j++ )
	    {
	    s += "<tr><td>";
	    var ind = sectlist[i][j];
	    var eind = entries[ind].i;
	    if( ! answers[eind] )			//CMC
		{ alert("eind="+eind+", length="+answers.length); }
	    s += "<a href='javascript:modify("+ind+");'>";
	    s += ( (eind >= 0) ? answers[eind].t : "" );
	    s += "</a></td><td align=right>";
	    var pnt = answers[ eind ].p;
	    s += pnt;
	    total += 1*pnt;
	    s += "</td></tr>";
	    }
	}

    i = 0;
    while( current_weight >= (ranges[i+1].weight) )
        { i++; }
    var minp = ranges[i].minp;
    var maxp = ranges[i].maxp;
    var colflag = "";
    if( total > maxp )
        { colflag = " bgcolor=#e08080"; }
    else if( total >= minp )
        { colflag = " bgcolor=#80e080"; }
    else if( total > 0 )
        { colflag = " bgcolor=#8080e0"; }

    s += "<tr"+colflag+"><th align=left>XL(Permissible points): "+minp+"-"+maxp;
    s += "</td><th align=right>XL(Total):</th><th align=right>";
    s += total+"</th></tr>";
    s += "<tr><th colspan=3><hr></td></tr>";

    for( i=0; i<categories.length; i++ )
        {
	var col = ( (cattot[i] < categories[i].needed) ? "#e08080" : "#80e080" );
	s += "<tr bgcolor="+col+"><th align=left>"+categories[i].text+":</th>";
	s += "<th><table width=100%><tr><td align=left>";
	s += "<a href='javascript:add_to_category("+i+",1);'>+</a>";
	s += "</td><td align=right>";
	s += "<a href='javascript:add_to_category("+i+",-1);'>-</a>";
	s += "</td></tr></table></th>";
	s += "<td align=right>" + cattot[i] + "</td></tr>";
	}
    s += "<tr><th align=left>XL(Comments):</th><td colspan=2>";
    s += "<a href='javascript:setcomment();'>";
    s += ( comment ? comment : "[SET]" );
    s += "</a></td></tr><tr><th colspan=3>";
    s += "<input type=hidden name=cats><input type=hidden name=events>";
    s += "<input type=hidden name=comment><input type=hidden name=weight>";
    s += "<input type=button help='button-modify-day'";
    s += " value=\"XL(Modify day's information)\" onClick='done();'></form>";
    s += "</th></tr></table></td></tr></table>";
    document.getElementById("REPLACE_ID").innerHTML = s;
    }
</script>
<center><div id=REPLACE_ID>TEXT</div></center>
<script>draw_day_page();</script>
