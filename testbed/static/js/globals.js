$(document).ready(function() {
  var Testbed = window.Testbed;
  var Globals = Testbed.namespace('globals');

  var UiState = Backbone.Model.extend({
    defaults: {
      source_panel: true, parsed_panel: true, compiled_panel: false,
    },
    count_panels: function() {
      return this.get('source_panel') + this.get('parsed_panel') +
          this.get('compiled_panel');
    },
    toggle: function(what) {
      var selected = this.get(what + '_panel');
      var to_set;
      if(selected === false) {
        to_set = {};
        to_set[what + '_panel'] = true;
        this.set(to_set);
      } else {
        if(this.count_panels() > 1) {
          to_set = {};
          to_set[what + '_panel'] = false;
          this.set(to_set);
        }
      }
    },
  });

  var Payload = Backbone.Model.extend({
    send: function() {
      var _this = this;
      $.ajax({
        type: 'POST',
        url: '/api/',
        data: JSON.stringify(this.toJSON()),
        dataType: 'json',
        success: function(data) { _this.set(data); },
        error: function() {},
      });
    },
  });

  Globals.ui_state = new UiState();
  Globals.payload = new Payload();
});
