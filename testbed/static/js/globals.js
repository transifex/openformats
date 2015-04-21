$(document).ready(function() {
  var Testbed = window.Testbed;
  var Globals = Testbed.namespace('globals');

  var UiState = Backbone.Model.extend({
    defaults: {
      source_panel: true, parsed_panel: false, compiled_panel: false,
    },
    count_panels: function() {
      return this.get('source_panel') + this.get('parsed_panel') +
          this.get('compiled_panel');
    },
    toggle_panel: function(what) {
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

  var String = Backbone.Model.extend({});
  var Stringset = Backbone.Collection.extend({
    model: String,
  });

  var Payload = Backbone.Model.extend({
    defaults: { action: null },
    initialize: function() {
      this.stringset = new Stringset();
    },
    set: function(data) {
      if('stringset' in data) {
        var stringset = data.stringset;
        delete data.stringset;
        this.stringset.set(stringset);
      }
      Backbone.Model.prototype.set.call(this, data);
    },
    send: function() {
      if(this.get('action') == 'parse') {
        Globals.ui_state.set({ parsed_panel: true });
      } else if(this.get('action') == 'compile') {
        Globals.ui_state.set({ compiled_panel: true });
      }
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
    toJSON: function() {
      var return_value = Backbone.Model.prototype.toJSON.call(this);
      return_value.stringset = this.stringset.toJSON();
      return return_value;
    },
  });

  Globals.ui_state = new UiState();
  Globals.payload = new Payload();
});
