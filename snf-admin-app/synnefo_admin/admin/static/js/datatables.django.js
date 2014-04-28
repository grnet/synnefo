(function($) {

    "use strict";

    /**
     * Parse French date in the following format: dd/mm/YYYY HH:MM
     */
    function parseDateFR(str) {
        if ($.trim(str)) {
            var dParts = $.trim(str).split(' ')[0].split('/');
            var tParts = $.trim(str).split(' ')[1].split(':');
            return new Date(dParts[2], dParts[1]-1, dParts[0], tParts[0], tParts[1]);
        }
        return null;
    }

    $.extend( $.fn.dataTableExt.oSort, {
        /*
         * French date sorting.
         */
        'date-fr-pre': function(a) {
            return parseDateFR(a) || new Date(0);
        },

        'date-fr-asc': function(a, b) {
            return a.getTime() - b.getTime();
        },

        'date-fr-desc': function(a, b) {
            return b.getTime() - a.getTime();
        },

        /*
         * html numeric sorting (ignore html tags)
         */
        'html-num-pre': function ( a ) {
            return a.replace( /<.*?>/g, "" ).toLowerCase();
        },

        'html-num-asc': function ( x, y ) {
            return x - y;
        },

        'html-num-desc': function ( x, y ) {
            return y - x;
        }
    });


})(window.jQuery);
