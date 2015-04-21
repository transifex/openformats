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
  new Views.SaveForm({ el: '#save-form' });

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
    if(event.target.type == 'input' || event.target.type == 'textarea' ||
       ('' + event.target.type).indexOf('select') != -1) { return; }
    var keys = {49: '1', 50: '2', 51: '3', 72: 'h', 83: 's', 80: 'p', 84: 't',
                67: 'c'};
    var key_code = event.which;
    var key = keys[event.which];
    if((key == '1' || key == '2' || key == '3')) {
      var panels = {1: 'source', 2: 'parsed', 3: 'compiled'};
      Globals.ui_state.toggle_panel(panels[key]);
    }
    if(key == 'h') {
      Globals.ui_state.set({ source_panel: true });
      $('select[name="handler"]').focus();
    }
    if(key == 's') {
      Globals.ui_state.set({ source_panel: true });
      $('textarea[name="source"]').focus(); 
      $('textarea[name="source"]').trigger('select'); 
    }
    if(key == 'p') {
      Globals.ui_state.set({ source_panel: true });
      $('#source-form').submit(); 
    }
    if(key == 't') {
      Globals.ui_state.set({ parsed_panel: true });
      $('#stringset a:first').click(); 
    }
    if(key == 'c') { $('#compile-button').click(); }
  });

  // Last bit of bootstraping
  $('select[name="handler"]').focus();
});
