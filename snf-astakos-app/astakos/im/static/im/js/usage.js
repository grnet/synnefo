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


DO_LOG = false;
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
  this.projects_url = this.settings.projects_url;
  this.container = $(this.settings.container);
  this.meta = this.settings.meta;
  this.groups = this.settings.groups;
  this.projects = {};
  this.el = {};
  this.updating_projects = false;
  this.usage_cls_map = this.settings.usage_cls_map || default_usage_cls_map;
  this.initialize();
}


_.extend(UsageView.prototype, {
  tpls: {
      'main': '<div class="stats clearfix"><ul></ul></div>',
      'quotas': "#quotaTpl",
      'projectQuota': "#projectQuotaTpl"
  },

  initialize: function() {
    LOG("Initializing UsageView", this.settings);
    this.updateProjects(this.meta.projects_details);
    this.initResources();

    // initial usage set ????
    this.quotas = {};
    if (this.settings.quotas && _.keys(this.settings.quotas).length > 0) {
      this.setQuotas(this.settings.quotas);
    }
    this.initLayout();
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
      'resources': this.resources_ordered,
    });
    ul.append(this.el.list).hide();
    _.each(this.resources_ordered, function(resource) {
      this.renderResourceProjects(this.container, resource);
    }, this);
    this.updateQuotas();
    ul.show();
  },
  
  renderResourceProjects: function(list, resource) {
    var resource_el = list.find("li[data-resource='"+resource.name+"']");
    var projects_el = resource_el.find(".projects");
    projects_el.empty();
    _.each(resource.projects_list, function(project) {
      _.extend(project, {report_desc: resource.report_desc});
      projects_el.append(this.render('projectQuota', project));
    }, this);
  },

  initResources: function() {
    var ordered = this.meta.resources_order;
    var resources = {};
    var resources_ordered = [];
    var projects = this.projects;

    _.each(this.meta.resources, function(group, index) {
      _.each(group[1], function(resource, rindex) {
        resource.resource_name = resource.name.split(".")[1];
        resources[resource.name] = resource;
      }, this);
    }, this);
      
    resources_ordered = _.filter(
      _.map(ordered, function(rk, index) { 
        rk.index = index;
        return resources[rk] 
      }), function(i) { return i });

    this.resources = resources;
    this.resources_ordered = resources_ordered;

    LOG("Resources initialized", this.resources_ordered, this.resources);
  },
    
  updateProject: function(uuid, details) {
    LOG("Update project", uuid, details);
    this.projects[uuid] = details;
  },

  addProject: function(uuid, details) {
    LOG("New project", uuid, details);
    this.projects[uuid] = details;
  },

  updateProjects: function(projects, uuids) {
    this.projects = {};
    _.each(projects, function(details) {
      if (this.projects[details.id]) {
        this.updateProject(details.id, details);
      } else {
        this.addProject(details.id, details);
      }
    }, this);
    LOG("Projects updated", this.projects);
  },

  updateLayout: function() {
    LOG("Updating layout", this.quotas);
    var self = this;
    _.each(this.quotas, function(value, key) {
      var usage = self.getUsage(key);
      if (!usage) { return }
      var el = self.$().find("li[data-resource='"+key+"']");
      self.updateResourceElement(el.find(".summary.resource-bar"), usage);
      _.each(self.resources[key].projects_list, function(project){
        var project_el = el.find(".project-" + project.id);
        if (project_el.length === 0) {
          self.renderResourceProjects(self.container, self.resources[key]);
        } else {
          self.updateResourceElement(project_el, project.usage);
        }
      });
      var project_ids = _.keys(self.project_quotas);
      _.each(el.find(".resource-bar.project"), function(el) {
        if (project_ids.indexOf($(el).data("project")) == -1) {
          self.renderResourceProjects(self.container, self.resources[key]);
        }
      })
    })
  },

  updateResourceElement: function(el, usage) {
    var bar_el = el.find(".bar span");
    var bar_value = el.find(".bar .value");

    el.find(".currValue").text(usage.curr);
    el.find(".maxValue").text(usage.max);
    bar_el.css({width:usage.perc+"%"});
    bar_value.text(usage.perc+"%");
    var left = usage.label_left == 'auto' ? 
               usage.label_left : usage.label_left + "%";
    bar_value.css({left:left});
    bar_value.css({color:usage.label_color});
    el.removeClass("green yellow red");
    el.addClass(usage.cls);
    if (el.hasClass("summary")) {
      el.parent().removeClass("green yellow red");
      el.parent().addClass(usage.cls);
    };
  },
    
  getUsage: function(resource_name, quotas) {
    var resource = quotas ? quotas[resource_name] : this.quotas[resource_name];
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
    if (label_left != 'auto') { label_left = label_left + "%" }
    percentage = humanize.numberFormat(percentage, 0);
    qdata = {'curr': value, 'max': limit, 'perc': percentage, 'cls': cls,
             'label_left': label_left, 'label_color': label_col}
    _.extend(qdata, resource);
    return qdata
  },
  
  setQuotas: function(data, update_projects) {
    LOG("Set quotas", data);
    this.last_quota_received = data;
    var project_uuids = _.keys(data);

    var self = this;
    var sums = {};
    _.each(data, function(quotas, project_uuid) {
      _.each(quotas, function(values, qname) {
        if (!sums[qname]) {
          sums[qname] = {};
        }
        var qitem = sums[qname];
        _.each(values, function(value, param) {
          var current = qitem[param];
          qitem[param] = current ? qitem[param] + value : value;
        }, this);
      });
    }, this);
    
    this.project_quotas = data;
    this.quotas = sums;
    _.each(this.quotas, function(v, k) {
      var r = self.resources[k];
      var usage = self.getUsage(k);
      if (!usage) { return }
      r.usage = usage;
      self.resources[k].usage = usage;
      if (!self.resources_ordered[r.index]) { return }
      self.resources_ordered[r.index].usage = usage;
    });
    
    var active_project_uuids = _.keys(this.project_quotas);
    var project_change = false;
    _.each(this.project_quotas, function(resources, uuid) {
      if (project_change) { return }
      _.each(resources, function(v, k){
        if (project_change) { return }

        if (!self.resources[k]) { return }
        if (!self.resources[k].projects) { 
          self.resources[k].projects = {};
          self.resources[k].projects_list = [];
        }

        var resource = self.resources[k];
        var project_usage = self.getUsage(k, resources);
        var resource_projects_list = self.resources[k].projects_list;

        if (!self.projects[uuid]) { 
          self.getProjects(function(data) {
            self.updateProjects(data);
            self.setQuotas(self.last_quota_received);
            self.updateLayout();
          });

          project_change = true;
          return;
        }
        if (!project_usage) { return; }
        
        if (!resource.projects[uuid]) {
          resource.projects[uuid] = _.clone(self.projects[uuid]);
          if (self.projects[uuid].base_project) {
            resource.projects[uuid].name = 'User quota'
          }
        }
        var resource_project = resource.projects[uuid];
        resource_project.usage = project_usage;

        if (resource_project.index === undefined) {
          resource_project.index = resource_projects_list.length;
          resource_projects_list.push(resource_project);
        } else {
          resource_projects_list[resource_project.index] = resource_project;
        }

        _.each(resource.projects, function(project, uuid) {
          if (active_project_uuids.indexOf(uuid) == -1) {
            var index = resource.projects[uuid].index;
            delete resource.projects[uuid];
            delete resource.projects_list[index];
          }
        });
      });
      
    });

  },

  _ajaxOptions: function(url) {
    var token = $.cookie(this.settings.cookie_name).split("|")[1];
    return {
      'url': url || this.url,
      'headers': {
        'X-Auth-Token': token
      },
    }
  },
  
  updateQuotas: function() {
    LOG("Updating quotas");
    var self = this;
    this.getQuotas(function(data){
      self.setQuotas(data, true);
      self.updateLayout();
    })
  },

  getProjects: function(callback) {
    var options = this._ajaxOptions(this.projects_url);
    options.success = callback;
    LOG("Calling projects API", options);
    $.ajax(options);
  },

  getQuotas: function(callback) {
    if (this.updating_projects) { return }
    var options = this._ajaxOptions();
    options.success = callback;
    LOG("Calling quotas API", options);
    $.ajax(options);
  }
  
});

window.UsageView = UsageView;
})();
