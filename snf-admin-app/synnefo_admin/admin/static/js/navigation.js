$(document).ready(function() {
console.log('navigation.js')

var curPath = window.location.pathname;

function showCurrentPlace() {
	var pathArray = curPath.split('/');
	
	$('.main-nav li').each(function () {

		if($(this).find('a').attr('href') === curPath) {
			if($(this).closest('ul').hasClass('dropdown-menu')) {
				$(this).closest('li').addClass('active');
				$(this).closest('ul').closest('li').addClass('active');
			}
			else {
				$(this).closest('li').addClass('active');

			}
			
		}
		else if('/'+pathArray[1]+'/'+pathArray[2] === $(this).find('a').attr('href')) { // sumvasi! ***
			$(this).closest('li').addClass('active');
		}
		else {
			$(this).closest('li').removeClass('active');
		}
	});
};

showCurrentPlace();

$('.sub-nav li:last-child').click(function(e) {
	e.preventDefault();
})

});