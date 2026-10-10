"""Корневые маршруты Django-проекта FAQ Service."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("homepage.urls")),
    path("faq/", include("faq_web.urls")),
]

handler404 = "homepage.views.page_not_found"
