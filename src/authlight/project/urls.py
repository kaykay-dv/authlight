from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/console/")),
    path("console/", admin.site.urls),
    path("", include("authlight.urls")),
]
