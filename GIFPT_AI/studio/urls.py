from django.urls import path
from .views import animate, task_status

urlpatterns = [
    path('animate', animate),
    path('tasks/<str:task_id>', task_status),
]
