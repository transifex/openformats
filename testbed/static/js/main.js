$(document).ready(function() {
  var Testbed = window.Testbed;
  var Views = Testbed.namespace('views');

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
});
