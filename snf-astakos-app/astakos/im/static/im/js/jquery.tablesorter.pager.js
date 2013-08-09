(function($) {
    $.extend({
        tablesorterPager: new function() {


            // this function renders upon initialization
            function updatePageDisplay(c,table) {
                checkDisabled(table);
                /*
                The following line has been added to provide page display
                info on non input form elements
                */
                $(c.cssPageDisplay).html((c.page+1) + c.seperator + c.totalPages);
                var s = $(c.cssPageDisplay,c.container).val((c.page+1) + c.seperator + c.totalPages);

            }

            function setPageSize(table,size) {
                var c = table.config;
                c.size = size;
                c.totalPages = Math.ceil(c.totalRows / c.size);
                c.pagerPositionSet = false;
                moveToPage(table);
                fixPosition(table);
            }

            function fixPosition(table) {
                var c = table.config;
                if(!c.pagerPositionSet && c.positionFixed) {
                    var c = table.config, o = $(table);
                    if(o.offset) {
                        c.container.css({
                            top: o.offset().top + o.height() + 'px',
                            position: 'absolute'
                        });
                    }
                    c.pagerPositionSet = true;
                }
            }

            function checkDisabled(table) {

                var c = table.config;
                if (c.page == (c.totalPages-1)) {
                    $(config.cssNext).addClass('disabled');
                } else {
                    $(config.cssNext).removeClass('disabled');
                }
                if (c.page == 0) {
                    $(config.cssPrev).addClass('disabled');
                } else {
                    $(config.cssPrev).removeClass('disabled');
                }


            }


            function moveToFirstPage(table) {
                var c = table.config;
                c.page = 0;
                moveToPage(table);
            }

            function moveToLastPage(table) {
                var c = table.config;
                c.page = (c.totalPages-1);
                moveToPage(table);
            }

            function moveToNextPage(table) {
                var c = table.config;
                c.page++;
                if(c.page >= (c.totalPages-1)) {
                    c.page = (c.totalPages-1);
                }
                moveToPage(table);
            }

            function moveToPrevPage(table) {
                var c = table.config;
                c.page--;
                if(c.page <= 0) {
                    c.page = 0;
                }
                moveToPage(table);
            }


            function moveToPage(table) {
                var c = table.config;
                if(c.page < 0 || c.page > (c.totalPages-1)) {
                    c.page = 0;
                }
                renderTable(table,c.rowsCopy);
            }

            function renderTable(table,rows) {

                var c = table.config;
                var l = rows.length;
                var s = (c.page * c.size);
                var e = (s + c.size);
                if(e > rows.length ) {
                    e = rows.length;
                }


                var tableBody = $(table.tBodies[0]);

                // clear the table body

                $.tablesorter.clearTableBody(table);

                for(var i = s; i < e; i++) {

                    //tableBody.append(rows[i]);

                    var o = rows[i];
                    var l = o.length;
                    for(var j=0; j < l; j++) {

                        tableBody[0].appendChild(o[j]);

                    }
                }

                fixPosition(table,tableBody);

                $(table).trigger("applyWidgets");

                if( c.page >= c.totalPages ) {
                    moveToLastPage(table);
                }

                updatePageDisplay(c,table);
            }

            this.appender = function(table,rows) {

                var c = table.config;

                c.rowsCopy = rows;
                c.totalRows = rows.length;
                c.totalPages = Math.ceil(c.totalRows / c.size);

                renderTable(table,rows);
            };

            this.defaults = {
                size: 10,
                offset: 0,
                page: 0,
                totalRows: 0,
                totalPages: 0,
                container: null,
                cssNext: '.next',
                cssPrev: '.prev',
                cssFirst: '.first',
                cssLast: '.last',
                cssPageDisplay: '.pagedisplay',
                cssPageSize: '.pagesize',
                seperator: "/",
                positionFixed: true,
                appender: this.appender
            };

            this.construct = function(settings) {

                return this.each(function() {

                    config = $.extend(this.config, $.tablesorterPager.defaults, settings);

                    var table = this, pager = config.container;

                    $(this).trigger("appendCache");


                    /*

                    If uncommented the plugin does not function properly
                    when page size select is not present on the page.

                    */
                    //config.size = parseInt($(".pagesize",pager).val());

                    $(config.cssFirst,pager).click(function() {
                        moveToFirstPage(table);
                        return false;
                    });
                    $(config.cssNext,pager).click(function() {
                        moveToNextPage(table);
                        return false;
                    });
                    $(config.cssPrev,pager).click(function() {
                        moveToPrevPage(table);
                        return false;
                    });
                    $(config.cssLast,pager).click(function() {
                        moveToLastPage(table);
                        return false;
                    });
                    $(config.cssPageSize,pager).change(function() {
                        setPageSize(table,parseInt($(this).val()));
                        return false;
                    });
                });
            };

        }
    });
    // extend plugin scope
    $.fn.extend({
        tablesorterPager: $.tablesorterPager.construct
    });

})(jQuery);
