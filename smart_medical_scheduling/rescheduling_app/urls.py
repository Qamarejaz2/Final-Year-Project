from django.urls import path
from . import views
from django.conf import settings  # Import settings
from django.conf.urls.static import static 

app_name = 'rescheduling_app'


urlpatterns = [
    path("", views.SmartScheduling.as_view(), name="smart_rescheduling"),
    path("rescheduler/", views.Rescheduler.as_view(), name="rescheduler"),
    path("enhanced_rescheduler/", views.EnhancedRescheduler.as_view(), name="enhanced_rescheduler"),
    path("user_response/", views.UserResponse.as_view(), name="user_response"),
    path("get_slots_duration/", views.SlotsDuration.as_view(), name="get_slots_duration"),
    path("appointment_chatbot/", views.ProviderSlots.as_view(), name="appointment_chatbot"),
]