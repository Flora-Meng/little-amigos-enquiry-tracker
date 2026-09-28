from django.urls import path

from . import views

urlpatterns = [
    path("menu/<uuid:token>/", views.customer_menu, name="customer_menu"),
    path("menu/<uuid:token>/thanks/", views.customer_menu_thanks, name="customer_menu_thanks"),
    path("", views.party_summary_list, name="party_summary_list"),
    path("new/", views.party_summary_create, name="party_summary_create"),
    path("<uuid:summary_id>/edit/", views.party_summary_edit, name="party_summary_edit"),
    path("<uuid:summary_id>/delete/", views.party_summary_delete, name="party_summary_delete"),
    path("<uuid:summary_id>/decoration/", views.party_summary_decoration, name="party_summary_decoration"),
    path("<uuid:summary_id>/pdf/", views.party_summary_pdf, name="party_summary_pdf"),
]
