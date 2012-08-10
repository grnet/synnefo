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
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var views = snf.views = snf.views || {}
    var util = snf.util = snf.util || {}

    // shortcuts
    var bb = root.Backbone;
    
    // logging
    var logger = new snf.logging.logger("SNF-VIEWS");
    var debug = _.bind(logger.debug, logger);
    
    // Base view object
    views.View = bb.View.extend({
        // the main element of the view
        // view delegates show, visible, hide etc to this element
        view_id: false,

        el: '#app',
        data_from: false,
        selectors: {},
        
        initialize: function() {
            this.log = new snf.logging.logger("SNF-VIEWS:" + this.view_id);
        },
    
        // is the view visible ?
        visible: function(){
            return $(this.el).is(":visible");
        },
        
        // hide view
        hide: function(force) {
            if (!this.visible() && !force) { return this };
            return $(this.el).hide();
        },
        
        // show view
        show: function() {
            if (this.visible()) { return this };
            $(this.el).show();
            if (this.show_view) { this.show_view.apply(this, arguments)};
        },

        sel: function(id) {
            return this.$(this.selectors[id]);
        },

        // animations
        fadeIn: function(time, callback) {
            $(this.el).fadeIn(time, callback);
            return this.show();
        },

        fadeOut: function(time, callback) {
            $(this.el).fadeOut(time, callback);
            return this.hide();
        }
    });
    
    
    // overlays registry
    views._overlay_index = [];

    // overlay view helper
    views.Overlay = views.View.extend({
        view_id: 'overlay',
        tpl_selector: '#generic-overlay-tpl',
        css_class: 'overlay',
        oneInstance: true,
        fixed: false,

        initialize: function(options, selector) {
            this.defaults = {
                load: false,
                closeOnClick: false,
                closeOnEsc: false,
                mask: {
                    color: "#444",
                    loadSpeed: snf.config.overlay_speed || 0,
                    opacity: 0.7
                },
                speed: snf.config.overlay_speed || 200
            }
            
            this.tpl_selector = selector || this.tpl_selector;
            views.Overlay.__super__.initialize.apply(this);
            views._overlay_index.push(this);

            this.options = _.extend(this.defaults, options);
            this.options.clone = this.options.clone == undefined ? true : this.options.clone;
            this.options.fixed = this.fixed;

            this.options.onOpen = this.options.onOpen || function() {};
            this.options.onClose = this.options.onClose || function() {};
            this.options.beforeOpen = this.options.beforeOpen || function() {};
            this.options.beforeClose = this.options.beforeClose || function() {};
            this.el = this.create_element();
            this.el.hide();
        
            var ajax_params = _.clone(this.options);

            ajax_params.onBeforeLoad = _.bind(this._beforeOpen, this);
            ajax_params.onLoad = _.bind(this._onOpen, this);
            ajax_params.onBeforeClose = _.bind(this._beforeClose, this);
            ajax_params.onClose = _.bind(this._onClose, this);
            ajax_params.oneInstance = this.oneInstance;
            // create overlay
            // TODO: does this return overlay object ?? (to avoid the next code line)
            $(this.el).overlay(ajax_params);

            this.overlay = $(this.el).overlay();
            this.append_css = this.options ? this.options.css_class ? this.options.css_class : "" : "";

            this.is_visible = false;
            return this;
        },

        create_element: function() {
            var el = undefined;
            if (this.options.clone) {
                el = $(this.tpl_selector).clone();
            } else {
                el = $(this.tpl_selector);
            }
            
            // append content
            if (this.content_selector) {
                var content = $(this.content_selector).clone();
                content.addClass("content");
                
                if ($(el).find(".content").length) {
                    $(el).find(".content").replaceWith(content);
                }
                content.removeClass("hidden");
            }

            if (this.overlay_id) {
            }

            $(el).addClass("overlay");
            if (this.css_class) {
                $(el).addClass(this.css_class);
            }
            
            if (this.options.clone) {
                $("body").append(el);
            }

            return el;
        },

        set_title: function(title) {
            if (title || this.title) {
                $(this.el).find(".overlay-header .title").html(title || this.title)
            }
        },

        set_subtitle: function(subtitle) {
            if (subtitle || this.subtitle) {
                $(this.el).find(".overlay-header .subtitle").html(subtitle || this.subtitle)
            }
        },

        _beforeOpen: function() {
            this.is_visible = true;
            if (this.append_css) {
                $(this.el).addClass(this.append_css);
            }

            this.set_title();
            this.set_subtitle();
            
            this.beforeOpen.apply(this, arguments);
            this.options.beforeOpen.apply(this, arguments);
        },

        _onOpen: function() {
            // clear previously bound click events
            $(this.el).find(".closeme").unbind("click");

            if ($(this.el).find(".closeme").length) {
                $(this.el).find(".closeme").click(_.bind(function(){
                    this.hide();
                }, this))
            }
            this.onOpen.apply(this, arguments);
            this.options.onOpen.apply(this, arguments);
        },

        _beforeClose: function() {
            this.is_visible = false;
            this.beforeClose.apply(this, arguments);
            this.options.beforeClose.apply(this, arguments);
        },

        _onClose: function() {
            if (this.append_css) {
                $(this.el).removeClass(this.append_css);
            }
            this.onClose.apply(this, arguments);
            this.options.onClose.apply(this, arguments);
        },

        beforeOpen: function () {},
        onOpen: function () {},
        beforeClose: function () {},
        onClose: function () {},

        show: function() {
            // close opened overlays
            var hidden = false;
            _.each(views._overlay_index, function(ovr){
                if (ovr == this) { return };
                if (ovr.visible()) {
                    hidden = true;
                    ovr.hide();
                }
            })

            // do we need to wait for other overlays to close ???
            if (hidden) { delay = 300; } else { delay = 0; }

            this.is_visible = true;
            window.setTimeout(_.bind(function(){ this.overlay.load(); this.trigger('show') }, this), delay)
            return this;
        },

        hide: function() {
            if (!this.overlay.isOpened()) {
                // if its not opened events wont trigger
                this._onClose()
            } else {
                this.overlay.close();
            }
            return this;
        }
    });

    
    // overlay view helper
    views.VMOverlay = views.Overlay.extend({

        initialize: function() {
            views.VMOverlay.__super__.initialize.apply(this);
            this.vm = undefined;
            this.view_id_tpl = this.view_id;

            _.bindAll(this, "_handle_vm_change", "_handle_vm_remove");
        },

        set_vm: function(vm) {
            if (this.vm) { this.unbind_vm_handlers };
            this.vm = vm;
            this.view_id = this.view_id + "_" + vm.id;
            this.bind_vm_handlers();
        },

        bind_vm_handlers: function() {
            this.log.debug("binding handlers");
            this.vm.bind("change", this._handle_vm_change);
            storage.vms.bind("remove", this._handle_vm_remove);
        },
        
        unbind_vm_handlers: function() {
            this.log.debug("unbinding handlers", this.vm);
            if (!this.vm) { return };
            this.vm.unbind("change", this._handle_vm_change);
            storage.vms.unbind("remove", this._handle_vm_remove);
        },
        
        _update_vm_details: function() { 
            if (!this.vm) { console.error("invalid view state"); return }
            this.set_subtitle(this.vm.escape("name") + snf.ui.helpers.vm_icon_tag(this.vm, "small"));
            this.update_vm_details() 
        },

        update_vm_details: function() {},
        handle_vm_remove: function() {},
        handle_vm_change: function () {},
        
        _handle_vm_remove: function(vm, collection) {
            if (this.vm && vm.id == this.vm.id) {
                this.hide();
            }
            this.handle_vm_remove();
        },
        
        _handle_vm_change: function(vm) {
            this._update_vm_details();
            this.handle_vm_change(vm);
        },
        
        beforeClose: function() {
            this.unbind_vm_handlers();
            this.vm = undefined;
        },

        show: function(vm) {
            this.set_vm(vm);
            views.VMOverlay.__super__.show.apply(this, arguments);
            this._update_vm_details();
        }

    });

    snf.config.update_hidden_views = true;

})(this);
