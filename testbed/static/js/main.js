$(document).ready(function() {
  var Testbed = window.Testbed;
  var Views = Testbed.namespace('views');

  new Views.PanelButtons({ el: '#panel-toggles' });
  $('.js-panel').each(function() {
    var panel = this;
    new Views.Panel({ el: panel });
  });
  new Views.SourceForm({ el: '#source-form' });
});
