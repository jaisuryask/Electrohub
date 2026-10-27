from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("hub.urls")),
]

handler400 = "hub.views.error_400"
handler403 = "hub.views.error_403"
handler404 = "hub.views.error_404"
handler500 = "hub.views.error_500"
