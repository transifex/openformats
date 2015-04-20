from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from testbed.main.views import MainView, ApiView


urlpatterns = patterns('',  # noqa
    url(r'^$', MainView.as_view(), name="home"),
    url(r'^api/$', csrf_exempt(ApiView.as_view()), name="api"),
)
