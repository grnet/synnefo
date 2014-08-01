function humanize(value, unit) {
    if (!unit) {
        return value;
    }

    var units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];

    var i = 0;
    while (value >= 1024) {
        i++;
        value = value / 1024;
    }

    return Math.floor(value) + ' ' + units[i];
}

function percentify(value, total) {
    return Math.floor(100 * (value / total));
}

String.prototype.capitalize = function() {
        return this.charAt(0).toUpperCase() + this.slice(1);
}

String.prototype.sanitize = function() {
    new_string = ""
    for (var i = 0, len = this.length; i < len; i++) {
        c = this.charAt(i);
        if (/^[a-zA-Z0-9]$/.test(c)) {
            new_string += c;
        } else if (/^[\.\-\_\:\~]$/.test(c)) {
            new_string += c;
        } else {
            new_string += "_"; // replace it with a safe character
        }
    }
    return new_string;
}

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

    var displayed_categories = [];
    var used = [];
    var free = [];

    for (key in categories) {
        // why do we need it?
        if (!categories.hasOwnProperty(key)) {
            continue; // jumps over one iteration
        }

        displayed_categories.push(categories[key]);

        resource = data['resources']['all'][key];
        var u  = resource['used'];
        var f  = resource['allocated'] - resource['used'];
        var unit  = resource['unit'];

        var usedData = {
            'y': u,
            'human': humanize(u, unit),
        };

        var freeData = {
            'y': f,
            'human': humanize(f, unit),
        };

        used.push(usedData);
        free.push(freeData);
    }

    $('#infra-usage').highcharts({
        chart: {
            type: 'column'
        },
        title: {
            text: 'Total resource usage'
        },
        xAxis: {
            categories: displayed_categories
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Usage percentage'
            },
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.human}</b> ({point.percentage:.0f}%)<br/>',
            shared: true
        },
        plotOptions: {
            column: {
                stacking: 'percent'
            }
        },
        series: [{
            name: 'Free',
            data: free,
        }, {
            name: 'Used',
            data: used,
        }]
    });
}

function resourceUsage(data, name) {
    var domID = 'recource-'+name.replace(/\./gi, '_');
    $('#resource-usage').append('<div id="'+domID+'"></div>')

    var providers = data['providers'];
    var used = [];
    var free = [];

    for (var i = 0; i < providers.length; i++)  {
        provider = providers[i];

        resource = data['resources'][provider][name];
        var u  = resource['used'];
        var f  = resource['allocated'] - resource['used'];
        var unit  = resource['unit'];

        var usedData = {
            'y': u,
            'human': humanize(u, unit),
        };

        var freeData = {
            'y': f,
            'human': humanize(f, unit),
        };

        used.push(usedData);
        free.push(freeData);
    }
    $('#'+domID).highcharts({
        chart: {
            type: 'bar'
        },
        title: {
            text: name + ' usage per provider'
        },
        xAxis: {
            categories: providers
        },
        yAxis: {
            min: 0,
            title: {
                text: data['resources']['all'][name]['description'],
            },
        },
        legend : {
            reversed: true,
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.human}</b><br/>',
            shared: true
        },
        plotOptions: {
            series: {
                stacking: 'normal'
            }
        },
        series: [{
            name: 'Free',
            data: free,
        }, {
            name: 'Used',
            data: used,
        }]
    });
}


function statusPerProvider(data) {
    var providers = [];
    // This for-in loop works this way only for JSON objects. Otherwise, we
    // need to check if the key belongs to the object prototype.
    for (key in data['users']) {
        providers.push(key);
    }

    var statuses = [];
    for (key in data['users']['all']) {
        statuses.push(key);
    }

    var provider_status_data = [];
    for (var i = 0; i < providers.length; i++)  {
        var provider = providers[i];
        var status_array = [];

        for (var j = 0; j < statuses.length; j++) {
            var status = statuses[j];
            status_array.push(data['users'][provider][status]);
        }

        var statusData = {
            name: provider,
            data: status_array,
        };

        provider_status_data.push(statusData);
    }

    $('#provider-status').highcharts({
        chart: {
            type: 'column'
        },
        title: {
            text: 'User status per provider'
        },
        xAxis: {
            categories: statuses
        },
        yAxis: {
            //min: 0,
            title: {
                text: 'Users (log scale)'
            },
            type: 'logarithmic',
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b><br/>',
            shared: true
        },
        series: provider_status_data
    });
}

