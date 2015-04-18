from django.conf.urls import patterns, url

from testbed.main.views import MainView


urlpatterns = patterns('',  # noqa
    url(r'^$', MainView.as_view(), name="home"),
)
