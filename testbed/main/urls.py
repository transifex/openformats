from django.urls import re_path
from django.views.decorators.csrf import csrf_exempt

from testbed.main.views import MainView, ApiView, SaveView


urlpatterns = [
    re_path(r'^$', MainView.as_view(), name="testbed_home"),
    re_path(r'^(?P<payload_hash>\w{32})$', MainView.as_view(),
            name="testbed_main"),
    re_path(r'^api/$', csrf_exempt(ApiView.as_view()), name="testbed_api"),
    re_path(r'^save/$', SaveView.as_view(), name="testbed_save"),
]
