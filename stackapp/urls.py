from django.urls import path
from .views import StackAPIView, ListStackQuestions

urlpatterns = [
    path('', StackAPIView.as_view()),
    path('fetch', ListStackQuestions.as_view()),
]
