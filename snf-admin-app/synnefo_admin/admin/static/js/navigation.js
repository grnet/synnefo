$(document).ready(function() {
console.log('navigation.js')

var curPath = window.location.pathname;

function showCurrentPlace() {
	var pathArray = curPath.split('/');
	
	$('.main-nav li').each(function () {
		var pointer ='<div class="arrow-pointer"><div class="point arrow-up-outer"></div><div class="point arrow-up-inner"></div></div>';
		// console.log($(this).find('a').attr('href'))
		if($(this).find('a').attr('href') === curPath) {
			if($(this).closest('ul').hasClass('dropdown-menu')) {
				$(this).closest('ul').closest('li').append(pointer);
				$(this).closest('li').addClass('active');
				$(this).closest('ul').closest('li').addClass('active');
			}
			else {
				$(this).closest('li').append(pointer)
				$(this).closest('li').addClass('active');

			}
			
		}
		else if('/'+pathArray[1]+'/'+pathArray[2] === $(this).find('a').attr('href')) { // sumvasi! ***
			console.log('eimai se details')
			$(this).closest('li').append(pointer)
			$(this).closest('li').addClass('active');
		}
		else {
				// console.log(pathArray)
			$(this).closest('li').remove('.arrow-pointer');
			$(this).closest('li').removeClass('active');
		}
	});
	
};

function updateBreadcrumb() {
	// var pathArray = curPath.split('/');
	// var nodesNum = pathArray.length;
	// for (var i=1; i<nodesNum; i++) {
	// 	console.log(pathArray[i])
	// 	if(pathArray[i] !== "admin") {
			
	// 	}
	// }


}

showCurrentPlace();
updateBreadcrumb();



})