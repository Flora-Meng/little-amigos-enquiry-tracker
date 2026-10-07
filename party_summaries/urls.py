from django.urls import path

from . import views

urlpatterns = [
    path("start/<uuid:token>/", views.customer_party_intake, name="customer_party_intake"),
    path("start/<uuid:token>/thanks/", views.customer_party_intake_thanks,
        name="customer_party_intake_thanks"),
    path("menu/<uuid:token>/", views.customer_menu, name="customer_menu"),
    path("menu/<uuid:token>/thanks/", views.customer_menu_thanks, name="customer_menu_thanks"),
    path("", views.party_summary_list, name="party_summary_list"),
    path("intake-links/", views.party_intake_links, name="party_intake_links"),
    path("new/", views.party_summary_create, name="party_summary_create"),
    path("weekly/<slug:location_code>/<slug:week_start>/pdf/", views.party_summary_weekly_pdf,
        name="party_summary_weekly_pdf"),
    path("<uuid:summary_id>/edit/", views.party_summary_edit, name="party_summary_edit"),
    path("<uuid:summary_id>/delete/", views.party_summary_delete, name="party_summary_delete"),
    path("<uuid:summary_id>/toggle-confirmed/", views.party_summary_toggle_confirmed,
        name="party_summary_toggle_confirmed"),
    path("<uuid:summary_id>/decoration/", views.party_summary_decoration, name="party_summary_decoration"),
    path("<uuid:summary_id>/confirmation-email/", views.party_summary_confirmation_email,
        name="party_summary_confirmation_email"),
    path("<uuid:summary_id>/pdf/", views.party_summary_pdf, name="party_summary_pdf"),
]
