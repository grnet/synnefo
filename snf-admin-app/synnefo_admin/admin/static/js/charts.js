String.prototype.capitalize = function() {
        return this.charAt(0).toUpperCase() + this.slice(1);
};


String.prototype.sanitize = function() {
    new_string = "";
    for (var i = 0, len = this.length; i < len; i++) {
        c = this.charAt(i);
        if (/^[a-zA-Z0-9]$/.test(c)) {
            new_string += c;
        } else if (/^[\.\-\_\:\~\(\)\,\']$/.test(c)) {
            new_string += c;
        } else {
            new_string += "_"; // replace it with a safe character
        }
    }
    return new_string;
};

var chart_options = {
    color: {
        pattern: ['#68B3F0','#EEC04C','#FF6F90','#A9DDD9','#7474F1', '#8EBE6D', '#C77529', '#F53939', '#FAA330', '#AD57EE'],
    }
};

// Shorten any value that is more than 100,000.
// Its presentation will be as a number multiplied by a power of 10. The power
// sign will be "^", if we wish to have non-html tags, else <sup></sup>.
function shorten(value, non_html) {
    if (value < 1000000)
        return value;

    non_html = non_html || false;

    var i = 0;
    while (value > 10) {
        value = value / 10;
        i++;
    }

    ret = value.toFixed(3) + ' x 10';
    if (non_html) {
        return ret + '^' + i.toString();
    } else {
        return ret + i.toString().sup();
    }
}


function humanize(value, unit) {
    if (!unit) {
        return shorten(value);
    }

    var units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    var i = 0;
    while (value >= 1024) {
        i++;
        value = value / 1024;
    }

    return shorten(Math.round(value)) + ' ' + units[i];
}


function percentify(value, total) {
    if (total === 0)
        return 0;
    return Math.round(100 * (value / total));
}


// Decide whether a chart presents purely size data (storage, RAM etc.)
function is_size_chart(units) {
    if (!units) {
        return false;
    }

    // If at least one unit in the list is null, then this is not a size chart.
    for (var i = 0; i < units.length; i++) {
        if (units[i] === null) {
            return false;
        }
    }

    return true;
}


// Convert all number elements of a given list to their logarithmic (base 10)
// values.  Should a list contain another list, the calculations continue
// recursively.
function convert2log(list) {
    for (var i = 0; i < list.length; i++) {
        item = list[i];

        if (Array.isArray(item))
            item = convert2log(item);
        else if (typeof item === 'string')
            continue;
        else
            list[i] = Math.log(item) / Math.LN10;
    }

    return list;
}


function create_pie_chart(cols) {
    var c3_opts = {
        data: {
            columns: cols,
            type: 'pie',
            labels: true,
        },
        color: {
            pattern: chart_options.color.pattern,
        },
        //bindto: '#infra-usage',
        tooltip: {
            format: {
                value: function (value, ratio, id, index) {
                    var prc = ratio * 100;
                    prc = prc.toFixed(1);
                    return value + " (" + prc + "%)";
                }
            }
        }
    };

    return c3_opts;
}


function create_bar_chart(cols, log_scale) {
    // By default use natural scale for the Y-axis, unless if prompted
    // otherwise.
    log_scale = log_scale || false;

    if (log_scale)
        cols = convert2log(cols);

    var c3_opts = {
        data: {
            x: 'x',
            columns: cols,
            type: 'bar',
            labels: {
                format: {
                    y: d3.format("d")
                },
            },
        },
        color: {
            pattern: chart_options.color.pattern,
        },

        //bindto: '#infra-usage',
        axis: {
            x: {
                type: 'category', // this needed to load string x value
                label: {
                    //text: 'x-axis text',
                    //position: 'outer-center',
                },
            },
            y: {
                label: {
                    //text: 'Usage Percentage',
                    //position: 'outer-middle',
                },
                tick: {
                    format: d3.format('d')
                }
            }
        },
        grid: {
            y: {
                //show: true,
                show: true,
            }
        },
    };

    // If the Y-axis uses a log scale, then convert its ticks and the data labels
    // to natural numbers (10^x), in order to achieve the log effect. For more
    // info on this trick, read here:
    //
    //      https://github.com/masayuki0812/c3/issues/252#issuecomment-47167150
    //
    if (log_scale) {
        c3_opts.axis.y.tick.format = function(d) {
            return Math.round(Math.pow(10, d)); };
        c3_opts.data.labels = {
            format: {
                y: function(d) {
                    return Math.round(Math.pow(10, d));
                }
            }
        };
    }

    return c3_opts;
}

// The argument names for the arrays are "used" and "free", but they refer to
// any two arrays whose item sum forms a total.
function create_stacked_chart(categories, used, free, units) {
    // Get the category names for the used and free arrays respectively.
    var used_label = used[0];
    var free_label = free[0];

    // Add these category names in any array that derives from the above.
    var used_prc = [used_label];
    var free_prc = [free_label];
    var used_human = [used_label];
    var free_human = [free_label];
    var unit = null;

    for (var i = 1; i < used.length; i++)  {
        var u = used[i];
        var f = free[i];

        if (units) {
            unit = units[i - 1];
        }

        used_human.push(humanize(u, unit));
        free_human.push(humanize(f, unit));
        used_prc.push(percentify(u, u + f));
        free_prc.push(percentify(f, u + f));
    }

    var c3_opts = create_bar_chart([categories, used, free]);

    c3_opts.data.groups = [[used_label, free_label]];
    c3_opts.tooltip = {
        format: {
            value: function (value, ratio, id, index) {
                if (id == used_label) {
                    return used_human[index + 1] + " (" + used_prc[index + 1] + "%)";
                } else {
                    return free_human[index + 1] + " (" + free_prc[index + 1] + "%)";
                }
            }
        }
    };
    c3_opts._priv = {
        'used_human': used_human,
        'free_human': free_human,
        'used_prc': used_prc,
        'free_prc': free_prc,
    };

    //Convert the Y-axis and the data labels to size format.
    size_format_fn = function (v) {
        return humanize(v, units[0]);
    };

    //Shorten values in the Y-axis, if necessary.
    num_format_fn = function (v) {
        return shorten(v, true);
    };

    if (is_size_chart(units)) {
        c3_opts.data.labels.format.y = size_format_fn;
        c3_opts.axis.y.tick.format = size_format_fn;
    } else {
        c3_opts.data.labels.format.y = num_format_fn;
        c3_opts.axis.y.tick.format = num_format_fn;
    }

    return c3_opts;
}


function create_usage_percentage_chart(categories, used, free, units) {
    format_fn = function (d) {
        return d + "%";
    };

    var c3_opts = create_stacked_chart(categories, used, free, units);
    c3_opts.data.columns = [categories, c3_opts._priv.used_prc,
        c3_opts._priv.free_prc];
    c3_opts.axis.y.tick.format = format_fn;

    return c3_opts;
}


//TODO: Wrap long data labels
function infraUsage(data) {
    categories = {
        'astakos.pending_app': 'Project apps',
        'cyclades.cpu': 'CPUs',
        'cyclades.disk': 'System Disk',
        'cyclades.floating_ip': 'Public (Floating) IPs',
        'cyclades.network.private': 'Private Networks',
        'cyclades.ram': 'RAM',
        'cyclades.vm': 'VMs',
        'pithos.diskspace': 'Storage space',
    };

    var displayed_categories = ['x'];
    var used = ['Used'];
    var free = ['Free'];
    var units = [];

    for (var key in categories) {
        // why do we need it?
        if (!categories.hasOwnProperty(key)) {
            continue; // jumps over one iteration
        }

        displayed_categories.push(categories[key]);

        resource = data.resources.all[key];
        var u = resource.used;
        var f = resource.allocated - resource.used;
        units.push(resource.unit);

        used.push(u);
        free.push(f);
    }

    c3_opts = create_usage_percentage_chart(displayed_categories, used, free,
            units);
    c3_opts.bindto = '#infra-usage';
    c3_opts.axis.y.label.text = 'Usage Percentage';
    c3_opts.axis.y.label.position = 'outer-middle';

    var chart = c3.generate(c3_opts);
}


function resourceUsage(data, name) {
    var wrapDomID = 'resource-'+name.replace(/\./gi, '_')+'-wrap';
    var domID = 'resource-'+name.replace(/\./gi, '_');
    $('#resource-usage').append('<div id="'+wrapDomID+'"></div>');
    var chartTitle = '<h3>'+name+' usage</h3>';
    $('#'+wrapDomID).append(chartTitle);
    $('#'+wrapDomID).append('<div id="'+domID+'"></div>');

    var providers = data.providers.slice();
    var used = ['Used'];
    var free = ['Free'];
    var units = [];
    var provider = "";

    for (var i = 0; i < providers.length; i++)  {
        provider = providers[i];

        resource = data.resources[provider][name];
        var u  = resource.used;
        var f  = resource.allocated - resource.used;
        units.push(resource.unit);

        used.push(u);
        free.push(f);
    }
    //Prepend x label
    providers.unshift('x');

    c3_opts = create_stacked_chart(providers, used, free, units);
    c3_opts.bindto = '#'+domID;
    c3_opts.axis.rotated = true;
    c3_opts.axis.y.label.text = data.resources.all[name].description;
    c3_opts.axis.y.label.position = 'outer-center';

    var chart = c3.generate(c3_opts);
}


function statusPerProvider(data) {
    var key = "";

    // Create a list of lists. Each list will start with the name of the
    // provider, as per c3's requirements.
    var providers = [];
    //This for-in loop works this way only for JSON objects. Otherwise, we
    //need to check if the key belongs to the object prototype.
    for (key in data.users) {
        providers.push([key]);
    }

    // Get list of user statuses (e.g. active, total, verified), and prepend it
    // with an 'x' that is necessary for c3.
    var statuses = ['x'];
    for (key in data.users.all) {
        statuses.push(key);
    }

    // Fill each provider list with the number of users that have a certain
    // status.
    for (var i = 1; i < statuses.length; i++)  {
        for (var j = 0; j < providers.length; j++)  {
            var provider = providers[j][0];
            var status = statuses[i];
            providers[j].push(data.users[provider][status]);
        }
    }

    //Prepend the providers lists with the status categories.
    providers.unshift(statuses);

    // Create logarithmic bar chart.
    var c3_opts = create_bar_chart(providers, true);
    c3_opts.bindto = '#provider-status';
    c3_opts.axis.y.label.text = 'Users (log scale)';
    c3_opts.axis.y.label.position = 'outer-middle';
    c3_opts.axis.x.label.text = 'Status categories';
    c3_opts.axis.x.label.position = 'outer-center';

    var chart = c3.generate(c3_opts);
}


function statusPerProviderReversed(data) {
    var key = "";

    // Get list of user statuses (e.g. active, total, verified), and prepend it
    // with an 'x' that is necessary for c3.
    var statuses = [];
    for (key in data.users.all) {
        statuses.push([key]);
    }

    // Create a list of lists. Each list will start with the name of the
    // provider, as per c3's requirements.
    var providers = ['x'];
    //This for-in loop works this way only for JSON objects. Otherwise, we
    //need to check if the key belongs to the object prototype.
    for (key in data.users) {
        providers.push(key);
    }

    // Fill each provider list with the number of users that have a certain
    // status.
    for (var i = 1; i < providers.length; i++)  {
        for (var j = 0; j < statuses.length; j++)  {
            var status = statuses[j][0];
            var provider = providers[i];
            statuses[j].push(data.users[provider][status]);
        }
    }

    //Prepend the providers lists with the status categories.
    statuses.unshift(providers);

    // Create logarithmic bar chart.
    var c3_opts = create_bar_chart(statuses, true);
    c3_opts.bindto = '#provider-status-reversed';
    c3_opts.axis.y.label.text = 'Users (log scale)';
    c3_opts.axis.y.label.position = 'outer-middle';
    c3_opts.axis.x.label.text = 'Providers';
    c3_opts.axis.x.label.position = 'outer-center';

    var chart = c3.generate(c3_opts);
}


function exclusiveProviders(data) {
    providers = data.providers.slice();
    var excl = ['Exclusive'];
    var non_excl = ['Non-exclusive'];

    for (var i = 0; i < providers.length; i++)  {
        var provider = providers[i];
        var prov_data = data.users[provider];

        var e = prov_data.exclusive;
        var ne = prov_data.active - prov_data.exclusive;

        excl.push(e);
        non_excl.push(ne);
    }
    //Prepend x label
    providers.unshift('x');

    c3_opts = create_stacked_chart(providers, excl, non_excl);
    c3_opts.bindto = '#provider-exclusiveness';
    c3_opts.axis.y.tick.format = d3.format("d");
    c3_opts.axis.y.label.text = 'Active Users';
    c3_opts.axis.y.label.position = 'outer-middle';
    c3_opts.axis.x.label.text = 'Providers';
    c3_opts.axis.x.label.position = 'outer-center';

    var chart = c3.generate(c3_opts);
}


function serverStatus(data) {
    var servers = data.servers;
    var server_data = [];
    var status = "";

    for (status in data.servers) {
        var count = servers[status].count;
        server_data.push([status.capitalize(), count]);
    }

    var c3_opts = create_pie_chart(server_data);
    c3_opts.bindto = "#server-status";
    var chart = c3.generate(c3_opts);
}


function ipPoolStatus(data) {
    var ip_pools = data.ip_pools;
    var status = "";

    var ip_data = [];
    for (status in ip_pools) {
        var ip_sp = ip_pools[status];
        var a = ip_sp.total - ip_sp.free;
        var f = ip_sp.free;

        ip_data.push([status.capitalize() + ' - Allocated', a]);
        ip_data.push([status.capitalize() + ' - Free', f]);
    }

    var c3_opts = create_pie_chart(ip_data);
    c3_opts.bindto = "#ip-pool-status";

    var chart = c3.generate(c3_opts);
}


function diskTemplates(data) {
    var servers = data.servers;
    var templates = {};

    for (var status in servers) {
        var disks = servers[status].disk;
        for (var key in disks) {
            if (!templates.hasOwnProperty(key)) {
                templates[key] = 0;
            }
            for (var flavor in disks[key]) {
                templates[key] += disks[key][flavor];
            }
        }
    }

    var disk_data = [];
    for (var t in templates) {
        if (!templates.hasOwnProperty(t)) {
            continue;
        }
        disk_data.push([t.capitalize(), templates[t]]);
    }

    var c3_opts = create_pie_chart(disk_data);
    c3_opts.bindto = "#disk-templates";

    var chart = c3.generate(c3_opts);
}


function imagesStats(data) {
    var images = data.images;

    var image_data = [];
    for (var i in images) {
        image_data.push([i.sanitize(), images[i]]);
    }

    var c3_opts = create_pie_chart(image_data);
    c3_opts.bindto = "#images";

    var chart = c3.generate(c3_opts);
}

$(document).ready(function() {
    sticker();
});
