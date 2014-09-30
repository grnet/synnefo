/* To avoid CSS expressions while still supporting IE 7 and IE 6, use this script */
/* The script tag referring to this file must be placed before the ending body tag. */

/* Use conditional comments in order to target IE 7 and older:
	<!--[if lt IE 8]><!-->
	<script src="ie7/ie7.js"></script>
	<!--<![endif]-->
*/

(function() {
	function addIcon(el, entity) {
		var html = el.innerHTML;
		el.innerHTML = '<span style="font-family: \'font-icons\'">' + entity + '</span>' + html;
	}
	var icons = {
		'snf-envelope': '&#x63;',
		'snf-ok': '&#x61;',
		'snf-remove': '&#x62;',
		'snf-exclamation-sign': '&#x67;',
		'snf-envelope-alt': '&#x64;',
		'snf-angle-up': '&#x65;',
		'snf-angle-down': '&#x66;',
		'0': 0
		},
		els = document.getElementsByTagName('*'),
		i, c, el;
	for (i = 0; ; i += 1) {
		el = els[i];
		if(!el) {
			break;
		}
		c = el.className;
		c = c.match(/snf-[^\s'"]+/);
		if (c && icons[c[0]]) {
			addIcon(el, icons[c[0]]);
		}
	}
}());
