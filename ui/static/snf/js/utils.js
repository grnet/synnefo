;(function(root){
    
    var root = root;
    var snf = root.synnefo = root.synnefo || {};
    
    snf.i18n = {};

    // Logging namespace
    var logging = snf.logging = snf.logging || {};

    // logger object
    var logger = logging.logger = function(ns, level){
        var levels = ["debug", "info", "error"];
        var con = window.console;
        
        this.level = level || synnefo.logging.level;
        this.ns = ns || "";

        this._log = function(lvl) {
            if (lvl >= this.level && con) {
                var args = Array.prototype.slice.call(arguments[1]);
                var level_name = levels[lvl];
                    
                if (this.ns) {
                    args = ["["+this.ns+"] "].concat(args);
                }

                log = con.log
                if (con[level_name])
                    log = con[level_name]

                try {
                    con && log.apply(con, Array.prototype.slice.call(args));
                } catch (err) {}
            }
        }

        this.debug = function() {
            var args = [0]; args.push.call(args, arguments);
            this._log.apply(this, args);
        }

        this.info = function() {
            var args = [1]; args.push.call(args, arguments);
            this._log.apply(this, args);
        }

        this.error = function() {
            var args = [2]; args.push.call(args, arguments);
            try {
                console.trace()
            } catch (err) {}
            this._log.apply(this, args);
        }

    };
    
    synnefo.collect_user_data = function() {
        var data = {}
        
        try {
            data.calls = synnefo.api.requests;
        } catch (err) { data.calls = err }
        try {
            data.errors = synnefo.api.errors;
        } catch (err) { data.errors = err }
        try {
            data.data = {};
        } catch (err) { data.data = err }
        try {
            data.data.vms = synnefo.storage.vms.toJSON();
        } catch (err) { data.data.vms = err }
        try {
            data.data.networks = synnefo.storage.vms.toJSON();
        } catch (err) { data.data.networks = err }
        try {
            data.data.images = synnefo.storage.images.toJSON();
        } catch (err) { data.data.images = err }
        try {
            data.data.flavors = synnefo.storage.flavors.toJSON();
        } catch (err) { data.data.flavors = err }
        try {
            data.date = new Date;
        } catch (err) { data.date = err }

        return data;
    }

    // default logger level (debug)
    synnefo.logging.level = 0;

    // generic logger
    synnefo.log = new logger({'ns':'SNF'});

    // synnefo config options
    synnefo.config = synnefo.config || {};
    synnefo.config.api_url = "/api/v1.1";
    
    // Util namespace
    synnefo.util = synnefo.util || {};

    // Extensions and Utility functions
    synnefo.util.ISODateString = function(d){
        function pad(n){
            return n<10 ? '0'+n : n
        }
         return d.getUTCFullYear()+'-'
         + pad(d.getUTCMonth()+1)+'-'
         + pad(d.getUTCDate())+'T'
         + pad(d.getUTCHours())+':'
         + pad(d.getUTCMinutes())+':'
         + pad(d.getUTCSeconds())+'Z'
    }

 
    synnefo.util.parseUri = function(sourceUri) {
        var uriPartNames = ["source","protocol","authority","domain","port","path","directoryPath","fileName","query","anchor"];
        var uriParts = new RegExp("^(?:([^:/?#.]+):)?(?://)?(([^:/?#]*)(?::(\\d*))?)?((/(?:[^?#](?![^?#/]*\\.[^?#/.]+(?:[\\?#]|$)))*/?)?([^?#/]*))?(?:\\?([^#]*))?(?:#(.*))?").exec(sourceUri);
        var uri = {};
        
        for(var i = 0; i < 10; i++){
            uri[uriPartNames[i]] = (uriParts[i] ? uriParts[i] : "");
        }
    
        // Always end directoryPath with a trailing backslash if a path was present in the source URI
        // Note that a trailing backslash is NOT automatically inserted within or appended to the "path" key
        if(uri.directoryPath.length > 0){
            uri.directoryPath = uri.directoryPath.replace(/\/?$/, "/");
        }
        
        return uri;
    }

    synnefo.util.equalHeights = function() {
        var max_height = 0;
        var selectors = _.toArray(arguments);
            
        _.each(selectors, function(s){
            console.log($(s).height());
        })
        // TODO: implement me
    }

    synnefo.util.ClipHelper = function(cont) {
        this.cont = cont || $('<div class="clip-copy"></div>');
        this.clip = new ZeroClipboard.Client();
        this.clip.setHandCursor(true);
        this.el = this.cont;
        this.el.append(this.clip.getHTML(20,20));

        this.setText = function(t) {
            this.clip.setText(t);
        }

        this.el.attr({title: "Click to copy to clipboard"})
        this.clip.addEventListener('complete', _.bind(function(client, text) {
            //$(".tooltip").text("Copied");
        }, this));
    }

    synnefo.util.truncate = function(string, size, append, words) {
        if (string.length <= size) {
            return string;
        }

        if (append === undefined) {
            append = "...";
        }
        
        if (!append) { append = "" };
        // TODO: implement word truncate
        if (words === undefined) {
            words = false;
        }
        
        len = size - append.length;
        return string.substring(0, len) + append;
    }

    synnefo.util.readablizeBytes = function(bytes) {
        var s = ['bytes', 'kb', 'MB', 'GB', 'TB', 'PB'];
        var e = Math.floor(Math.log(bytes)/Math.log(1024));
        return (bytes/Math.pow(1024, Math.floor(e))).toFixed(2)+" "+s[e];
    }
    
    synnefo.i18n.API_ERROR_MESSAGES = {
        'timeout': {
            'message': 'Timeout', 
            'allow_report': false
        },
        
        'error': {
            'message': 'API error'
        }, 

        'abort': {},
        'parserror': {}
    }
    
    synnefo.util.array_diff = function(arr1, arr2) {
        var removed = [];
        var added = [];

        _.each(arr1, function(v) {
            if (arr2.indexOf(v) == -1) {
                removed[removed.length] = v;
            }
        })


        _.each(arr2, function(v) {
            if (arr1.indexOf(v) == -1) {
                added[added.length] = v;
            }
        })

        return {del: removed, add: added};
    }

    synnefo.util.open_window = function(url, name, specs) {
        // default specs
        var opts = _.extend({
            scrollbars: 'no',
            menubar: 'no',
            toolbar: 'no',
            status: 'no',
            top: 'no',
            left: 'no',
            height: screen.height,
            width: screen.width,
            fullscreen: 'yes',
            channelmode: 'yes',
            directories: 'no',
            left: 0,
            location: 'no',
            top: 0
        }, opts)
        
        window.open(url, name, opts);
    }

    synnefo.util.stacktrace = function() {
        try {
            var obj = {};
            if (window.Error && Error.captureStackTrace) {
                Error.captureStackTrace(obj, synnefo.util.stacktrace);
                return obj.stack;
            } else {
                return printStackTrace().join("<br /><br />");
            }
        } catch (err) {}
        return "";
    },
    
    synnefo.util.array_combinations = function(arr) {
        if (arr.length == 1) {
            return arr[0];
        } else {
            var result = [];

            // recur with the rest of array
            var allCasesOfRest = synnefo.util.array_combinations(arr.slice(1));  
            for (var i = 0; i < allCasesOfRest.length; i++) {
                for (var j = 0; j < arr[0].length; j++) {
                    result.push(arr[0][j] + "-" + allCasesOfRest[i]);
                }
            }
            return result;
        }
    }

    synnefo.util.parse_api_error = function(arguments) {
        arguments = arguments[0];

        var xhr = arguments[0];
        var error_message = arguments[1];
        var error_thrown = arguments[2];
        var ajax_settings = arguments.ajax;
        var call_settings = arguments.ajax.error_params || {};

        var json_data = undefined;
        if (xhr.responseText) {
            try {
                json_data = JSON.parse(xhr.responseText)
            } catch (err) {}
        }
        
        module = "API"

        try {
            path = synnefo.util.parseUri(ajax_settings.url).path.split("/");
            path.splice(0,3)
            module = path.join("/");
        } catch (err) {
            console.error("cannot identify api error module");
        }

        defaults = {
            'message': 'Api error',
            'type': 'API',
            'allow_report': true
        }

        var code = -1;
        try {
            code = xhr.status || "undefined";
        } catch (err) {console.error(err);}
        var details = "";
        
        if ([413].indexOf(code) > -1) {
            defaults.non_critical = true;
            defaults.allow_report = false;
            defaults.allow_reload = false;
        }
        
        if (json_data) {
            $.each(json_data, function(key, obj) {
                code = obj.code;
                details = obj.details.replace("\n","<br>");
                error_message = obj.message;
            })
        }
        
        extra = {'URL': ajax_settings.url};
        options = {};
        options = _.extend(options, {'details': details, 'message': error_message, 'ns': module, 'extra_details': extra});
        options = _.extend(options, call_settings);
        options = _.extend(options, synnefo.i18n.API_ERROR_MESSAGES[error_message] || {});
        options = _.extend(defaults, options);
        options.code = code;

        return options;
    }


    // Backbone extensions
    //
    // super method
    Backbone.Model.prototype._super = Backbone.Collection.prototype._super = Backbone.View.prototype._super = function(funcName){
        return this.constructor.__super__[funcName].apply(this, _.rest(arguments));
    }

    // simple string format helper 
    // http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format
    String.prototype.format = function() {
        var formatted = this;
        for (var i = 0; i < arguments.length; i++) {
            var regexp = new RegExp('\\{'+i+'\\}', 'gi');
            formatted = formatted.replace(regexp, arguments[i]);
        }
        return formatted;
    };


    $.fn.setCursorPosition = function(pos) {
        if ($(this).get(0).setSelectionRange) {
          $(this).get(0).setSelectionRange(pos, pos);
        } else if ($(this).get(0).createTextRange) {
          var range = $(this).get(0).createTextRange();
          range.collapse(true);
          range.moveEnd('character', pos);
          range.moveStart('character', pos);
          range.select();
        }
    }
})(this);