function statusPerProviderReversed(data) {
    var providers = [];
    // This for-in loop works this way only for JSON objects. Otherwise, we
    // need to check if the key belongs to the object prototype.
    for (key in data['users']) {
        providers.push(key);
    }

    var statuses = [];
    for (key in data['users']['all']) {
        statuses.push(key);
    }

    var provider_status_data_rev = [];
    for (var i = 0; i < statuses.length; i++)  {
        var status = statuses[i];
        var providers_array = [];

        for (var j = 0; j < providers.length; j++) {
            var provider = providers[j];
            providers_array.push(data['users'][provider][status]);
        }

        var statusData = {
            name: status,
            data: providers_array,
        };

        provider_status_data_rev.push(statusData);
    }

    $('#provider-status-reversed').highcharts({
        colors: ['#5cb85c', '#058DC7', '#f0ad4e', '#DDDF00', '#24CBE5', '#64E572','#FF9655', '#FFF263', '#6AF9C4'],
        chart: {
            type: 'column'
        },
        title: {
            text: 'Providers per user status'
        },
        xAxis: {
            categories: providers
        },
        yAxis: {
            //min: 0,
            title: {
                text: 'Users (log scale)'
            },
            type: 'logarithmic',
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b><br/>',
            shared: true
        },
        series: provider_status_data_rev
    });
}

function exclusiveProviders(data) {
    providers = data['providers']
    var excl = [];
    var non_excl = [];

    for (var i = 0; i < providers.length; i++)  {
        var provider = providers[i];
        var prov_data = data['users'][provider];

        var e  = prov_data['exclusive'];
        var ne  = prov_data['active'] - prov_data['exclusive'];

        excl.push(e);
        non_excl.push(ne);
    }

    $('#provider-exclusiveness').highcharts({
        chart: {
            type: 'column'
        },
        title: {
            text: 'Exclusive users per Provider'
        },
        xAxis: {
            categories: providers
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Active users'
            },
            stackLabels: {
                enabled: true,
                style: {
                    fontWeight: 'bold',
                    color: (Highcharts.theme && Highcharts.theme.textColor) || 'gray'
                }
            },
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b><br/>',
            shared: true
        },
        plotOptions: {
            series: {
                stacking: 'normal'
            }
        },
        series: [{
            name: 'Exclusive',
            data: excl,
        }, {
            name: 'Non-exclusive',
            data: non_excl,
        }]
    });
}

function serverStatus(data) {
    var total_servers = 0;
    var servers = data['servers'];
    for (status in servers) {
        total_servers += servers[status]['count'];
    }

    var server_data = [];
    for (status in data['servers']) {
        var count = servers[status]['count'];
        var statusData = {
            name: status.capitalize(),
            y: percentify(count, total_servers),
            num: count,
        }

        if (status === 'started') {
            statusData.sliced = true;
            statusData.selected = true;
        }

        server_data.push(statusData);
    }

    $('#server-status').highcharts({
        chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'Servers Status'
            },
            tooltip: {
                headerFormat: '<span>{point.key} Servers</span><br/>',
                pointFormat: 'Number: {point.num}'
            },
            plotOptions: {
                pie: {
                    allowPointSelect: true,
                    cursor: 'pointer',
                    dataLabels: {
                        enabled: true,
                        format: '<b>{point.name}: {point.percentage:.1f} %</b>',
                        style: {
                            colors: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                        }
                    }
                }
            },
            series: [{
                name: 'Servers' ,
                data: server_data
            }]
        });
}

