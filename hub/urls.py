from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/", views.project_list, name="projects"),
    path("projects/<slug:slug>/", views.project_detail, name="project"),
    path("projects/<slug:slug>/download/", views.download_bundle, name="bundle"),
    path("code/<int:pk>/download/", views.download_code, name="download_code"),
    path("ai-lab/", views.ai_lab, name="ailab"),
    path("api/search/", views.api_search, name="api_search"),
    path("api/ai/chat/", views.api_chat, name="api_chat"),
    path("api/ai/recommend/", views.api_recommend, name="api_recommend"),
    path("api/ai/troubleshoot/", views.api_troubleshoot, name="api_troubleshoot"),
    path("api/ai/explain/<int:pk>/", views.api_explain, name="api_explain"),
]
