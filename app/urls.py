from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/video2text", views.api_video2text, name="video2text"),
    path("api/parse_douyin", views.api_parse_douyin, name="parse_douyin"),
    path("api/optimize_text", views.api_optimize_text, name="optimize_text"),
    path("api/summarize_text", views.api_summarize_text, name="summarize_text"),
]
