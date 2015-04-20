(function() {
  var Testbed = window.Testbed || (window.Testbed = {});
  Testbed.namespace = function(structure) {
    if(typeof(structure) == 'string') {
      return Testbed.namespace._return.apply(this, arguments);
    } else {
      Testbed.namespace._extend.apply(this, arguments);
    }
  };
  Testbed.namespace._extend = function(structure) {
    if(! structure) { structure = {}; }
    for(var key in structure) {
      if(! (key in this)) { this[key] = {}; }
      var value = structure[key];
      if(_.isString(value) || _.isArray(value) || _.isNumber(value) ||
         _.isBoolean(value) || _.isNull(value) || _.isUndefined(value) ||
         _.isFunction(value) || _.isDate(value) || _.isRegExp(value))
      {
        this[key] = value;
      } else {
        Testbed.namespace._extend.call(this[key], structure[key]);
      }
    }
  };

  Testbed.namespace._return = function(path) {
    var keys = path.split('.');
    var previous = this;
    for(var i = 0; i < keys.length; i++) {
      var key = keys[i];
      if(! (key in previous)) { previous[key] = {}; }
      previous = previous[key];
    }
    return previous;
  };
})();
