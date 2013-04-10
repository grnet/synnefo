// Copyright 2011 GRNET S.A. All rights reserved.
// 
// Redistribution and use in source and binary forms, with or
// without modification, are permitted provided that the following
// conditions are met:
// 
//   1. Redistributions of source code must retain the above
//      copyright notice, this list of conditions and the following
//      disclaimer.
// 
//   2. Redistributions in binary form must reproduce the above
//      copyright notice, this list of conditions and the following
//      disclaimer in the documentation and/or other materials
//      provided with the distribution.
// 
// THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
// OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
// PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
// CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
// USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
// AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
// LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
// ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.
// 
// The views and conclusions contained in the software and
// documentation are those of the authors and should not be
// interpreted as representing official policies, either expressed
// or implied, of GRNET S.A.
// 

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
        'read'  : 'GET',
        'head'  : 'HEAD'
    };

    // custom getUrl function
    // handles url retrieval based on the object passed
    // on most occasions in the synnefo api this will call
    // the model/collection url method
    var getUrl = function(object, options, method) {
        if (!(object && object.url)) return null;
        return _.isFunction(object.url) ? object.url(options, method) : object.url;
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
            // subtract threshold
            d = new Date(d - synnefo.config.changes_since_alignment);
            url = url + "?changes-since=" + snf.util.ISODateString(d);
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

            options.url = getUrl(urlobject, options, method) || urlError();
            if (urlobject && urlobject.supportIncUpdates) {
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
        options.data = _.isEmpty(options.data) ? undefined : options.data;
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

            if (handler_type == "beforeSend") {
                arguments[0].setRequestHeader('X-Auth-Token', 
                                              synnefo.user.get_token());
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

            if (["beforeSend", "complete"].indexOf(cb_type) == -1 && this.is_recurrent) {
                // trigger event to notify that a recurrent event
                // has returned status other than notmodified
                snf.api.trigger("change:recurrent");
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
        // dont trigger api error until timeouts occured
        // exceed the skips_timeouts limit
        //
        // check only requests with skips_timeouts option set
        
        if (xhr === "timeout" && _.last(arguments).skips_timeouts) {
            var skip_timeouts = snf.config.skip_timeouts || 1;
            if (snf.api.timeouts_occured < skip_timeouts) {
                snf.api.timeouts_occured++;
                return;
            } else {
                // reset trigger error
                snf.api.timeouts_occured = 0;
                var args = _.toArray(arguments);
                api.trigger("error", args);
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
                url: snf.config.api_urls[this.api_type] + "/" + url,
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
        this.handler_id = options.id;

        // the interval with which we start
        this.interval = this.normal_interval = options.interval || 4000;

        // fast interval
        // set when faster() gets called
        this.fast_interval = options.fast || 1000;
    
        // after how many calls to increase the interval
        this.interval_increase_count = options.increase_after_calls || 0;

        // increase the timer by this value after interval_increase_count calls
        this.interval_increase = options.increase || 500;
        
        // maximum interval limit
        this.maximum_interval = options.max || 60000;
        
        // make a call before interval starts
        this.call_on_start = options.initial_call === undefined ? true : options.initial_call;
            
        this.increase_enabled = this.interval_increase_count === 0;

        if (this.increase_enabled) {
            this.maximum_interval = this.interval;
            this.interval_increase_count = 1;
        }
        
        // inner params
        this._called = 0;
        this._first_call_date = undefined;
        this.window_interval = undefined;
        
        // state params
        this.running = false;
        this.last_call = false;
        
        // helper for api calls
        // TODO: move this out of here :/
        if (options.is_recurrent) {
            snf.api.bind("change:recurrent", _.bind(function() {
                if (this.running) {
                    this.faster(true);
                }
            }, this));
        }
        
        // callback wrapper
        this._cb = function() {
            if (!this.running) { this.stop() }
            if (this._called >= this.interval_increase_count) {
                this._called = 0;
                this.slower(false);
            }
            
            this.cb();
            this.last_call = new Date;
            this._called++;
        };

        // start from faster timeout and start increasing
        this.faster = function(do_call) {
            if (!this.running) { return }

            this.interval = this.fast_interval;
            this.setInterval(do_call);
        }

        // slow down
        this.slower = function(do_call) {
            if (this.interval == this.maximum_interval) {
                // no need to increase
                return;
            }
            
            this.interval = this.interval + this.interval_increase;
            // increase timeout
            if (this.interval > this.maximum_interval) {
                this.interval = this.maximum_interval;
            }
            
            this.setInterval(do_call);
        }
        
        // reset internal
        this.setInterval = function(do_call) {
            this.trigger("clear");
            
            // reset times called
            this._called = 0;
            
            window.clearInterval(this.window_interval);
            this.window_interval = window.setInterval(_.bind(this._cb, this), this.interval);

            this.running = true;
            
            // if no do_call set, fallback to object creation option
            // else force what was requested
            var call = do_call === undefined ? this.call_on_start : do_call;
            
            if (this.last_call && do_call !== false) {
                var next_call = (this.interval - ((new Date) - this.last_call));
                if (next_call < this.interval/2) {
                    call = true;
                } else {
                    call = false;
                }
            }
            
            if (call) {
                this._cb();
            }

            return this;
        }

        this.start = function (call_on_start) {
            if (this.running) { this.stop() };
            this.setInterval(call_on_start);
            return this;
        }

        this.stop = function() {
            this.trigger("clear");
            window.clearInterval(this.window_interval);
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
