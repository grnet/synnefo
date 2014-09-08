         $(document).ready(function() {
         	Highcharts.setOptions({colors: ['#00BC8C', '#f45b5b', '#f7a35c', '#858585', '#64E572', '#FF9655', '#FFF263', '#6AF9C4']});
         	
	// 	first colors: green, red, orange, gray
	// 	i can put color in each data object
         	
	// 		// drilldown
 //            Highcharts.data({
 //        csv: document.getElementById('tsv').innerHTML,
 //        itemDelimiter: '\t',
 //        parsed: function (columns) {

 //            var brands = {},
 //                brandsData = [],
 //                versions = {},
 //                drilldownSeries = [];
            
 //            // Parse percentage strings
 //            columns[1] = $.map(columns[1], function (value) {
 //                if (value.indexOf('%') === value.length - 1) {
 //                    value = parseFloat(value);
 //                }
 //                return value;
 //            });

 //            $.each(columns[0], function (i, name) {
 //                var brand,
 //                    version;

 //                if (i > 0) {

 //                    // Remove special edition notes
 //                    name = name.split(' -')[0];

 //                    // Split into brand and version
 //                    version = name.match(/([0-9]+[\.0-9x]*)/);
 //                    if (version) {
 //                        version = version[0];
 //                    }
 //                    brand = name.replace(version, '');

 //                    // Create the main data
 //                    if (!brands[brand]) {
 //                        brands[brand] = columns[1][i];
 //                    } else {
 //                        brands[brand] += columns[1][i];
 //                    }

 //                    // Create the version data
 //                    if (version !== null) {
 //                        if (!versions[brand]) {
 //                            versions[brand] = [];
 //                        }
 //                        versions[brand].push(['v' + version, columns[1][i]]);
 //                    }
 //                }
                
 //            });

 //            $.each(brands, function (name, y) {
 //                brandsData.push({ 
 //                    name: name, 
 //                    y: y,
 //                    drilldown: versions[name] ? name : null
 //                });
 //            });
 //            $.each(versions, function (key, value) {
 //                drilldownSeries.push({
 //                    name: key,
 //                    id: key,
 //                    data: value
 //                });
 //            });

 //            // Create the chart
 //            $('#container2').highcharts({
 //                chart: {
 //                    type: 'pie'
 //                },
 //                title: {
 //                    text: 'Browser market shares. November, 2013.'
 //                },
 //                subtitle: {
 //                    text: 'Click the slices to view versions. Source: netmarketshare.com.'
 //                },
 //                plotOptions: {
 //                    series: {
 //                        dataLabels: {
 //                            enabled: true,
 //                            format: '{point.name}: {point.y:.1f}%'
 //                        }
 //                    }
 //                },

 //                tooltip: {
 //                    headerFormat: '<span style="font-size:11px">{series.name}</span><br>',
 //                    pointFormat: '<span style="color:{point.color}">{point.name}</span>: <b>{point.y:.2f}%</b> of total<br/>'
 //                }, 

 //                series: [{
 //                    name: 'Brands',
 //                    colorByPoint: true,
 //                    data: brandsData
 //                }],
 //                drilldown: {
 //                    series: drilldownSeries
 //                }
 //            })

 //        }
 //    });

         // simple
         $('#container1').highcharts({
        chart: {
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false
        },
        title: {
            text: 'Accounts State'
        },
        tooltip: {
        	headerFormat: '<span>{point.key} Accounts</span><br/>',
    	    pointFormat: 'Population: {point.num}'
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
            type: 'pie',
            name: 'Accounts',
            data: [
                {
                    name: 'Active',
                    y: 63.2,
                    sliced: true,
                    selected: true,
                    num: 3000,
                    drilldown: 'providers-act'
                },
                {
                	name: 'Inactive',
                	y:   2.4,
                	num: 100,
                    drilldown: 'providers-inact'
                },
                {
                	name: 'Pending Moderation',
                	y: 27.1,
                	num: 700,
                    drilldown: 'providers-pMod'
                },
                {
                	name: 'Pending Verification',
                	y: 7.3,
                	num: 300,
                    drilldown: 'providers-pVer'
                },
                
            ]
        }],
        drilldown: {
        	series: [
        	{
        		id: 'providers-act',
        		data: [
        		{
        			name: 'Shibboleth',
        			y: 60
        		},
        		{
        			name: 'Local',
        			y: 40
        		}]
        	},
        	{
        		id: 'providers-inact',
        		data: [
        		{
        			name: 'Shibboleth',
        			y: 10
        		},
        		{
        			name: 'Local',
        			y: 90
        		}]
        	},
        	{
        		id: 'providers-pMod',
        		data: [
        		{
        			name: 'Shibboleth',
        			y: 0
        		},
        		{
        			name: 'Local',
        			y: 100
        		}]
        	},
        	{
        		id: 'providers-pVer',
        		data: [
        		{
        			name: 'Shibboleth',
        			y: 20
        		},
        		{
        			name: 'Local',
        			y: 80
        		}]
        	},
        	]
        }
    });

	// /*
	// Notes:
	// - the series.data should be placed in this order so each pie-piece to have the right color (eg active <- green)
	// - I want the tooltip to have the raw number of population se I added "property"
	//  - The plan is to create series.data form the accountsData func that will take as parameter an array of objs like accounts
	// */
 //     function accountsData() {

 //     }
 //     var accounts = [
 //     {
 //     	state: 'Active',
 //     	population: 1000,
 //     	percentage: 0
 //     },
 //     {
 //     	state: 'Inactive',
 //     	population: 10,
 //     	percentage: 0
 //     },
 //     {
 //     	state: 'Pending Verification',
 //     	population: 300,
 //     	percentage: 0
 //     },
 //     {
 //     	state: 'Pending Moderation',
 //     	population: 700,
 //     	percentage: 0
 //     }]

         });

