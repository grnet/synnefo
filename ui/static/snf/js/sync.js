;(function(root){
    
    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var sync = snf.sync = snf.sync || {};
    var api = snf.api = snf.api || {};

    // shortcuts
    var bb = Backbone;

    // logging
    var logger = new snf.logging.logger("SNF-API");
    var debug = _.bind(logger.debug, logger)
    
    // method map
    var methodMap = {
        'create': 'POST',
        'update': 'PUT',
        'delete': 'DELETE',
        'read'  : 'GET'
    };

    // custom getUrl function
    // handles url retrieval based on the object passed
    // on most occasions in the synnefo api this will call
    // the model/collection url method
    var getUrl = function(object, options) {
        if (!(object && object.url)) return null;
        return _.isFunction(object.url) ? object.url(options) : object.url;
    };
    
    // Call history (set of api paths with the dates the path last called)
    var api_history = api.requests = api.requests || {};
    var addApiCallDate = function(url, d) {
        if (d === undefined) { d = Date() };
        var path = snf.util.parseUri(url).path;
        api_history[path] = d;
        return api_history[path]
    }
    
    var api_errors = api.errors = api.errors || [];
    var add_api_error = function(settings, data) {
        api_errors.push({url:settings.url, date:new Date, settings:settings, data:data})
    }

    var setChangesSince = function(url) {
        var path = snf.util.parseUri(url).path;
        var d = api_history[path];

        if (d) {
            url = url + "?changes-since=" + snf.util.ISODateString(d)
        }
        return url;
    }
    
    // custom sync method
    // appends global ajax handlers
    // handles changed-since url parameter based on api path
    api.sync = function(method, model, options) {

        var type = methodMap[method];
        
        if (model && (model.skipMethods || []).indexOf(method) >= 0) {
            throw "Model does not support " + method + " calls";
        }
        
        if (!options.url) {
            options.url = getUrl(model, options) || urlError();
            options.url = options.refresh ? options.url : setChangesSince(options.url, options);
            if (!options.refresh && options.cache === undefined) {
                options.cache = true;
            }
        }

        options.handles_error = options.handles_error || false;
        
        if (api.stop_calls) {
            return;
        }

        var success = options.success || function(){};
        var error = options.error || function(){};
        var complete = options.complete || function(){};
        var before_send = options.beforeSend || function(){};

        // custom json data.
        if (options.data && model && (method == 'create' || method == 'update')) {
            options.contentType = 'application/json';
            options.data = JSON.stringify(options.data);
        }
        
        var api_params = {};
        var api_options = _.extend(api_params, options, {
            success: api.handlerWrapper(api.successHandler, success, "success"),
            error: api.handlerWrapper(api.errorHandler, error, "error"),
            complete: api.handlerWrapper(api.completeHandler, complete, "complete"),
            beforeSend: api.handlerWrapper(api.beforeSendHandler, before_send, "beforeSend"),
            cache: options.cache || false,
            timeout: options.timeout || window.TIMEOUT || 5000
        });
        return bb.sync(method, model, api_options);
    }
    
    api.handlerWrapper = function(wrap, method, type) {
        var cb_type = type;
        return function() {
            
            if (type == "error") {
                add_api_error(this, arguments);
            }

            if (type == "error" && this.handles_error) { return method.apply(this, arguments)}

            var args = wrap.apply(this, arguments);
            args = _.toArray(args);
            var ajax_options = this;
            
            try {
                if (args[1] === "abort") {
                    api.trigger("abort");
                    return;
                }
            } catch(error) {
                console.error("error aborting", error);
            }

            // FIXME: is this good practice ??
            // fetch callbacks wont get called
            try {
                // identify xhr object
                var xhr = args[2];
                if (args.length == 2) {
                    xhr = args[0];
                }

                // do not call success for 304 responses
                if (args[1] === "notmodified" || xhr.status == 0 && $.browser.opera) {
                    if (args[2]) {
                        addApiCallDate(this.url, new Date(args[2].getResponseHeader('Date')));
                    }
                    return;
                }
                
            } catch (err) {
                console.error(err);
            }
            method.apply(this, args);
        }
    }

    api.successHandler = function(data, status, xhr) {
        //debug("ajax success", arguments)
        // on success, update the last date we called the api url
        addApiCallDate(this.url, new Date(xhr.getResponseHeader('Date')));
        return [data, status, xhr];
    }

    api.errorHandler = function(event, xhr, settings, error) {
        //debug("ajax error", arguments, this);
        arguments.ajax = this;

        // skip aborts
        if (xhr != "abort") {
            if (!settings.handles_error) api.trigger("error", arguments);
        }
        return arguments;
    }

    api.completeHandler = function(xhr, status) {
        //debug("ajax complete", arguments)
        return arguments;
    }

    api.beforeSendHandler = function(xhr, settings) {
        //debug("ajax beforeSend", arguments)
        // ajax settings
        var ajax_settings = this;
        return arguments;
    }


    api.call = function(url, method, data, complete, error, success) {
            var self = this;
            error = error || function(){};
            success = success || function(){};
            complete = complete || function(){};
            var params = {
                url: snf.config.api_url + "/" + url,
                data: data,
                success: success,
                complete: function() { api.trigger("call"); complete(this) },
                error: error
            }
            this.sync(method, this, params);
        },

    _.extend(api, bb.Events);

    
    api.updateHandler = function(options) {
        this.cb = options.callback;
        this.limit = options.limit;
        this.timeout = options.timeout;

        this.normal_timeout = options.timeout;
        this.fast_timeout = options.fast;

        this._called = 0;
        this.interval = undefined;
        this.call_on_start = options.call_on_start || true;
        
        // wrapper
        function _cb() {
            if (this.fast_timeout == this.timeout){
                this._called++;
            }

            if (this._called >= this.limit && this.fast_timeout == this.timeout) {
                this.timeout = this.normal_timeout;
                this.setInterval()
            }
            this.cb();
        };
        _cb = _.bind(_cb, this);

        this.faster = function() {
            this.timeout = this.fast_timeout;
            this._called = 0;
            this.setInterval();
        }

        this.setInterval = function() {
            this.trigger("clear");
            window.clearInterval(this.interval);
            if (this.call_on_start) {
                _cb();
            }
            this.interval = window.setInterval(_cb, this.timeout);
        }

        this.start = function () {
            this.setInterval();
        }

        this.stop = function() {
            this.trigger("clear");
            window.clearInterval(this.interval);
        }
    }
    
    api.stop_calls = false;

    // make it eventable
    _.extend(api.updateHandler.prototype, bb.Events);
    
})(this);
