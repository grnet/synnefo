//this object holds the results
$profile = {};
old$ = jQuery;
$ = function () {
var args = Array.prototype.slice.apply(arguments);
if (args && args[0] && typeof args[0] === "string") {
    $profile[args[0]] = typeof $profile[args[0]] === "undefined" ? 1 : $profile[args[0]] += 1;
}
return old$.apply(this, arguments);
};
old$.extend(true, $, old$);
jQuery = $;

$$profile = function(limit) {
    var limit = limit || 10;
    results = _.select(_.map($profile, function(val,key){
        if (val > limit)
            return [key, val]

        return false;
    }), function(r){ return r })
    
    var sorted = _.sortBy(results, function(el) {
        return -el[1];
    })

    _.each(sorted, function(el) {
        console.log(el[0], el[1])
    })
}
