from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("console/", admin.site.urls),
    path("", include("authlight.urls")),
]
