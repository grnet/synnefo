;(function() {


var truncate = function(str, n){
  var p  = new RegExp("^.{0," + n + "}[\S]*", 'g');
  var re = str.match(p);
  var l  = re[0].length;
  var re = re[0].replace(/\s$/,'');
  if (l < str.length) return _.escape(re) + '&hellip;';
  return _.escape(str);
};

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
  33: 'orange',
  66: 'red'
}

function UsageView(settings) {
  this.settings = settings;
  this.url = this.settings.url;
  this.projects_url = this.settings.projects_url;
  this.container = $(this.settings.container);
  this.project_url_tpl = this.settings.project_url_tpl;
  
  this.filter_all_btn = $("h2 .filter-all");
  this.filter_base_btn = $("h2 .filter-base");
  this.filter_all_btn.click(_.bind(this.handle_filter_action, this, 'all'));
  this.filter_base_btn.click(_.bind(this.handle_filter_action, this, 'base'));

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
      'main': '<div class="stats filter-base clearfix"><ul></ul></div>',
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
    this.el.main.removeClass('filter-base');
  },
  
  $: function(selector) {
    return this.container;
  },
  
  handle_filter_action: function(filter) {
    if (filter == 'base') {
      this.el.main.addClass('filter-base');
      this.filter_all_btn.show();
      this.filter_base_btn.hide();
    } else {
      this.el.main.removeClass('filter-base');
      this.filter_all_btn.hide();
      this.filter_base_btn.show();
    }
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
    this.handle_filter_action('base');
    ul.show();
    
    // live is deprecated in latest jquery versions
    $(".bar").live("mouseenter", function() {
      var warn = $(this).find("i.warn");
      if (warn.hasClass("visible")) {
        $(this).find("i.warn-msg").addClass("hovered");
      }
    }).live("mouseleave", function() {
      $(this).find("i.warn-msg").removeClass("hovered");
    });
  },
  
  renderResourceProjects: function(list, resource) {
    var resource_el = list.find("li[data-resource='"+resource.name+"']");
    var projects_el = resource_el.find(".resource-projects");
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
    details.display_name = truncate(details.name, 25);
    details.details_url = this.project_url_tpl.replace("UUID", details.id);
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
      el.removeClass("green yellow red");
      el.addClass(usage.cls);
      _.each(self.resources[key].projects_list, function(project){
        var project_el = el.find(".project-" + project.id);
        if (project_el.length === 0) {
          self.renderResourceProjects(self.container, self.resources[key]);
        } else {
          self.updateResourceElement(project_el, project.usage, project);
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
    var bar_el = el.find(".bar span.member");
    var bar_value = el.find(".bar .value");
    var project_bar_el = el.find(".bar span.project");

    el.find(".currValue").text(usage.curr);
    el.find(".maxValue").text(usage.max);
    el.find(".leftValue").text(usage.left);
    bar_el.css({width:usage.ratio + "%"});
    project_bar_el.css({width: usage.user_project_ratio + "%"});

    bar_value.text(usage.ratio+"%");
    var left = usage.label_left;
    bar_value.css({left:left});
    bar_value.css({color:usage.label_color});
    el.removeClass("green yellow red");
    el.addClass(usage.cls);
    if (el.hasClass("summary")) {
      el.parent().removeClass("green yellow red");
      el.parent().addClass(usage.cls);
    };

    el.find("i.warn").removeClass("visible");
    el.find("i.warn-msg").text(usage.project_warn_msg);
    if (usage.project_warn) {
      el.find("i.warn").addClass("visible");
    } else {
      el.find("i.warn-msg").removeClass("hovered");
    }
  },
    
  getUsage: function(resource_name, quotas) {
    var resource = quotas ? quotas[resource_name] : this.quotas[resource_name];
    var resource_meta = this.resources[resource_name];
    if (!resource_meta) { return }
    var value, limit, ratio, cls, label_left, label_col, left,
        project_value, project_limit, project_ratio, project_cls, project_left,
        user_project_left;
    
    limit = resource.limit;
    value = resource.usage;
    left = limit - value;
    project_limit = resource.project_limit;
    project_value = resource.project_usage;
    project_left = project_limit - project_value;
    user_project_left = 0;
    user_project_ratio = 0;

    if (left > project_left) {
        user_project_left = left - project_left;
    }

    if (user_project_left < 0) { user_project_left = 0; }
    if (left < 0) { left = 0; }
    if (project_left < 0) { project_left = 0; }
    if (value < 0) { value = 0; }
    if (project_value < 0) { project_value = 0; }
    
    ratio = (value/limit) * 100;
    if (value == 0) { ratio = 0; }
    if (value >= limit) {
      ratio = 100;
    }
    
    if (left && limit && user_project_left) {
        user_project_ratio = (user_project_left / limit) * 100;
        if (user_project_ratio > ratio) {
            user_project_ratio = 100 - ratio;
        }
        user_project_ratio = parseInt(user_project_ratio);
        console.log("USER PROJECT RATIO", user_project_ratio);
    }

    project_ratio = (project_value/project_limit) * 100;
    if (project_value == 0) { project_ratio = 0 }
    if (project_value >= project_limit) {
      project_ratio = 100;
    }
  
    if (resource_meta.unit == 'bytes') {
      value = humanize.filesize(value);
      limit = humanize.filesize(limit);
      left = humanize.filesize(left);
      user_project_left = humanize.filesize(user_project_left);
      project_value = humanize.filesize(value);
      project_limit = humanize.filesize(limit);
      project_left = humanize.filesize(project_left);
    }

    cls = 'green';
    project_cls = 'green';
    _.each(this.usage_cls_map, function(ucls, u){
      if (ratio >= u) {
        cls = ucls;
      }
      if (project_ratio >= u) {
        project_cls = ucls;
      }
    });

    var span = (ratio + '').length >= 3 ? 15 : 12;
    label_left = ratio >= 30 ? ratio - span : ratio;
    label_col = label_left == ratio ? 'inherit' : '#fff';
    if (label_left != 'auto') { label_left = label_left + "%"; }

    ratio = humanize.numberFormat(ratio , 0);
    project_ratio = humanize.numberFormat(project_ratio , 0);
    
    var project_warn = user_project_ratio && ratio != 100 ? true : false;
    var project_warn_msg = "WARNING: " + project_left + " left in project.";

    qdata = {
      'curr': value, 
      'max': limit, 
      'left': left,
      'ratio': ratio, 
      'cls': cls,
      'label_left': label_left, 
      'label_color': label_col,
      'project_curr': project_value,
      'project_max': project_limit, 
      'project_ratio': project_ratio, 
      'project_cls': project_cls,
      'project_warn': project_warn,
      'project_warn_msg': project_warn_msg,
      'user_project_left': user_project_left,
      'user_project_ratio': user_project_ratio
    };
    _.extend(qdata, resource);
    return qdata;
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
        var resource_projects_list = resource.projects_list;
        var resource_projects = resource.projects;

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
          if (self.projects[uuid].system_project) {
            resource.projects[uuid].display_name = 'System project';
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
        
        resource.projects_list.sort(function(p1, p2) {
          if (p1.system_project && !p2.system_project) { return -1; }
          if (!p1.system_project && p2.system_project) { return 1;  }
          return -1;
        });
        
        // update indexes
        _.each(resource.projects_list, function(p, index) {
            if (!_.contains(active_project_uuids, p.id)) {
                p.not_a_member = true;
            } else {
                p.not_a_member = false;
            }
            p.index = index;
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