function ipPoolStatus(data) {
    var ip_pools = data['ip_pools'];

    var total_ips = 0;
    for (status in ip_pools) {
        total_ips += ip_pools[status]['total'];
    }

    ip_data = [];
    for (status in ip_pools) {
        var ip_sp = ip_pools[status];
        var a = ip_sp['total'] - ip_sp['free'];
        var f = ip_sp['free'];
        var a_percent = percentify(a, total_ips);
        var f_percent = percentify(f, total_ips);

        var ipData = {
            name: status.capitalize() + ' - Allocated',
            y: a_percent,
            num: a,
        }
        if (status === 'active') {
            ipData.sliced = true;
            ipData.selected = true;
        }
        ip_data.push(ipData);

        var ipData = {
            name: status.capitalize() + ' - Free',
            y: f_percent,
            num: f,
        }
        ip_data.push(ipData);
    }

    $('#ip-pool-status').highcharts({
        chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'IP Allocation Status'
            },
            tooltip: {
                headerFormat: '<span>{point.key} IPs</span><br/>',
                pointFormat: 'Number: {point.num}'
            },
            plotOptions: {
                pie: {
                    allowPointSelect: true,
                    cursor: 'pointer',
                    dataLabels: {
                        enabled: true,
                        format: '<b>{point.name}: {point.percentage:.1f} %</b>',
                        style: {
                            colors: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                        }
                    }
                }
            },
            series: [{
                name: 'IPs' ,
                data: ip_data
            }]
        });
}

function diskTemplates(data) {
    var servers = data['servers'];
    var total_disks = 0;
    var templates = {};
    for (status in servers) {
        var disks = servers[status]['disk'];
        for (key in disks) {
            if (!templates.hasOwnProperty(key)) {
                templates[key] = 0;
            }
            for (flavor in disks[key]) {
                templates[key] += disks[key][flavor];
                total_disks += disks[key][flavor];
            }
        }
    }

    var disk_data = []
    for (t in templates) {
        if (!templates.hasOwnProperty(t)) {
            continue;
        }
        var diskData = {
            name: t.capitalize(),
            y: percentify(templates[t], total_disks),
            num: templates[t],
        }

        disk_data.push(diskData);
    }

    $('#disk-templates').highcharts({
        chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'Disk templates'
            },
            tooltip: {
                headerFormat: '<span>{point.key} Template</span><br/>',
                pointFormat: 'Number: {point.num}'
            },
            plotOptions: {
                pie: {
                    allowPointSelect: true,
                    cursor: 'pointer',
                    dataLabels: {
                        enabled: true,
                        format: '<b>{point.name}: {point.percentage:.1f} %</b>',
                        style: {
                            colors: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                        }
                    }
                }
            },
            series: [{
                name: 'Disk templates' ,
                data: disk_data,
            }]
        });
}

function imagesStats(data) {
    var images = data['images'];
    var total_images = 0;

    for (i in images) {
        total_images += images[i];
    }

    var image_data = [];
    for (i in images) {
        var imageData = {
            name: i.sanitize(), // Sanitize user input aggressively
            y: percentify(images[i], total_images),
            num: images[i],
        }

        image_data.push(imageData);
    }

    $('#images').highcharts({
        chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'VMs from Images'
            },
            tooltip: {
                headerFormat: '<span>{point.key} Image</span><br/>',
                pointFormat: 'Number: {point.num}'
            },
            plotOptions: {
                pie: {
                    allowPointSelect: true,
                    cursor: 'pointer',
                    dataLabels: {
                        enabled: true,
                        format: '<b>{point.name}: {point.percentage:.1f} %</b>',
                        style: {
                            colors: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                        }
                    }
                }
            },
            series: [{
                name: 'Images' ,
                data: image_data,
            }]
        });
}


$(document).ready(function() {
    sticker();
});
