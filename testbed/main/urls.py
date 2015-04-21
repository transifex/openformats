from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from testbed.main.views import MainView, ApiView, SaveView


urlpatterns = patterns('',  # noqa
    url(r'^$', MainView.as_view(), name="testbed_home"),
    url(r'^(?P<payload_hash>\w{32})$', MainView.as_view(),
        name="testbed_main"),
    url(r'^api/$', csrf_exempt(ApiView.as_view()), name="testbed_api"),
    url(r'^save/$', SaveView.as_view(), name="testbed_save")
)
