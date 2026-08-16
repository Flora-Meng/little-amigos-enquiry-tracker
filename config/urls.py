"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from accounts.forms import EmailAuthenticationForm
from accounts.views import dashboard
from config.views import health_check
from enquiries.views import add_note, archive_enquiry, enquiry_detail, enquiry_list, extension_token_settings, new_store_enquiry, reschedule_follow_up, update_enquiry, zumo_duplicate_check, zumo_ignore, zumo_import, zumo_imports, zumo_review_again, zumo_review_status

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path('admin/', admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", dashboard, name="dashboard"),
    path("enquiries/new/", new_store_enquiry, name="new_store_enquiry"),
    path("enquiries/", enquiry_list, name="enquiry_list"),
    path("enquiries/<uuid:enquiry_id>/", enquiry_detail, name="enquiry_detail"),
    path("enquiries/<uuid:enquiry_id>/update/", update_enquiry, name="update_enquiry"),
    path("enquiries/<uuid:enquiry_id>/notes/", add_note, name="add_note"),
    path("enquiries/<uuid:enquiry_id>/archive/", archive_enquiry, name="archive_enquiry"),
    path("enquiries/<uuid:enquiry_id>/follow-up/", reschedule_follow_up, name="reschedule_follow_up"),
    path("zumo-imports/", zumo_imports, name="zumo_imports"),
    path("api/zumo/conversations/<str:conversation_id>/", zumo_review_status, name="zumo_review_status"),
    path("api/zumo/import/", zumo_import, name="zumo_import"),
    path("api/zumo/ignore/", zumo_ignore, name="zumo_ignore"),
    path("api/zumo/duplicates/", zumo_duplicate_check, name="zumo_duplicate_check"),
    path("api/zumo/conversations/<str:conversation_id>/review-again/", zumo_review_again, name="zumo_review_again"),
    path("zumo-imports/extension/", extension_token_settings, name="extension_token_settings"),
]
