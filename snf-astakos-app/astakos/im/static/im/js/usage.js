;(function() {


// helper humanize methods
// https://github.com/taijinlee/humanize/blob/master/humanize.js 
humanize = {};
humanize.filesize = function(filesize, kilo, decimals, decPoint, thousandsSep) {
    kilo = (kilo === undefined) ? 1024 : kilo;
    decimals = isNaN(decimals) ? 2 : Math.abs(decimals);
    decPoint = (decPoint === undefined) ? '.' : decPoint;
    thousandsSep = (thousandsSep === undefined) ? ',' : thousandsSep;
    if (filesize <= 0) { return '0 bytes'; }

    var thresholds = [1];
    var units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    if (filesize < kilo) { return humanize.numberFormat(filesize, 0) + ' ' + units[0]; }

    for (var i = 1; i < units.length; i++) {
      thresholds[i] = thresholds[i-1] * kilo;
      if (filesize < thresholds[i]) {
        return humanize.numberFormat(filesize / thresholds[i-1], decimals, decPoint, thousandsSep) + ' ' + units[i-1];
      }
    }

    // use the last unit if we drop out to here
    return humanize.numberFormat(filesize / thresholds[units.length - 1], decimals, decPoint, thousandsSep) + ' ' + units[units.length - 1];
};
humanize.numberFormat = function(number, decimals, decPoint, thousandsSep) {
    decimals = isNaN(decimals) ? 2 : Math.abs(decimals);
    decPoint = (decPoint === undefined) ? '.' : decPoint;
    thousandsSep = (thousandsSep === undefined) ? ',' : thousandsSep;

    var sign = number < 0 ? '-' : '';
    number = Math.abs(+number || 0);

    var intPart = parseInt(number.toFixed(decimals), 10) + '';
    var j = intPart.length > 3 ? intPart.length % 3 : 0;

    return sign + (j ? intPart.substr(0, j) + thousandsSep : '') + intPart.substr(j).replace(/(\d{3})(?=\d)/g, '$1' + thousandsSep) + (decimals ? decPoint + Math.abs(number - intPart).toFixed(decimals).slice(2) : '');
  };


DO_LOG = false
LOG = DO_LOG ? _.bind(console.log, console) : function() {};
WARN = DO_LOG ? _.bind(console.warn, console) : function() {};

var default_usage_cls_map = {
  0: 'green',
  33: 'yellow',
  66: 'red'
}

function UsageView(settings) {
  this.settings = settings;
  this.url = this.settings.url;
  this.container = $(this.settings.container);
  this.meta = this.settings.meta;
  this.groups = this.settings.groups;
  this.el = {};
  this.usage_cls_map = this.settings.usage_cls_map || default_usage_cls_map;
  this.initialize();
}


_.extend(UsageView.prototype, {
  tpls: {
      'main': '<div class="stats clearfix"><ul></ul></div>',
      'quotas': "#quotaTpl"
  },

  initialize: function() {
    LOG("Initializing UsageView", this.settings);
    this.initResources();

    // initial usage set ????
    this.quotas = {};
    if (this.settings.quotas && _.keys(this.settings.quotas).length > 0) {
      this.setQuotas(this.settings.quotas);
    }
    this.initLayout();
    this.updateQuotas();
  },
  
  $: function(selector) {
    return this.container;
  },

  render: function(tpl, params) {
    LOG("Rendering", tpl, params);
    var tpl = this.tpls[tpl];
    if (/^[#\.]/.exec(tpl)) { 
      tpl = $(tpl).html();
    }
    var rendered = Mustache.render(tpl, params);
    return $(rendered);
  },

  initLayout: function() {
    LOG("Initializing layout");
    this.el.main = this.render('main');
    this.container.append(this.el.main);
    var ul = this.container.find("ul");
    this.el.list = this.render('quotas', {
      'resources': this.resources_ordered
    });
    ul.append(this.el.list);
  },
  
  initResources: function() {
    var ordered = this.meta.resources_order;
    var resources = {};
    var resources_ordered = [];

    _.each(this.meta.resources, function(group, index) {
      _.each(group[1], function(resource, rindex) {
        var resource_index = ordered.length;
        if (!_.contains(ordered, resource.name)) {
          ordered.push(resource.name);
        } else {
          resource_index = ordered.indexOf(resource.name);
        }
        resource.index = resource_index;
        resource.resource_name = resource.name.split(".")[1];
        resources[resource.name] = resource;
      })
    });
      
    resources_ordered = _.filter(_.map(ordered, 
                                       function(rk) { 
                                         return resources[rk] 
                                       }), 
                                 function(i) { return i});
    this.resources = resources;
    this.resources_ordered = resources_ordered;

    LOG("Resources initialized", this.resources_ordered, this.resources);
  },

  updateLayout: function() {
    LOG("Updating layout", this.quotas);
    var self = this;
    _.each(this.quotas, function(value, key) {
      var usage = self.getUsage(key);
      if (!usage) { return }
      var el = self.$().find("li[data-resource='"+key+"']");
      self.updateResourceElement(el, usage);
    })
  },

  updateResourceElement: function(el, usage) {
    el.find(".currValue").text(usage.curr);
    el.find(".maxValue").text(usage.max);
    el.find(".bar span").css({width:usage.perc+"%"});
    el.find(".bar .value").text(usage.perc+"%");
    var left = usage.label_left == 'auto' ? 
               usage.label_left : usage.label_left + "%";
    el.find(".bar .value").css({left:left});
    el.find(".bar .value").css({color:usage.label_color});
    el.removeClass("green yellow red");
    el.addClass(usage.cls);
  },
    
  getUsage: function(resource_name) {
    var resource = this.quotas[resource_name];
    var resource_meta = this.resources[resource_name];
    if (!resource_meta) { return }
    var value, limit, percentage; 
    
    limit = resource.limit;
    value = resource.usage;
    if (value < 0 ) { value = 0 }
  
    percentage = (value/limit) * 100;
    if (value == 0) { percentage = 0 }
    if (value > limit) {
      percentage = 100;
    }
  
    if (resource_meta.unit == 'bytes') {
      value = humanize.filesize(value);
      limit = humanize.filesize(limit);
    }

    var cls = 'green';
    _.each(this.usage_cls_map, function(ucls, u){
      if (percentage >= u) {
        cls = ucls
      }
    })
  
    var label_left = percentage >= 30 ? percentage - 17 : 'auto'; 
    var label_col = label_left == 'auto' ? 'inherit' : '#fff';
    percentage = humanize.numberFormat(percentage, 0);
    qdata = {'curr': value, 'max': limit, 'perc': percentage, 'cls': cls,
             'label_left': label_left, 'label_color': label_col}
    _.extend(qdata, resource);
    return qdata
  },

  setQuotas: function(data) {
    LOG("Set quotas", data);
    var self = this;
    this.quotas = data;
    _.each(this.quotas, function(v, k) {
      var r = self.resources[k];
      var usage = self.getUsage(k);
      if (!usage) { return }
      r.usage = usage;
      self.resources[k].usage = usage;
      if (!self.resources_ordered[r.index]) { return }
      self.resources_ordered[r.index].usage = usage;
    });
  },

  _ajaxOptions: function() {
    var token = $.cookie(this.settings.cookie_name).split("|")[1];
    return {
      'url': this.url,
      'headers': {
        'X-Auth-Token': token
      },
    }
  },
  
  updateQuotas: function() {
    LOG("Updating quotas");
    var self = this;
    this.getQuotas(function(data){
      self.setQuotas(data.system);
      self.updateLayout();
    })
  },

  getQuotas: function(callback) {
    var options = this._ajaxOptions();
    options.success = callback;
    LOG("Calling quotas API", options);
    $.ajax(options);
  }
  
});

window.UsageView = UsageView;
})();
