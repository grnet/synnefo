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
    var units = ['bytes', 'Kb', 'Mb', 'Gb', 'Tb', 'Pb'];
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

function UsageClient(settings) {
  this.settings = settings;
  this.url = this.settings.url;
  this.container = $(this.settings.container);
}

UsageClient.prototype.load = function() {
  var self = this;
  $.ajax(this.url, {
    'success': function(data) {
      self.update(data);
    }
  })
}

function setText(el, valueFrom, valueTo, direction, modifier) {
  //valueTo = parseInt(valueTo);
  //text = valueFrom;

  //if (valueFrom >= valueTo) {
    //valueFrom = valueTo;
  //}
  
  var text = valueTo;
  if (modifier) {
    text = modifier(text);
  }
  el.html(text);

  //if (valueTo > valueFrom) {
    //window.setTimeout(function() {
      //setText(el, parseInt(valueFrom) + step, parseInt(valueTo));
    //}, 10)
  //}
}

UsageClient.prototype.updateEntry = function(key, data) {

  var entry = $('li[data-resourcekey=\''+key+'\']');
  var currentEl = entry.find("span.currValue");
  var maxEl = entry.find("span.maxValue");
  var ratioEl = entry.find("div.bar");
  var barEl = entry.find("div.bar span");
  var percentageEl = ratioEl.find("em");
  var units = entry.data("units");
  var infoEl = entry.find(".info");
  
  var current = data.currValue;
  var max = data.maxValue;
  
  modifier = function(v) { return v; }
  if (units == 'bytes') {
      modifier = humanize.filesize;
  }

  setText(maxEl, infoEl.data('maxvalue'), max, infoEl.data('maxvalue') > max, 
          modifier);
  setText(currentEl, infoEl.data('currvalue'), current, 
          infoEl.data('currvalue') > current, modifier);
  
  var percentage = humanize.numberFormat(data.ratio, 1);
  setText(percentageEl, percentageEl.data('value'), 
          percentage, percentageEl.data('value') > percentage, 
          function(v) { return v + '&#37; &nbsp;&nbsp;'});

  var width = data.ratio;
  if (width > 100) { width = 100; }
  if (width < 0) { width = 0; }

  width = humanize.numberFormat(width, 1);
  barEl.css({'width': width + '%'});

  if (percentage > 18) {
      percentageEl.addClass("hovered");
  } else {
      percentageEl.removeClass("hovered");
  }
  percentageEl.data('value', percentage);

  entry.removeClass("red green yellow");
  entry.addClass(data.load_class);

  entry.find(".info").data("currvalue", data.currValue);
  entry.find(".info").data("maxvalue", data.maxValue);
}

UsageClient.prototype.update = function(data) {
  var usage = {}, self = this;
  _.each(data, function(e) { usage[e.name] = e});

  _.each(usage, function(data, key) {
      self.updateEntry(key, data);
  });
}

window.UsageClient = UsageClient;
})();
