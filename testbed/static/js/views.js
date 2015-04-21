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

  Views.ParsedLoading = Backbone.View.extend({
    initialize: function() {
      this.listenTo(Globals.payload, 'change:action', function() {
        if(Globals.payload.get('action') == 'parse') {
          this.$el.removeClass('hidden');
        } else {
          this.$el.addClass('hidden');
        }
      });
    },
  });

  Views.ParsedMain = Backbone.View.extend({
    initialize: function() {
      this.listenTo(Globals.payload, 'change:parse_error', function() {
        if(Globals.payload.get('parse_error')) {
          this.$el.addClass('hidden');
        } else {
          this.$el.removeClass('hidden');
        }
      });
    },
  });
  Views.ParsedError = Backbone.View.extend({
    initialize: function() {
      this.$pre = this.$('pre');
      this.listenTo(Globals.payload, 'change:parse_error', function() {
        if(Globals.payload.get('parse_error')) {
          this.$el.removeClass('hidden');
        } else {
          this.$el.addClass('hidden');
        }
        this.$pre.html(Globals.payload.get('parse_error'));
      });
    },
  });

  Views.Stringset = Backbone.View.extend({
    initialize: function() {
      this.listenTo(Globals.payload.stringset, 'add', this.render_new);
    },
    render_new: function(new_string) {
      var new_string_view = new Views.String({ model: new_string });
      new_string_view.render().$el.appendTo(this.$el);
    },
  });

  Views.String = Backbone.View.extend({
    template: _.template($('#string-template').html()),
    initialize: function() {
      this.listenTo(this.model, 'destroy remove', this.remove);
      this.listenTo(this.model, 'change', this.render);
    },
    render: function() {
      this.$el.html(this.template({ string: this.model.toJSON() }));
      this.$el.addClass('list-group-item');
      return this;
    },
  });

  Views.Template = Backbone.View.extend({
    initialize: function() {
      this.listenTo(Globals.payload, 'change:template', this.render);
    },
    render: function() {
      if(Globals.payload.get('template')) {
        this.$el.text(Globals.payload.get('template'));
        this.$el.removeClass('hidden');
      } else {
        this.$el.addClass('hidden');
      }
      return this;
    },
  });
});
