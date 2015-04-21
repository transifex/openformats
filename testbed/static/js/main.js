$(document).ready(function() {
  var Testbed = window.Testbed;
  var Views = Testbed.namespace('views');
  var Globals = Testbed.namespace('globals');

  // Header
  new Views.PanelButtons({ el: '#panel-toggles' });
  $('.js-panel').each(function() {
    var panel = this;
    new Views.Panel({ el: panel });
  });

  // Source
  new Views.SourceForm({ el: '#source-form' });

  // Parsed
  new Views.ParsedLoading({ el: '#parsed-loading' });
  new Views.ParsedMain({ el: '#parsed-main' });
  new Views.ParsedError({ el: '#parsed-error' });
  new Views.Stringset({ el: '#stringset' });
  new Views.Template({ el: '#template' });

  // Compiled
  new Views.CompileButton({ el: '#compile-button' });
  new Views.CompiledLoading({ el: '#compiled-loading' });
  new Views.Compiled({ el: '#compiled' });
  new Views.CompiledMain({ el: '#compiled-main' });
  new Views.CompiledError({ el: '#compiled-error' });

  // Global events
  $('body').on('click', function() {
    // Deselect all strings
    Globals.ui_state.set({ selected_string: null });
  });
  $('body').on('keyup', function(event) {
    var key_code = event.which;
    if(event.target.type == 'input' || event.target.type == 'textarea' ||
       key_code < 49 || key_code > 51) { return; }
    key_code -= 48;
    var panels = {1: 'source', 2: 'parsed', 3: 'compiled'};
    Globals.ui_state.toggle_panel(panels[key_code]);
  });

  // Last bit of bootstraping
  $('select[name="handler"]').focus();
});
