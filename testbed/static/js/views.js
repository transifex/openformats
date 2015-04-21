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
    events: {
      'change select[name="handler"]': "validate_handler",
      'keydown select[name="handler"]': "blur_handler",
      'submit': "submit_source",
      'keydown textarea[name="source"]': "source_keypress",
    },
    initialize: function() {
      this.ui = { handler: this.$('select[name="handler"]'),
                  source: this.$('textarea[name="source"]') };
      this.listenTo(Globals.payload, 'change:handler change:source',
                    this.render);
    },
    blur_handler: function(event) {
      if(event.which == 17) { this.ui.handler.blur(); }
    },
    submit_source: function(event) {
      if(event) { event.preventDefault(); }
      var handler_valid = this.validate_handler();
      var source_valid = this.validate_source();
      if(handler_valid && source_valid) {
        Globals.payload.set({ handler: this.ui.handler.val(),
                              source: this.ui.source.val(),
                              action: 'parse' });
        Globals.payload.send();
      }
    },
    source_keypress: function(event) {
      if(event.which == 17) { this.ui.source.blur(); }
      if(event.metaKey && event.which == 13) { this.submit_source(); }
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
    render: function() {
      this.ui.handler.val(Globals.payload.get('handler'));
      this.ui.source.val(Globals.payload.get('source'));
      return this;
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
    tagName: 'a',
    events: {
      'click': "select_string",
      'keyup textarea': "capture_string",
      'blur textarea': "capture_string",
      'focus textarea': "select_all_string",
    },
    template: _.template($('#string-template').html()),
    initialize: function() {
      this.listenTo(this.model, 'destroy remove', this.remove);
      this.listenTo(this.model, 'change', this.render);
      this.listenTo(Globals.ui_state, 'change:selected_string',
                    this.switch_to_detailed);
    },
    render: function() {
      this.$el.html(this.template({ string: this.model.toJSON() }));
      this.$el.addClass('list-group-item');
      this.$el.attr('href', '#');
      this.ui = {simple: this.$('.js-simple'),
                 expanded: this.$('.js-expanded')};
      return this;
    },
    select_string: function(event) {
      event.preventDefault();
      Globals.ui_state.set({
        selected_string: this.model.get('template_replacement')
      });
      event.stopPropagation();
    },
    switch_to_detailed: function() {
      if(Globals.ui_state.get('selected_string') ==
         this.model.get('template_replacement'))
      {
        this.ui.simple.addClass('hidden');
        this.ui.expanded.removeClass('hidden');
        this.$('textarea:first').focus();
      } else {
        this.render();
      }
    },
    capture_string: function(event) {
      var $textarea = $(event.currentTarget);
      var rule = $textarea.data('rule');
      var value = $textarea.val();
      var strings = _.clone(this.model.get('strings'));
      strings[rule] = value;
      this.model.set({ strings: strings }, {silent: true});
    },
    select_all_string: function(event) {
      $(event.currentTarget).trigger('select');
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

  Views.CompileButton = Backbone.View.extend({
    events: { 'click': "submit_stringset" },
    submit_stringset: function(event) {
      event.preventDefault();
      Globals.payload.set({ action: 'compile' });
      Globals.payload.send();
    },
  });

  Views.CompiledLoading = Backbone.View.extend({
    initialize: function() {
      this.listenTo(Globals.payload, 'change:action', function() {
        if(Globals.payload.get('action') == 'compile') {
          this.$el.removeClass('hidden');
        } else {
          this.$el.addClass('hidden');
        }
      });
    },
  });

  Views.Compiled = Backbone.View.extend({
    initialize: function() {
      this.listenTo(Globals.payload, 'change:compiled', this.render);
    },
    render: function() {
      if(Globals.payload.get('compiled')) {
        this.$el.text(Globals.payload.get('compiled'));
        this.$el.removeClass('hidden');
      } else {
        this.$el.addClass('hidden');
      }
    },
  });

  Views.CompiledMain = Backbone.View.extend({
    initialize: function() {
      this.listenTo(Globals.payload, 'change:compile_error', function() {
        if(Globals.payload.get('compile_error')) {
          this.$el.addClass('hidden');
        } else {
          this.$el.removeClass('hidden');
        }
      });
    },
  });

  Views.CompiledError = Backbone.View.extend({
    initialize: function() {
      this.$pre = this.$('pre');
      this.listenTo(Globals.payload, 'change:compile_error', function() {
        if(Globals.payload.get('compile_error')) {
          this.$el.removeClass('hidden');
        } else {
          this.$el.addClass('hidden');
        }
        this.$pre.html(Globals.payload.get('compile_error'));
      });
    },
  });

  Views.SaveForm = Backbone.View.extend({
    events: { 'submit': "submit_payload" },
    initialize: function() {
      this.ui = { payload: this.$('input[name="payload"]'),
                  submit: this.$('button[type="submit"]') };
    },
    submit_payload: function() {
      this.ui.payload.val(JSON.stringify(Globals.payload.toJSON()));
      return true;
    },
  });
});
