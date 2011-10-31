;(function(root){
    
    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var sync = snf.sync = snf.sync || {};
    var api = snf.api = snf.api || {};
    var storage = snf.storage = snf.storage || {};

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
    var addApiCallDate = function(url, d, method) {
        if (d === undefined) { d = Date() };
        var path = snf.util.parseUri(url).path;
        var key = path + "_" + method;

        // TODO: check if d is very old date
        api_history[key] = d;
        return api_history[path]
    }

    var clearApiCallDate = function(url, method) {
        var path = snf.util.parseUri(url).path;
        var key = path + "_" + method;
        api_history[key] = false;
        return api_history[path]
    }

    var api_errors = api.errors = api.errors || [];
    var add_api_error = function(settings, data) {
        api_errors.push({url:settings.url, date:new Date, settings:settings, data:data})
    }

    var setChangesSince = function(url, method) {
        var path = snf.util.parseUri(url).path;
        var d = api_history[path + "_" + method];
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
            var urlobject = model;

            // fallback to collection url for item creation
            if (method == "create" && model.isNew && model.isNew()) {
                urlobject = model.collection;
            }

            options.url = getUrl(model, options) || urlError();
            if (model && model.supportIncUpdates) {
                options.url = options.refresh ? options.url : setChangesSince(options.url, type);
            }
            if (!options.refresh && options.cache === undefined) {
                options.cache = true;
            }
        }

        // default error options
        options.critical = options.critical === undefined ? true : options.critical;
        options.display = options.display === undefined ? true : options.display;

        if (api.stop_calls && !options.no_skip) {
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
            timeout: options.timeout || snf.config.ajax_timeout || window.TIMEOUT || 5000
        });
        return bb.sync(method, model, api_options);
    }
    
    api.timeouts_occured = 0;

    api.handlerWrapper = function(wrap, method, type) {
        
        var cb_type = type;

        return function() {
            
            var xhr = undefined;
            var handler_type = type;
            var args = arguments;
            var ajax_options = this;

            // save the request date to use it as a changes-since value
            // for opera because we are not able to determine
            // response date header for 304 requests
            if (handler_type == "beforeSend" && $.browser.opera) {
                this.date_send = new Date;
            }

            // error with status code 0 in opera
            // act as 304 response
            if (handler_type == "error" && $.browser.opera) {
                if (arguments[0].status === 0 && arguments[1] === "error") {
                    arguments[0].status = 304;
                    arguments[1] = "notmodified";
                    response_type = "success";
                    xhr = arguments[0];
                }
            }
            
            // add error in api errors registry
            // api errors registry will be sent
            // if user reports an error using feedback form
            if (handler_type == "error") {
                // skip logging requested ?
                // if not log this error
                if (this.log_error !== false) {
                    add_api_error(this, arguments);
                }
            }
            
            // identify response status
            var status = 304;
            if (arguments[0]) {
                status = arguments[0].status;
            }
            
            // identify aborted request
            try {
                if (args[1] === "abort") {
                    api.trigger("abort");
                    return;
                }
            } catch(error) {
                console.error("error aborting", error);
            }
            
            // try to set the last request date
            // only for notmodified or succeed responses
            try {
                // identify xhr object
                xhr = xhr || args[2];
                
                // not modified response
                if (args[1] === "notmodified") {
                    if (xhr) {
                        // use date_send if exists (opera browser)
                        var d = this.date_send || xhr.getResponseHeader('Date');
                        if (d) { addApiCallDate(this.url, new Date(d), ajax_options.type); };
                    }
                    return;
                }
                
                // success response
                if (args[1] == "success" && handler_type == "success") {
                    try {
                        // use date_send if exists (opera browser)
                        var d = this.date_send || args[2].getResponseHeader('Date');
                        if (d) { addApiCallDate(this.url, new Date(d), ajax_options.type); };
                    } catch (err) {
                        console.error(err)
                    }
                }
            } catch (err) {
                console.error(err);
            }
            
            // dont call error callback for non modified responses
            if (arguments[1] === "notmodified") {
                return;
            }
            
            // prepare arguments for error callbacks
            var cb_args = _.toArray(arguments);
            if (handler_type === "error") {
                cb_args.push(_.clone(this));
            }
            
            // determine if we need to call our callback wrapper
            var call_api_handler = true;
            
            // request handles errors by itself, s
            if (handler_type == "error" && this.skip_api_error) {
                call_api_handler = false
            }

            // aborted request, don't call error handler
            if (handler_type === "error" && args[1] === "abort") {
                call_api_handler = false;
            }
            
            // reset api call date, next call will be sent without changes-since
            // parameter set
            if (handler_type === "error") {
                if (args[1] === "error") {
                    clearApiCallDate(this.url, this.type);
                }
            }
            
            // call api call back and retrieve params to
            // be passed to the callback method set for
            // this type of response
            if (call_api_handler) {
                cb_args = wrap.apply(this, cb_args);
            }
            
            // call requested callback
            method.apply(this, _.toArray(cb_args));
        }
    }

    api.successHandler = function(data, status, xhr) {
        //debug("ajax success", arguments)
        // on success, update the last date we called the api url
        return [data, status, xhr];
    }

    api.errorHandler = function(event, xhr, settings, error) {
        
        // dont trigger api error untill timeouts occured
        // exceed the skips_timeouts limit
        //
        // check only requests with skips_timeouts option set
        if (xhr === "timeout" && _.last(arguments).skips_timeouts) {
            var skip_timeouts = snf.config.skip_timeouts || 1;
            if (snf.api.timeouts_occured < skip_timeouts) {
                snf.api.timeouts_occured++;
                return;
            } else {
                // reset and continue to error trigger
                snf.api.timeouts_occured = 0;
            }
        }

        // if error occured and changes-since is set for the request
        // skip triggering the error and try again without the changes-since
        // parameter set
        var url = snf.util.parseUri(this.url);
        if (url.query.indexOf("changes-since") > -1) {
            clearApiCallDate(this.url, this.type);
            return _.toArray(arguments);
        }
    
        // skip aborts, notmodified (opera)
        if (xhr === "error" || xhr === "timeout") {
            var args = _.toArray(arguments);
            api.trigger("error", args);
        }

        return _.toArray(arguments);
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

    // api call helper
    api.call = function(url, method, data, complete, error, success, options) {
            var self = this;
            error = error || function(){};
            success = success || function(){};
            complete = complete || function(){};
            var extra = data ? data._options || {} : {};

            // really ugly way to pass sync request options.
            // it works though....
            if (data && data._options) { delete data['_options'] };
            
            // prepare the params
            var params = {
                url: snf.config.api_url + "/" + url,
                data: data,
                success: success,
                complete: function() { api.trigger("call"); complete(this) },
                error: error
            }

            params = _.extend(params, extra, options);
            this.sync(method, this, params);
        },

    _.extend(api, bb.Events);
    
    // helper for callbacks that need to get called
    // in fixed intervals
    api.updateHandler = function(options) {
        this.cb = options.callback;
        this.limit = options.limit;
        this.timeout = options.timeout;

        this.normal_timeout = options.timeout;
        this.fast_timeout = options.fast;

        this._called = 0;
        this.interval = undefined;
        this.call_on_start = options.call_on_start || true;

        this.running = false;
        this.last_call = false;
        
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
            this.last_call = new Date;
        };

        _cb = _.bind(_cb, this);

        this.faster = function(do_call) {
            this.timeout = this.fast_timeout;
            this._called = 0;
            this.setInterval(do_call);
        }

        this.setInterval = function(do_call) {
            this.trigger("clear");
            window.clearInterval(this.interval);
            
            this.interval = window.setInterval(_cb, this.timeout);
            this.running = true;
            
            var call = do_call || this.call_on_start;
            
            if (this.last_call) {
                var next_call = (this.timeout - ((new Date) - this.last_call));
                if (next_call < this.timeout/2) {
                    call = true;
                } else {
                    call = false;
                }
            }

            if (call) {
                _cb();
            }
            return this;
        }

        this.start = function (call_on_start) {
            if (this.running) { this.stop() };
            this.call_on_start = call_on_start == undefined ? this.call_on_start : call_on_start;
            this.setInterval();
            return this;
        }

        this.stop = function() {
            this.trigger("clear");
            window.clearInterval(this.interval);
            this.running = false;
            return this;
        }
    }
    
    // api error state
    api.stop_calls = false;
    api.STATES = { NORMAL:1, WARN:0, ERROR:-1 };
    api.error_state = api.STATES.NORMAL;

    // on api error update the api error_state
    api.bind("error", function() {
        if (snf.api.error_state == snf.api.STATES.ERROR) { return };

        var args = _.toArray(_.toArray(arguments)[0]);
        var params = _.last(args);
        
        if (params.critical) {
            snf.api.error_state = api.STATES.ERROR;
            snf.api.stop_calls = true;
        } else {
            snf.api.error_state = api.STATES.ERROR;
        }
        snf.api.trigger("change:error_state", snf.api.error_state);
    });
    
    // reset api error state
    api.bind("reset", function() {
        snf.api.error_state = api.STATES.NORMAL;
        snf.api.stop_calls = false;
        snf.api.trigger("change:error_state", snf.api.error_state);
    })

    // make it eventable
    _.extend(api.updateHandler.prototype, bb.Events);
    
})(this);
