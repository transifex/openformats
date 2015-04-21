$(document).ready(function() {
  var Testbed = window.Testbed;
  var Views = Testbed.namespace('views');

  new Views.PanelButtons({ el: '#panel-toggles' });
  $('.js-panel').each(function() {
    var panel = this;
    new Views.Panel({ el: panel });
  });
  new Views.SourceForm({ el: '#source-form' });
  new Views.ParsedLoading({ el: '#parsed-loading' });
  new Views.ParsedMain({ el: '#parsed-main' });
  new Views.ParsedError({ el: '#parsed-error' });
  new Views.Stringset({ el: '#stringset' });
  new Views.Template({ el: '#template' });
});
