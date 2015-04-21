$(function() {
  var Testbed = window.Testbed;
  var Views = Testbed.namespace('views');
  var Globals = Testbed.namespace('globals');

  Views.PanelButtons = Backbone.View.extend({
    events: { 'click button': "select_panel" },
    initialize: function() {
      this.listenTo(
        Globals.ui_state,
        'change:source_panel change:parsed_panel change:compiled_panel',
        this.render
      );
      this.ui = { source: this.$('.js-source'),
                  parsed: this.$('.js-parsed'),
                  compiled: this.$('.js-compiled') };
    },
    select_panel: function(event) {
      event.preventDefault();
      var what = $(event.currentTarget).data('value');
      Globals.ui_state.toggle_panel(what);
    },
    render: function() {
      for(var what in this.ui) {
        var $button = this.ui[what];
        if(Globals.ui_state.get(what + '_panel')) {
          $button.addClass('btn-primary');
        } else {
          $button.removeClass('btn-primary');
        }
      }
      return this;
    },
  });

  Views.Panel = Backbone.View.extend({
    initialize: function() {
      this.what = this.$el.data('value');
      this.listenTo(
        Globals.ui_state,
        'change:source_panel change:parsed_panel change:compiled_panel',
        this.show_hide
      );
    },
    show_hide: function() {
      this.$el.removeClass('col-xs-4 col-xs-6 col-xs-12');
      var column_size = 12 / Globals.ui_state.count_panels();
      this.$el.addClass('col-xs-' + column_size);
      if(Globals.ui_state.get(this.what + '_panel')) {
        this.$el.removeClass('hidden');
      } else {
        this.$el.addClass('hidden');
      }
    },
  });

  Views.SourceForm = Backbone.View.extend({
    events: { 'change select[name="handler"]': "validate_handler",
              'submit': "submit_source" },
    initialize: function() {
      this.ui = { handler: this.$('select[name="handler"]'),
                  source: this.$('textarea[name="source"]') };
    },
    submit_source: function(event) {
      event.preventDefault();
      var handler_valid = this.validate_handler();
      var source_valid = this.validate_source();
      if(handler_valid && source_valid) {
        Globals.payload.set({ handler: this.ui.handler.val(),
                              source: this.ui.source.val(),
                              action: 'parse' });
        Globals.payload.send();
      }
    },
    _validate_input: function(what) {
      var value = this.ui[what].val();
      if(!value) {
        this.ui[what].parent().addClass('has-error');
      } else {
        this.ui[what].parent().removeClass('has-error');
      }
      return !! value;
    },
    validate_handler: function() {
      return this._validate_input('handler');
    },
    validate_source: function() {
      return this._validate_input('source');
    },
  });
});
