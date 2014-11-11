$(document).ready(function() {
	var astakos_stats_url = $('#charts').data("astakos-stats");
	var cyclades_stats_url = $('#charts').data("cyclades-stats");
    var astakos_stats = {};
    var cyclades_stats = {};

    $.ajax({
        url: astakos_stats_url,
        type: 'GET',
        contentType: 'application/json',
        success: function(response, statusText, jqXHR) {
            astakos_stats = response;
            infraUsage(astakos_stats);
            for (var key in astakos_stats.resources.all) {
                resourceUsage(astakos_stats, key);
            }
            statusPerProvider(astakos_stats);
            statusPerProviderReversed(astakos_stats);
            exclusiveProviders(astakos_stats);
        },
        error: function(jqXHR, statusText) {
            console.log('error', statusText);
        }
    });

    $.ajax({
        url: cyclades_stats_url,
        type: 'GET',
        contentType: 'application/json',
        success: function(response, statusText, jqXHR) {
            cyclades_stats = response;
            serverStatus(cyclades_stats);
            ipPoolStatus(cyclades_stats);
            diskTemplates(cyclades_stats);
            imagesStats(cyclades_stats);
        },
        error: function(jqXHR, statusText) {
            console.log('error', statusText);
        }
    });

    // when page is loaded show charts whose sidebar a is active
    function display_charts_init(){
        $('.charts .sidebar a.active').each(function(){
            var el = $(this).attr('data-chart');
            $('.well').find('div[data-chart='+el+']').show();
        });
    }

    display_charts_init();

    $('.charts .sidebar a').click(function(e) {
        e.preventDefault();
        $(this).toggleClass('active');
        var el = $(this).attr('data-chart');
        $('.well').find('div[data-chart='+el+']').stop(true, false).slideToggle('slow');
    });
});
