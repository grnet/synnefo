$(document).ready(function() {
	Highcharts.setOptions({colors: ['#00BC8C', '#f45b5b', '#f7a35c', '#858585', '#64E572', '#FF9655', '#FFF263', '#6AF9C4']});
	// with drilldown
	$('#pie-drilldown').highcharts({
	chart: {
			plotBackgroundColor: null,
			plotBorderWidth: null,
			plotShadow: false,
			type: 'pie'
		},
		title: {
			text: 'Accounts State'
		},
		subtitle: {
			text: "Click the slices to view the authentication methods of each category"
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
			// type: 'pie',
			name: 'Accounts' ,
			data: 
				[{
					name: 'Active',
					y: 63.2,
					// sliced: true,
					// selected: true,
					num: 3000,
					drilldown: 'providers-act'
				},
				{
					name: 'Inactive',
					y:   2.4,
					drilldown: 'providers-inact',
					num: 100,
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
				}]
		}],
		drilldown: {
			series: 
				[{
					id: 'providers-act',
					data: [
						{
							name: 'Shibboleth',
							y: 60 // percentage is per parent-slice (60% of active accounts are shibboleth)
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
				}]
		}
	});




$('#pie-simple').highcharts({
	chart: {
			plotBackgroundColor: null,
			plotBorderWidth: null,
			plotShadow: false,
			type: 'pie'
		},
		title: {
			text: 'Servers Status'
		},
		subtitle: {
			text: "Data Last update: 12/12/2012 01.00"
		},
		tooltip: {
			headerFormat: '<span>{point.key} Servers</span><br/>',
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
			// type: 'pie',
			name: 'Servers' ,
			data: 
				[{
					name: 'Started',
					y: 45,
					// sliced: true,
					// selected: true,
					num: 2250
				},
				{
					name: 'Error',
					y:   5,
					num: 250,
				},
				{
					name: 'Stopped',
					y: 50,
					num: 2500,
					color: '#858585'
				}]
		}]
	});


	/*
	Notes:
	- the series.data should be placed in this order so each pie-slice to have the right color (eg active <- green)
	- I want the tooltip to have the raw number of population se I added "property"
	- The plan is to create series.data form the accountsData func that will take as parameter an array of objs like accounts
	*/
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
