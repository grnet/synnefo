/*$(document).ready(function() {

// 	function drawChart() {
// 		google.load("visualization", "1", {packages:["corechart"]});
// 		google.setOnLoadCallback(initialize);
// 	    var data = google.visualization.arrayToDataTable([
// 	        ['Account State', 'Number'],
// 	        ['Active',     50],
// 	        ['Other',      200]
// 	    ]);

//     var options = {
//         title: 'Test',
//         is3D: true
//     };

//     var chart = new google.visualization.PieChart(document.getElementById('pie-active-users'));
//     chart.draw(data, options);
// }

	if($('#pie-active-users').length>0) {
      function drawChart() {
      	console.log('hi')
        var data = google.visualization.arrayToDataTable([
          ['Task', 'Hours per Day'],
          ['Work',     11],
          ['Eat',      2],
          ['Commute',  2],
          ['Watch TV', 2],
          ['Sleep',    7]
        ]);
      google.load("visualization", "1", {packages:["corechart"], callback: 'drawChart'});
      google.setOnLoadCallback(drawChart);

        var options = {
          title: 'My Daily Activities'
        };

        var chart = new google.visualization.PieChart($('#pie-active-users'));
        chart.draw(data, options);
      }


}
});*/


$(document).ready(function(){
	if($('#chartdiv').length > 0) {
		// var statsData;
		$.getJSON( "/stats/", function( statsData ) {			
			var usersActive = statsData.astakos.users.active;
			var usersTotal = statsData.astakos.users.total;
			var usersNotActive = usersTotal - usersActive; 
		    var data = [
			    ['Active', usersActive],['Other', usersNotActive]
			];
			var plot1 =jQuery.jqplot ('chartdiv', [data], 
		    { 
		      seriesDefaults: {
		        // Make this a pie chart.
		        renderer: jQuery.jqplot.PieRenderer, 
		        rendererOptions: {
		          // Put data labels on the pie slices.
		          // By default, labels show the percentage of the slice.
		          showDataLabels: true
		        }
			  }, 
		      legend: { show:true, location: 'e' }
		    }
		  );
				
		});

	}
});