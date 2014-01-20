Date.prototype.addMinutes = function (m) {
    this.setTime(this.getTime() + (m * 60 * 1000));
    return this;
}

Date.prototype.addHours = function (h) {
    this.setTime(this.getTime() + (h * 60 * 60 * 1000));
    return this;
}

Date.prototype.addDays = function (d) {
    this.setTime(this.getTime() + (d * 24 * 60 * 60 * 1000));
    return this;
}

Date.prototype.addWeeks = function (d) {
    this.setTime(this.getTime() + (d * 7 * 24 * 60 * 60 * 1000));
    return this;
}

function draw_cockpit_panel(interval, location, end) {

    end = typeof end !== 'undefined' ? new Date(Number(end) * 1000) : new Date();

    $("#log-cockpit-loading-indicator").show();
    $("#log-cockpit-loading-indicator").position({
        my: "center",
        at: "center",
        of: location
    });

    var xUnitInterval = function (interval) {
        if (interval == 'minute') {
            return d3.time.seconds
        } else if (interval == 'hour') {
            return d3.time.minutes
        } else if (interval == 'day') {
            return d3.time.hours
        } else if (interval == 'month') {
            return d3.time.days
        } else {
            //TODO define proper error handling strategy
            alert("interval '" + interval + "' not recognized." )
        }
    }


    var click_renderlet = function (_chart) {
        _chart.selectAll("rect.bar").on("click", function (d) {
            // load the log search page with chart and table set
            // to this range.
            var start = new Date(d.data.key);
            var end = new Date(start);
            var new_interval;

            if (interval === 'hour') {
                end.addMinutes(1);
                new_interval = 'minute';
            } else if (interval === 'day') {
                end.addHours(1);
                new_interval = 'hour';
            } else if (interval === 'month') {
                end.addDays(1);
                new_interval = 'day';
            } else if (interval === 'minute') {
                new_interval = 'seconds';
                end.addMinutes(1);
            }

            var uri = '/intelligence/search?start_time='.
                    concat(String(Math.round(start.getTime()/1000)),
                    "&end_time=", String(Math.round(end.getTime()/1000)),
                    "&interval=", new_interval);
            window.location.assign(uri);
        });
    };

    var panelWidth = $(location).width();
    var panelHeight = 300;
    var margin = {top: 30, right: 30, bottom: 30, left: 40};

    var chart = dc.barChart(location);
    var start = new Date(end);
    if (interval === 'hour') {
                start.addHours(-1);
            } else if (interval === 'day') {
                start.addDays(-1);
            } else if (interval === 'month') {
                start.addWeeks(-4);
            } else if (interval === 'minute') {
                start.addMinutes(-1);
            }
    var uri = "/intelligence/log/cockpit/data?start_time=".
        concat(String(Math.round(start.getTime()/1000)),
            "&end_time=", String(Math.round(end.getTime()/1000)),
            "&interval=", interval);

    d3.json(uri, function (error, events) {

        if (events.data.length == 0) {
            $(location).html("<h2>No log data found.<h2>");
        } else {
            events.data.forEach(function (d) {
                d.time = new Date(d.time);
                d.count = +d.count;
            });

            var xf = crossfilter(events.data);
            var comps = events.components;
            var timeDim = xf.dimension(function (d) {
                return d.time;
            });

            var eventsByTime = timeDim.group().reduce(
                function (p, v) {
                    if (v.loglevel === 'error') {
                        p.errorEvents += v.count;
                    } else {
                        p.warnEvents += v.count;
                    }
                    return p;
                },
                function (p, v) {
                    if (v.loglevel === 'error') {
                        p.errorEvents -= v.count;
                    } else {
                        p.warnEvents -= v.count;
                    }
                    return p;
                },
                function () {
                    return {
                        errorEvents: 0,
                        warnEvents: 0
                    };
                }
            );

            var minDate = timeDim.bottom(1)[0].time;
            var maxDate = timeDim.top(1)[0].time;

            chart
                .width(panelWidth)
                .height(panelHeight)
                .margins(margin)
                .dimension(timeDim)
                .group(eventsByTime, "Warning Events")
                .valueAccessor(function (d) {
                    return d.value.warnEvents;
                })
                .stack(eventsByTime, "Error Events", function (d) {
                    return d.value.errorEvents;
                })
                .x(d3.time.scale().domain([minDate, maxDate]))
                .xUnits(xUnitInterval(interval))
                .renderHorizontalGridLines(true)
                .centerBar(true)
                .elasticY(true)
                .brushOn(false)
                .renderlet(click_renderlet)
                .legend(dc.legend().x(100).y(10))
                .title(function (d) {
                    return d.key
                        + "\n\n" + d.value.errorEvents + " ERRORS"
                        + "\n\n" + d.value.warnEvents + " WARNINGS";
                });

            chart.render();
            $("#log-cockpit-loading-indicator").hide();
        }

    });
}

function draw_search_table(start, end, location) {

    var uri = "/intelligence/log/search/data/".concat(String(start), "/", String(end));
    var oTableParams = {
        "bProcessing": true,
        "bServerSide": true,
        "sAjaxSource": uri,
        "bPaginate": true,
        "bFilter": true,
        "bSort": true,
        "bInfo": false,
        "bAutoWidth": true,
        "bLengthChange": true,
        "aoColumnDefs":[
                { "bVisible": false, "aTargets": [ 5,6,7,8,9,10 ] },
                { "sName": "timestamp", "aTargets": [ 0 ] },
                { "sType": "date", "aTargets": [0] },
                { "sName": "loglevel", "aTargets": [ 1 ] },
                { "sName": "component", "aTargets": [ 2 ] },
                { "sName": "host", "aTargets": [ 3 ] },
                { "sName": "message", "aTargets": [ 4 ] },
                { "sName": "location", "aTargets": [ 5 ] },
                { "sName": "pid", "aTargets": [ 6 ] },
                { "sName": "source", "aTargets": [ 7 ] },
                { "sName": "request_id", "aTargets": [ 8 ] },
                { "sName": "type", "aTargets": [ 9 ] },
                { "sName": "received", "aTargets": [ 10 ] },
                { "sType": "date", "aTargets": [10] }
            ]
    }

    var oTable = $(location).dataTable(oTableParams);

    $(window).bind('resize', function () {
        oTable.fnAdjustColumnSizing();
    } );
}

/*
 function updateWindow(){

 var panelWidth = $("#row3-full").width();
 var panelHeight = 300;
 var margin = {top: 30, right: 30, bottom: 30, left: 80},
 width = panelWidth - margin.left - margin.right,
 height = panelHeight - margin.top - margin.bottom;


 x = d3.time.scale().range([0, width]);
 x.domain(d3.extent(data, function(d) { return d.date; }));
 xAxis = d3.svg.axis().scale(x)
 .orient("bottom").ticks(5);

 console.log("adjusted width = " + panelWidth);
 console.log("adjusted height = " + panelHeight);
 svg.attr("width", panelWidth)
 .attr("height", panelHeight);
 svg.select(".x.axis")
 .call(xAxis);
 svg.select(".line")
 .attr("d", valueLine(data));

 }

 window.onresize = updateWindow;

 */