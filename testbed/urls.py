from django.urls import include, re_path

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    re_path(r"^", include("testbed.main.urls")),
    # Examples:
    # re_path(r'^testbed/', include('testbed.foo.urls')),
    # Uncomment the admin/doc line below to enable admin documentation:
    # re_path(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    # Uncomment the next line to enable the admin:
    # re_path(r'^admin/', include(admin.site.urls)),
]