//  $(function () {

//     Highcharts.data({
//         csv: document.getElementById('tsv').innerHTML,
//         itemDelimiter: csv.split,
//         parsed: function (columns) {
//         	cols = columns
//         	console.log(columns);
//             var brands = {},
//                 brandsData = [],
//                 versions = {},
//                 drilldownSeries = [];
//             console.log('now crash')
//             // Parse percentage strings
//             columns[1] = $.map(columns[1], function (value) {
//                 if (value.indexOf('%') === value.length - 1) {
//                     value = parseFloat(value);
//                 }
//                 return value;
//             });
//             console.log('/now crash')

//             $.each(columns[0], function (i, name) {
//                 var brand,
//                     version;

//                 if (i > 0) {

//                     // Remove special edition notes
//                     name = name.split(' -')[0];

//                     // Split into brand and version
//                     version = name.match(/([0-9]+[\.0-9x]*)/);
//                     if (version) {
//                         version = version[0];
//                     }
//                     brand = name.replace(version, '');

//                     // Create the main data
//                     if (!brands[brand]) {
//                         brands[brand] = columns[1][i];
//                     } else {
//                         brands[brand] += columns[1][i];
//                     }

//                     // Create the version data
//                     if (version !== null) {
//                         if (!versions[brand]) {
//                             versions[brand] = [];
//                         }
//                         versions[brand].push(['v' + version, columns[1][i]]);
//                     }
//                 }
                
//             });

//             $.each(brands, function (name, y) {
//                 brandsData.push({ 
//                     name: name, 
//                     y: y,
//                     drilldown: versions[name] ? name : null
//                 });
//             });
//             $.each(versions, function (key, value) {
//                 drilldownSeries.push({
//                     name: key,
//                     id: key,
//                     data: value
//                 });
//             });

//             // Create the chart
//             $('#container2').highcharts({
//                 chart: {
//                     type: 'pie'
//                 },
//                 title: {
//                     text: 'Browser market shares. November, 2013.'
//                 },
//                 subtitle: {
//                     text: 'Click the slices to view versions. Source: netmarketshare.com.'
//                 },
//                 plotOptions: {
//                     series: {
//                         dataLabels: {
//                             enabled: true,
//                             format: '{point.name}: {point.y:.1f}%'
//                         }
//                     }
//                 },

//                 tooltip: {
//                     headerFormat: '<span style="font-size:11px">{series.name}</span><br>',
//                     pointFormat: '<span style="color:{point.color}">{point.name}</span>: <b>{point.y:.2f}%</b> of total<br/>'
//                 }, 

//                 series: [{
//                     name: 'Brands',
//                     colorByPoint: true,
//                     data: brandsData
//                 }],
//                 drilldown: {
//                     series: drilldownSeries
//                 }
//             })

//         }
//     });
// });
    