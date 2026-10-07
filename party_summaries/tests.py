from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from accounts.models import Location

from .forms import TRIPLE_FRYER_CHOICES
from .models import PartyBillItem, PartyIntakeLink, PartyMenuItem, PartySummary
from .pdf import _numeric_quantity


def formset_data(prefix, rows):
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(rows)),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for index, row in enumerate(rows):
        for key, value in row.items():
            data[f"{prefix}-{index}-{key}"] = value
    return data


class PartySummaryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.flora = User.objects.get(email="flora@littleamigos.au")
        self.kiva = User.objects.get(email="southland@littleamigos.com")
        self.emma = User.objects.get(email="canberra@littleamigos.com")
        self.southland = Location.objects.get(code=Location.Code.SOUTHLAND)
        self.canberra = Location.objects.get(code=Location.Code.CANBERRA)
        self.base_data = {
            "location": str(self.southland.id),
            "party_date": "2026-09-05",
            "party_time": "5-8pm",
            "owner_name": "Rebecca Power",
            "owner_number": "0402 891 186",
            "food_ready": "5:30pm",
            "room_type": PartySummary.RoomType.DOUBLE,
            "kids_count": "12",
            "adults_count": "16",
            "deposit_method": "Card",
            "kids_name": "Ava",
            "gender": PartySummary.Gender.GIRL,
            "age": "5",
            "theme": "Rainbow",
            "balloon_color": "Pink and gold",
            "special_note": "Nut allergy",
            "deposit_amount": "500.00",
            "package_name": PartySummary.Package.DOUBLE_WEEKEND,
            "package_amount": "1299.00",
            "other_charges": "20.00",
        }

    def _post_data(self):
        data = dict(self.base_data)
        data.update(formset_data("adult", [
            {"quantity": "2 Jar", "item": "Drink"},
            {"quantity": "1 Jar", "item": "Water"},
        ]))
        data.update(formset_data("kids", [{"quantity": "12", "item": "Nuggets & Chips"}]))
        data.update(formset_data("extra", [{"quantity": "1", "item": "Fruit Platter", "amount": "75.50"}]))
        data.update(formset_data("bill", []))
        return data

    def _create_summary(self, location=None, user=None):
        return PartySummary.objects.create(
            location=location or self.southland, party_date=timezone.localdate() + timedelta(days=30), party_time="5-8pm",
            owner_name="Rebecca Power", owner_number="0402 891 186", room_type=PartySummary.RoomType.DOUBLE,
            kids_count=12, adults_count=16, package_name=PartySummary.Package.DOUBLE_WEEKEND,
            package_amount=Decimal("1299.00"), deposit_amount=Decimal("500.00"), created_by=user or self.flora,
        )

    def _customer_menu_data(self):
        return {
            "party_date": "2026-09-12",
            "party_time": "2:00pm-5:00pm",
            "owner_name": "Rebecca Power",
            "owner_number": "0402 891 186",
            "room_type": PartySummary.RoomType.DOUBLE,
            "kids_count": "12",
            "adults_count": "18",
            "dietary_requirements": "One child has a nut allergy",
            "food_ready_choice": "after_30",
            "kids_hot_0_selected": "on",
            "kids_hot_0_qty": "7",
            "kids_hot_3_selected": "on",
            "kids_hot_3_qty": "5",
            "kids_dessert_0_selected": "on",
            "kids_dessert_0_qty": "8",
            "kids_dessert_1_selected": "on",
            "kids_dessert_1_qty": "4",
            "adult_food_avoid": "No shellfish",
            "triple_fryer": "Mixed Fryer platter",
            "triple_pizza_0_qty": "1",
            "triple_pizza_1_qty": "1",
            "triple_pizza_2_qty": "1",
            "triple_pizza_3_qty": "1",
            "triple_salad": "Greek salad bowl",
            "triple_burger": "Mini burger platter 10pcs (Pork)",
            "triple_toast": "Smoked salmon toast 12pcs",
            "extra_12_selected": "on",
            "extra_12_qty": "2",
            "extra_34_selected": "on",
            "extra_34_qty": "3",
        }

    def _triple_customer_menu_data(self):
        data = self._customer_menu_data()
        data.update({
            "party_date": "2026-10-03",
            "party_time": "3:00pm-6:00pm",
            "owner_name": "Triple Customer",
            "owner_number": "0499 123 456",
            "room_type": PartySummary.RoomType.TRIPLE,
            "kids_count": "25",
            "adults_count": "30",
            "food_ready_choice": "earlier",
            "food_ready_time": "15:15",
            "kids_hot_0_qty": "15",
            "kids_hot_3_qty": "10",
            "kids_dessert_0_qty": "20",
            "kids_dessert_1_qty": "5",
            "triple_fryer": "Vege Fryer Platter",
            "triple_fryer_note": "No onion",
            "triple_fruit_note": "No kiwi",
            "triple_salad": "Greek salad bowl",
            "triple_salad_note": "Dressing on the side",
            "triple_burger": "Mini burger platter 10pcs (Pork)",
            "triple_burger_note": "No mustard",
            "triple_taco": "Taco platter 12pcs (Karaage chicken)",
            "triple_taco_note": "Mild sauce",
            "triple_pizza_0_qty": "2",
            "triple_pizza_1_qty": "1",
            "triple_pizza_2_qty": "1",
            "triple_pizza_3_qty": "0",
            "triple_pizza_note": "Cut into small slices",
            "triple_pasta": "Pesto pasta bowl without chicken",
            "triple_pasta_note": "No parmesan",
            "triple_toast": "Mushroom toast 12pcs (vegetarian)",
            "triple_toast_note": "",
            "triple_sushi": "Japanese sushi platter (assorted)",
            "triple_sushi_note": "No wasabi",
            "triple_drinks_note": "Mostly apple juice",
        })
        return data

    def test_login_is_required(self):
        response = self.client.get(reverse("party_summary_list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('party_summary_list')}")

    def test_admin_can_create_summary_with_all_menu_sections_and_calculated_balance(self):
        self.client.force_login(self.flora)
        response = self.client.post(reverse("party_summary_create"), self._post_data())
        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get(owner_name="Rebecca Power")
        self.assertEqual(summary.menu_items.filter(category="adult").count(), 2)
        self.assertEqual(summary.menu_items.filter(category="kids").count(), 1)
        self.assertEqual(summary.menu_items.filter(category="extra").count(), 1)
        self.assertEqual(summary.extra_food_total, Decimal("75.50"))
        self.assertEqual(summary.total_balance, Decimal("874.50"))

    def test_custom_bill_items_are_saved_and_included_in_balance(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        data.update(formset_data("bill", [
            {"name": "Extra entertainer", "amount": "120.00"},
            {"name": "Balloon upgrade", "amount": "35.50"},
        ]))
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get(owner_name="Rebecca Power")
        self.assertEqual(list(summary.bill_items.values_list("name", flat=True)), [
            "Extra entertainer", "Balloon upgrade",
        ])
        self.assertEqual(summary.custom_charges_total, Decimal("155.50"))
        self.assertEqual(summary.total_balance, Decimal("1030.00"))

    def test_negative_custom_bill_item_is_saved_as_discount(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        data.update(formset_data("bill", [
            {"name": "Invoice prepaid", "amount": "-598.00"},
        ]))

        response = self.client.post(reverse("party_summary_create"), data)

        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get(owner_name="Rebecca Power")
        discount = summary.bill_items.get()
        self.assertEqual(discount.amount, Decimal("-598.00"))
        self.assertEqual(summary.custom_charges_total, Decimal("-598.00"))
        self.assertEqual(summary.total_balance, Decimal("276.50"))

    def test_deleted_custom_bill_item_is_not_recreated_on_save(self):
        summary = self._create_summary()
        PartyBillItem.objects.create(summary=summary, name="Balloon upgrade", amount="35.50")
        self.client.force_login(self.flora)
        data = self._post_data()
        data.update(formset_data("bill", [
            {"name": "", "amount": "", "DELETE": "on"},
        ]))
        response = self.client.post(reverse("party_summary_edit", args=(summary.id,)), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        self.assertFalse(summary.bill_items.exists())

    def test_staff_summary_is_forced_to_their_location(self):
        self.client.force_login(self.kiva)
        data = self._post_data()
        data.pop("location")
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        self.assertEqual(PartySummary.objects.get().location, self.southland)

    def test_staff_only_sees_own_location_summaries(self):
        southland = self._create_summary()
        self._create_summary(location=self.canberra, user=self.emma).owner_name
        self.client.force_login(self.kiva)
        response = self.client.get(reverse("party_summary_list"))
        self.assertContains(response, southland.owner_name)
        self.assertEqual(len(response.context["summaries"]), 1)

    def test_search_matches_owner_phone_child_theme_and_location(self):
        summary = self._create_summary()
        summary.kids_name = "Ava"
        summary.theme = "Rainbow"
        summary.save()
        self.client.force_login(self.flora)
        for query in ("Rebecca", "891", "Ava", "Rainbow", "Southland"):
            with self.subTest(query=query):
                response = self.client.get(reverse("party_summary_list"), {"search": query})
                self.assertContains(response, "Rebecca Power")

    def test_party_summary_list_groups_by_week_then_southland_and_canberra(self):
        monday = timezone.localdate() + timedelta(days=(7 - timezone.localdate().weekday()))
        southland_first = self._create_summary()
        southland_first.party_date = monday + timedelta(days=1)
        southland_first.save(update_fields=("party_date",))
        southland_second = self._create_summary()
        southland_second.party_date = monday + timedelta(days=4)
        southland_second.save(update_fields=("party_date",))
        canberra = self._create_summary(location=self.canberra, user=self.emma)
        canberra.party_date = monday + timedelta(days=2)
        canberra.save(update_fields=("party_date",))
        self.client.force_login(self.flora)
        response = self.client.get(reverse("party_summary_list"))
        self.assertEqual(len(response.context["week_groups"]), 1)
        week = response.context["week_groups"][0]
        self.assertEqual(week["start"], monday)
        self.assertEqual([group["location"].code for group in week["locations"]], [
            Location.Code.SOUTHLAND, Location.Code.CANBERRA,
        ])
        self.assertEqual([len(group["summaries"]) for group in week["locations"]], [2, 1])

    def test_weekly_location_pdf_has_one_page_per_party_and_respects_access(self):
        monday = timezone.localdate() + timedelta(days=(7 - timezone.localdate().weekday()))
        for offset in (1, 5):
            summary = self._create_summary()
            summary.party_date = monday + timedelta(days=offset)
            summary.save(update_fields=("party_date",))
        self._create_summary(location=self.canberra, user=self.emma)
        url = reverse("party_summary_weekly_pdf", args=(Location.Code.SOUTHLAND, monday.isoformat()))
        self.client.force_login(self.flora)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        pdf = b"".join(response.streaming_content)
        self.assertEqual(len(PdfReader(BytesIO(pdf)).pages), 2)
        self.client.force_login(self.emma)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_confirmation_email_is_generated_from_current_summary(self):
        summary = self._create_summary()
        summary.kids_name = "Indiana"
        summary.age = "4"
        summary.theme = "Princess"
        summary.balloon_color = "Pink and gold"
        summary.food_ready = "1:30pm"
        summary.dietary_requirements = "No pineapple"
        summary.special_note = "Place the kids food in the middle of the table."
        summary.rsvp_information = "RSVP details must not appear in this email"
        summary.save()
        PartyMenuItem.objects.create(
            summary=summary, category=PartyMenuItem.Category.ADULT,
            quantity="2 pizzas (10-inch)", item="Pizza (Margherita)", notes="Cut into small slices",
        )
        PartyMenuItem.objects.create(
            summary=summary, category=PartyMenuItem.Category.KIDS,
            quantity="12", item="Nuggets & Chips",
        )
        PartyBillItem.objects.create(summary=summary, name="Balloon upgrade", amount="35.50")
        self.client.force_login(self.flora)

        response = self.client.get(reverse("party_summary_confirmation_email", args=(summary.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hi Rebecca Power,")
        self.assertContains(response, "Indiana")
        self.assertContains(response, "2 × Pizza (Margherita)")
        self.assertContains(response, "Cut into small slices")
        self.assertContains(response, "12 × Nuggets &amp; Chips")
        self.assertContains(response, "No pineapple")
        self.assertContains(response, "Balloon upgrade")
        self.assertContains(response, "Copy email")
        self.assertNotContains(response, "RSVP details must not appear in this email")

    def test_confirmation_email_respects_staff_location_access(self):
        canberra_summary = self._create_summary(location=self.canberra, user=self.emma)
        self.client.force_login(self.kiva)
        response = self.client.get(
            reverse("party_summary_confirmation_email", args=(canberra_summary.id,))
        )
        self.assertEqual(response.status_code, 404)

    def test_admin_can_create_private_customer_intake_link(self):
        self.client.force_login(self.flora)
        response = self.client.post(reverse("party_intake_links"), {
            "location": str(self.southland.id),
            "owner_name": "Beleni",
            "owner_number": "0430 990 265",
            "owner_email": "beleni@example.com",
        })
        self.assertRedirects(response, reverse("party_intake_links"))
        intake = PartyIntakeLink.objects.get()
        self.assertEqual(intake.location, self.southland)
        self.assertEqual(intake.owner_name, "Beleni")
        self.assertEqual(intake.created_by, self.flora)
        page = self.client.get(reverse("party_intake_links"))
        self.assertContains(page, reverse("customer_party_intake", args=(intake.token,)))
        self.assertContains(page, "Waiting for customer")

    def test_staff_intake_link_is_forced_to_their_location(self):
        self.client.force_login(self.kiva)
        response = self.client.post(reverse("party_intake_links"), {
            "owner_name": "Southland Customer",
            "owner_number": "0400 000 000",
            "owner_email": "customer@example.com",
        })
        self.assertRedirects(response, reverse("party_intake_links"))
        self.assertEqual(PartyIntakeLink.objects.get().location, self.southland)

    def test_customer_intake_creates_then_updates_one_party_summary(self):
        intake = PartyIntakeLink.objects.create(
            location=self.southland,
            owner_name="Beleni",
            owner_number="0430 990 265",
            owner_email="beleni@example.com",
            created_by=self.flora,
        )
        url = reverse("customer_party_intake", args=(intake.token,))
        first_response = self.client.post(url, {
            "party_date": "2026-11-07",
            "party_time": "1:00pm–3:00pm",
            "theme": "Princess",
            "kids_name": "Indiana",
            "age": "4",
            "rsvp_information": "RSVP to Beleni by 20 October",
        })
        self.assertRedirects(first_response, reverse("customer_party_intake_thanks", args=(intake.token,)))
        intake.refresh_from_db()
        summary = intake.summary
        self.assertIsNotNone(intake.submitted_at)
        self.assertEqual(summary.owner_name, "Beleni")
        self.assertEqual(summary.location, self.southland)
        self.assertEqual(summary.theme, "Princess")
        self.assertEqual(summary.kids_name, "Indiana")
        self.assertEqual(summary.rsvp_information, "RSVP to Beleni by 20 October")
        self.assertEqual(summary.package_name, PartySummary.Package.CUSTOM)

        second_response = self.client.post(url, {
            "party_date": "2026-11-08",
            "party_time": "2:00pm–4:00pm",
            "theme": "Frozen",
            "kids_name": "Indiana",
            "age": "5",
            "rsvp_information": "RSVP to Beleni by 21 October",
        })
        self.assertEqual(second_response.status_code, 302)
        intake.refresh_from_db()
        self.assertEqual(PartySummary.objects.count(), 1)
        self.assertEqual(intake.summary_id, summary.id)
        summary.refresh_from_db()
        self.assertEqual(summary.party_date.isoformat(), "2026-11-08")
        self.assertEqual(summary.theme, "Frozen")
        self.assertEqual(summary.age, "5")

    def test_customer_intake_post_does_not_lock_across_nullable_summary_join(self):
        intake = PartyIntakeLink.objects.create(
            location=self.canberra,
            owner_name="First submission",
            owner_number="",
            owner_email="first@example.com",
            created_by=self.flora,
        )
        url = reverse("customer_party_intake", args=(intake.token,))

        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(url, {
                "party_date": "2026-12-06",
                "party_time": "1:00pm–3:00pm",
                "theme": "Bluey",
                "kids_name": "Alex",
                "age": "5",
                "rsvp_information": "RSVP by 20 November",
            })

        intake_select = next(
            query["sql"] for query in queries.captured_queries
            if 'FROM "party_intake_links"' in query["sql"]
        )
        self.assertNotIn('JOIN "party_summaries"', intake_select)

        self.assertRedirects(
            response, reverse("customer_party_intake_thanks", args=(intake.token,)),
        )
        intake.refresh_from_db()
        self.assertIsNotNone(intake.summary_id)
        self.assertEqual(intake.summary.location, self.canberra)

    def test_staff_only_sees_intake_links_for_own_location(self):
        southland_link = PartyIntakeLink.objects.create(
            location=self.southland, owner_name="Southland Customer", created_by=self.flora,
        )
        PartyIntakeLink.objects.create(
            location=self.canberra, owner_name="Canberra Customer", created_by=self.flora,
        )
        self.client.force_login(self.kiva)
        response = self.client.get(reverse("party_intake_links"))
        self.assertContains(response, southland_link.owner_name)
        self.assertNotContains(response, "Canberra Customer")

    def test_visible_summary_can_be_updated_and_deleted(self):
        summary = self._create_summary()
        self.client.force_login(self.flora)
        data = self._post_data()
        data["owner_name"] = "Rebecca Updated"
        response = self.client.post(reverse("party_summary_edit", args=(summary.id,)), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        summary.refresh_from_db()
        self.assertEqual(summary.owner_name, "Rebecca Updated")
        response = self.client.post(reverse("party_summary_delete", args=(summary.id,)))
        self.assertRedirects(response, reverse("party_summary_list"))
        self.assertFalse(PartySummary.objects.filter(id=summary.id).exists())

    def test_staff_can_toggle_confirmation_and_list_replaces_delete_with_status(self):
        summary = self._create_summary()
        self.client.force_login(self.flora)
        list_response = self.client.get(reverse("party_summary_list"))
        self.assertNotContains(list_response, ">✓ Confirmed<", html=False)
        self.assertNotContains(list_response, ">Delete<", html=False)

        response = self.client.post(reverse("party_summary_toggle_confirmed", args=(summary.id,)))
        self.assertRedirects(response, reverse("party_summary_edit", args=(summary.id,)))
        summary.refresh_from_db()
        self.assertTrue(summary.confirmed)
        list_response = self.client.get(reverse("party_summary_list"))
        self.assertContains(list_response, "✓ Confirmed")

    def test_staff_cannot_open_other_location_summary(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        self.client.force_login(self.kiva)
        response = self.client.get(reverse("party_summary_edit", args=(summary.id,)))
        self.assertEqual(response.status_code, 404)

    def test_package_price_is_filled_when_zero_is_submitted(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        data["package_amount"] = "0"
        self.client.post(reverse("party_summary_create"), data)
        self.assertEqual(PartySummary.objects.get().package_amount, Decimal("1299.00"))

    def test_southland_package_choices_and_prices_are_location_specific(self):
        self.client.force_login(self.kiva)
        response = self.client.get(reverse("party_summary_create"))
        choices = dict(response.context["form"].fields["package_name"].choices)
        self.assertEqual(choices[PartySummary.Package.SINGLE_WEEKDAY], "Single Weekday $699")
        self.assertEqual(choices[PartySummary.Package.PRIVATE_WEEKEND], "Private Weekend $2,999")
        self.assertNotIn(PartySummary.Package.CLASSIC_WEEKDAY, choices)
        self.assertNotIn(PartySummary.Package.PRIVATE_WEEKDAY_2HOUR, choices)

    def test_canberra_package_choices_and_prices_are_location_specific(self):
        self.client.force_login(self.emma)
        response = self.client.get(reverse("party_summary_create"))
        choices = dict(response.context["form"].fields["package_name"].choices)
        self.assertEqual(choices[PartySummary.Package.CLASSIC_WEEKDAY], "Classic Weekday $599")
        self.assertEqual(choices[PartySummary.Package.DOUBLE_LITE_WEEKDAY], "Double Lite Weekday $1,099")
        self.assertEqual(choices[PartySummary.Package.DOUBLE_LITE_WEEKEND], "Double Lite Weekend $1,299")
        self.assertEqual(choices[PartySummary.Package.DOUBLE_WEEKDAY], "Double Weekday $1,280")
        self.assertEqual(choices[PartySummary.Package.DOUBLE_WEEKEND], "Double Weekend $1,580")
        self.assertEqual(choices[PartySummary.Package.PRIVATE_WEEKEND_3HOUR], "Private Weekend 3 hour $2,699")
        self.assertNotIn(PartySummary.Package.TRIPLE_WEEKDAY, choices)
        room_values = [value for value, _label in response.context["form"].fields["room_type"].choices]
        room_labels = dict(response.context["form"].fields["room_type"].choices)
        self.assertEqual(room_labels[PartySummary.RoomType.SINGLE], "Single room")
        self.assertEqual(room_labels[PartySummary.RoomType.SINGLE_VOUCHER], "Single (voucher)")
        self.assertEqual(room_values, [
            PartySummary.RoomType.SINGLE,
            PartySummary.RoomType.SINGLE_VOUCHER,
            PartySummary.RoomType.DOUBLE_LITE,
            PartySummary.RoomType.DOUBLE,
            PartySummary.RoomType.PRIVATE_2HOUR,
            PartySummary.RoomType.PRIVATE_3HOUR,
        ])

    def test_canberra_package_price_is_filled_from_canberra_catalog(self):
        self.client.force_login(self.emma)
        data = self._post_data()
        data.pop("location")
        data["package_name"] = PartySummary.Package.DOUBLE_LITE_WEEKDAY
        data["package_amount"] = "0"
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get()
        self.assertEqual(summary.location, self.canberra)
        self.assertEqual(summary.package_amount, Decimal("1099.00"))

    def test_canberra_double_room_uses_full_double_price(self):
        self.client.force_login(self.emma)
        data = self._post_data()
        data.pop("location")
        data["package_name"] = PartySummary.Package.DOUBLE_WEEKDAY
        data["package_amount"] = "0"
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        self.assertEqual(PartySummary.objects.get().package_amount, Decimal("1280.00"))

    def test_refillable_water_notes_are_cleared_but_soft_drink_notes_are_kept(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        data.update(formset_data("adult", [
            {"quantity": "8 jugs", "item": "Soft drinks / juice", "notes": "2 Coke, 2 Sprite"},
            {"quantity": "1 jug", "item": "Refillable water", "notes": "Should be removed"},
        ]))
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get()
        self.assertEqual(summary.menu_items.get(item="Soft drinks / juice").notes, "2 Coke, 2 Sprite")
        self.assertEqual(summary.menu_items.get(item="Refillable water").notes, "")

    def test_summary_can_be_created_before_guest_counts_and_billing_are_known(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        for name in ("kids_count", "adults_count", "deposit_amount", "package_name", "package_amount"):
            data[name] = ""
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get()
        self.assertEqual(summary.kids_count, 0)
        self.assertEqual(summary.package_name, PartySummary.Package.CUSTOM)
        self.assertEqual(summary.package_display_name, "Custom")
        self.assertEqual(summary.package_amount, Decimal("0.00"))

    def test_custom_package_name_is_saved_and_used_in_customer_documents(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        data.update({
            "package_name": PartySummary.Package.CUSTOM,
            "custom_package_name": "Mini Party",
            "package_amount": "650.00",
        })
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get()
        self.assertEqual(summary.package_display_name, "Mini Party")
        email_response = self.client.get(reverse("party_summary_confirmation_email", args=(summary.id,)))
        self.assertContains(email_response, "Mini Party")

    def test_non_custom_package_clears_old_custom_name(self):
        summary = self._create_summary()
        summary.custom_package_name = "Old custom name"
        summary.save(update_fields=("custom_package_name",))
        self.client.force_login(self.flora)
        data = self._post_data()
        response = self.client.post(reverse("party_summary_edit", args=(summary.id,)), data)
        self.assertRedirects(response, reverse("party_summary_list"))
        summary.refresh_from_db()
        self.assertEqual(summary.custom_package_name, "")

    def test_save_errors_are_shown_at_the_top_of_the_form(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        data["owner_name"] = ""
        response = self.client.post(reverse("party_summary_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Party summary was not saved")
        self.assertContains(response, "Owner name")

    def test_decoration_example_is_saved_and_only_visible_to_authorised_location(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        image = SimpleUploadedFile("rainbow.png", b"fake-png-content", content_type="image/png")
        response = self.client.post(reverse("party_summary_create"), {**data, "decoration_example_upload": image})
        self.assertRedirects(response, reverse("party_summary_list"))
        summary = PartySummary.objects.get()
        self.assertEqual(bytes(summary.decoration_example), b"fake-png-content")
        response = self.client.get(reverse("party_summary_decoration", args=(summary.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"fake-png-content")
        self.client.force_login(self.emma)
        response = self.client.get(reverse("party_summary_decoration", args=(summary.id,)))
        self.assertEqual(response.status_code, 404)

    def test_pdf_download_is_single_page_and_scoped_to_visible_summaries(self):
        summary = self._create_summary()
        for position in range(20):
            PartyMenuItem.objects.create(summary=summary, category=PartyMenuItem.Category.ADULT,
                quantity="1", item=f"Menu item {position}", position=position)
        self.client.force_login(self.flora)
        response = self.client.get(reverse("party_summary_pdf", args=(summary.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        pdf = b"".join(response.streaming_content)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"/Count 1", pdf)
        self.client.force_login(self.emma)
        self.assertEqual(self.client.get(reverse("party_summary_pdf", args=(summary.id,))).status_code, 404)

    def test_pdf_embeds_fonts_for_chinese_and_emoji(self):
        summary = self._create_summary()
        summary.owner_name = "小明 🎂"
        summary.dietary_requirements = "不要花生 🥜"
        summary.save(update_fields=("owner_name", "dietary_requirements"))
        self.client.force_login(self.flora)
        response = self.client.get(reverse("party_summary_pdf", args=(summary.id,)))
        pdf = b"".join(response.streaming_content)
        self.assertIn(b"NotoSansSC", pdf)
        self.assertIn(b"NotoEmoji", pdf)

    def test_pdf_adult_menu_quantities_only_show_the_number(self):
        self.assertEqual(_numeric_quantity("1 platter"), "1")
        self.assertEqual(_numeric_quantity("1 bowl"), "1")
        self.assertEqual(_numeric_quantity("4 pizzas"), "4")
        self.assertEqual(_numeric_quantity("6 jugs"), "6")

    def test_save_and_download_action_redirects_to_pdf(self):
        self.client.force_login(self.flora)
        data = self._post_data()
        data["action"] = "download"
        response = self.client.post(reverse("party_summary_create"), data)
        summary = PartySummary.objects.get()
        self.assertRedirects(response, reverse("party_summary_pdf", args=(summary.id,)), fetch_redirect_response=False)

    def test_customer_menu_link_is_public_and_shown_on_staff_form(self):
        summary = self._create_summary()
        summary.kids_name = "Ava"
        summary.age = "6"
        summary.save(update_fields=("kids_name", "age"))
        public_url = reverse("customer_menu", args=(summary.customer_menu_token,))
        response = self.client.get(public_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose food for your party")
        self.assertContains(response, "little-amigos-characters-stacked.png")
        self.assertContains(response, "Little Amigos characters")
        self.assertContains(response, "Rebecca Power")
        self.assertNotContains(response, "Birthday child")
        self.assertNotContains(response, "Turning age")
        self.assertContains(response, "Party date")
        self.assertContains(response, date_format(summary.party_date, "l, j F Y"))
        self.assertContains(response, "Party time")
        self.assertContains(response, "Adults food")
        self.assertNotContains(response, "Southland Triple adults' menu")
        self.assertContains(response, "Menu dietary legend")
        self.assertContains(response, "Kid spaghetti")
        self.assertNotContains(response, "Pesto Pello")
        self.assertNotContains(response, "<h3>Dessert</h3>", html=False)
        self.assertNotContains(response, 'name="kids_dessert_0_selected"', html=False)
        self.assertContains(response, 'aria-label="Popular"')
        self.assertContains(response, 'name="triple_fryer"', count=len(TRIPLE_FRYER_CHOICES))
        self.assertContains(response, "Pick one flavour")
        self.assertContains(response, "Taco platter 12pcs (Karaage chicken)")
        self.assertContains(response, "Pizza flavours")
        self.assertContains(response, "Sushi platter")
        self.assertContains(response, "Mini burger platter 10pcs (Pork)")
        self.assertContains(response, "Pesto pasta bowl without chicken")
        self.assertContains(response, "Japanese sushi platter (assorted)")
        self.assertContains(response, "Platters to share")
        self.assertContains(response, "Salad and pasta bowls")
        self.assertContains(response, "Fryer trays")
        room_values = [value for value, _label in response.context["form"].fields["room_type"].choices]
        self.assertEqual(room_values, [
            PartySummary.RoomType.SINGLE,
            PartySummary.RoomType.DOUBLE,
            PartySummary.RoomType.TRIPLE,
            PartySummary.RoomType.PRIVATE,
        ])
        self.assertIn(PartySummary.RoomType.TRIPLE, room_values)
        self.assertContains(response, "Essential (single room)")
        self.assertContains(response, "Signature (double room)")
        self.assertContains(response, "Ultimate (triple room)")
        self.assertContains(response, "Private (whole venue hire)")
        self.assertContains(response, "kids +")
        self.assertContains(response, "adults are included in this package")
        self.assertContains(response, "an extra charge will apply")

        self.client.force_login(self.flora)
        response = self.client.get(reverse("party_summary_edit", args=(summary.id,)))
        self.assertContains(response, public_url)
        self.assertContains(response, "Awaiting customer submission")

    def test_canberra_customer_link_offers_only_canberra_room_types(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        response = self.client.get(reverse("customer_menu", args=(summary.customer_menu_token,)))
        room_values = [value for value, _label in response.context["form"].fields["room_type"].choices]
        self.assertEqual(room_values, [
            PartySummary.RoomType.SINGLE,
            PartySummary.RoomType.SINGLE_VOUCHER,
            PartySummary.RoomType.DOUBLE_LITE,
            PartySummary.RoomType.DOUBLE,
            PartySummary.RoomType.PRIVATE_2HOUR,
            PartySummary.RoomType.PRIVATE_3HOUR,
        ])
        self.assertNotIn(PartySummary.RoomType.TRIPLE, room_values)
        room_labels = dict(response.context["form"].fields["room_type"].choices)
        self.assertEqual(room_labels[PartySummary.RoomType.SINGLE], "Single room")
        self.assertEqual(room_labels[PartySummary.RoomType.SINGLE_VOUCHER], "Single (voucher)")

    def test_canberra_customer_menu_uses_adult_food_voucher_catalog(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        summary.room_type = PartySummary.RoomType.SINGLE_VOUCHER
        summary.save(update_fields=("room_type",))
        response = self.client.get(reverse("customer_menu", args=(summary.customer_menu_token,)))
        self.assertContains(response, "Your package includes a")
        self.assertContains(response, "$100")
        self.assertContains(response, "food voucher")
        self.assertContains(response, "Adult food order total")
        self.assertContains(response, "Balance after voucher")
        self.assertContains(response, "Mixed fryer platter (assorted)")
        self.assertContains(response, "Dessert")
        self.assertContains(response, "Mini cupcakes")
        self.assertContains(response, "Yogurt berries smoothie")
        self.assertContains(response, 'name="kids_dessert_0_selected"', html=False)
        self.assertContains(response, 'name="voucher_menu_notes"', html=False)
        self.assertNotContains(response, 'name="triple_fryer"', html=False)

    def test_canberra_customer_food_balance_deducts_voucher(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        data = self._customer_menu_data()
        data["room_type"] = PartySummary.RoomType.SINGLE_VOUCHER
        data["voucher_menu_notes"] = "Please label the vegetarian platters."
        response = self.client.post(
            reverse("customer_menu", args=(summary.customer_menu_token,)),
            data,
        )
        self.assertRedirects(response, reverse("customer_menu_thanks", args=(summary.customer_menu_token,)))
        summary.refresh_from_db()
        self.assertTrue(summary.menu_items.filter(category="adult").exists())
        self.assertEqual(summary.menu_items.filter(category="extra").count(), 0)
        self.assertEqual(summary.extra_food_total, Decimal("0.00"))
        self.assertEqual(summary.food_ordered_total, Decimal("270.00"))
        self.assertEqual(summary.menu_items.get(item="Fruit Platter").amount, Decimal("78.00"))
        self.assertEqual(summary.food_voucher_amount, Decimal("100.00"))
        self.assertEqual(summary.extra_food_balance, Decimal("170.00"))
        self.assertEqual(summary.total_balance, Decimal("969.00"))
        self.assertEqual(summary.voucher_menu_notes, "Please label the vegetarian platters.")
        self.client.force_login(self.emma)
        staff_response = self.client.get(reverse("party_summary_edit", args=(summary.id,)))
        self.assertContains(staff_response, "Food ordered")
        self.assertContains(staff_response, "Price")
        self.assertContains(staff_response, 'name="adult-0-amount"', html=False)

    def test_voucher_food_uses_editable_unit_price_and_quantity(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        summary.room_type = PartySummary.RoomType.SINGLE_VOUCHER
        summary.save(update_fields=("room_type",))
        PartyMenuItem.objects.create(
            summary=summary,
            category=PartyMenuItem.Category.ADULT,
            quantity="2",
            item="Pizza (Pepperoni)",
            amount=Decimal("17.50"),
        )
        self.assertEqual(summary.food_ordered_total, Decimal("35.00"))

        self.client.force_login(self.emma)
        response = self.client.get(reverse("party_summary_edit", args=(summary.id,)))
        self.assertContains(response, 'value="17.50"', html=False)
        self.assertNotContains(response, "Other charges / adjustments")

    def test_staff_form_replaces_adult_food_to_avoid_with_voucher_notes(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        summary.room_type = PartySummary.RoomType.SINGLE_VOUCHER
        summary.save(update_fields=("room_type",))
        self.client.force_login(self.emma)
        response = self.client.get(reverse("party_summary_edit", args=(summary.id,)))
        self.assertNotContains(response, "Adult food to avoid")
        self.assertContains(response, "Food voucher menu notes")
        content = response.content.decode()
        self.assertEqual(content.count('name="dietary_requirements"'), 1)
        self.assertLess(content.index('name="dietary_requirements"'), content.index("Adult menu"))

    def test_canberra_voucher_amount_depends_on_room_type(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        expected = {
            PartySummary.RoomType.SINGLE: Decimal("0.00"),
            PartySummary.RoomType.SINGLE_VOUCHER: Decimal("100.00"),
            PartySummary.RoomType.DOUBLE_LITE: Decimal("180.00"),
            PartySummary.RoomType.DOUBLE: Decimal("0.00"),
            PartySummary.RoomType.PRIVATE_2HOUR: Decimal("400.00"),
            PartySummary.RoomType.PRIVATE_3HOUR: Decimal("400.00"),
        }
        for room_type, voucher in expected.items():
            summary.room_type = room_type
            self.assertEqual(summary.food_voucher_amount, voucher)

    def test_canberra_single_room_saves_three_included_adult_foods(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        data = self._customer_menu_data()
        data.update({
            "room_type": PartySummary.RoomType.SINGLE,
            "adult_fryer": "Mixed Fryer platter",
            "adult_starter": "Mini Burger sliders - 10pcs (Pork)",
        })
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertRedirects(response, reverse("customer_menu_thanks", args=(summary.customer_menu_token,)))
        summary.refresh_from_db()
        adult_items = summary.menu_items.filter(category=PartyMenuItem.Category.ADULT)
        self.assertEqual(summary.food_voucher_amount, Decimal("0.00"))
        self.assertTrue(adult_items.filter(item="Mixed Fryer platter").exists())
        self.assertTrue(adult_items.filter(item="Seasonal fruit platter").exists())
        self.assertTrue(adult_items.filter(item="Mini Burger sliders - 10pcs (Pork)").exists())
        self.assertEqual(adult_items.get(item="Soft drinks / juice").quantity, "1 jug")
        self.assertFalse(adult_items.filter(item__startswith="Pizza").exists())

    def test_canberra_double_room_saves_included_adult_menu_and_dessert(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        data = self._customer_menu_data()
        data.update({
            "room_type": PartySummary.RoomType.DOUBLE,
            "adult_fryer": "Mixed Fryer platter",
            "adult_starter": "Mini Burger sliders - 10pcs (Pork)",
            "adult_main": "__four_pizzas__",
            "adult_pasta": "Chicken Pesto Pasta Bowl",
            "triple_pizza_0_qty": "2",
            "triple_pizza_1_qty": "1",
            "triple_pizza_2_qty": "1",
            "triple_pizza_3_qty": "0",
            "triple_fruit_note": "No kiwi",
            "triple_pizza_note": "Cut into small slices",
            "triple_drinks_note": "Coke and juice",
        })
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertRedirects(response, reverse("customer_menu_thanks", args=(summary.customer_menu_token,)))
        summary.refresh_from_db()
        pizza_rows = summary.menu_items.filter(category="adult", item__startswith="Pizza")
        self.assertEqual(pizza_rows.count(), 3)
        self.assertEqual(sum(int(row.quantity) for row in pizza_rows), 4)
        self.assertEqual(pizza_rows.first().notes, "Cut into small slices")
        self.assertTrue(summary.menu_items.filter(category="adult", item="Seasonal fruit platter").exists())
        self.assertTrue(summary.menu_items.filter(category="kids", item="Mini cupcakes").exists())
        self.assertTrue(summary.menu_items.filter(category="kids", item="Yogurt berries smoothie").exists())
        self.assertEqual(summary.menu_items.filter(category="extra").count(), 2)
        self.assertEqual(summary.extra_food_total, Decimal("270.00"))

    def test_canberra_double_pizza_flavour_quantities_must_add_up_to_four(self):
        summary = self._create_summary(location=self.canberra, user=self.emma)
        data = self._customer_menu_data()
        data.update({
            "room_type": PartySummary.RoomType.DOUBLE,
            "adult_fryer": "Mixed Fryer platter",
            "adult_starter": "Mini Burger sliders - 10pcs (Pork)",
            "adult_main": "__four_pizzas__",
            "adult_pasta": "Chicken Pesto Pasta Bowl",
            "triple_pizza_0_qty": "1",
            "triple_pizza_1_qty": "1",
            "triple_pizza_2_qty": "1",
            "triple_pizza_3_qty": "0",
        })
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pizza flavour quantities must add up to 4")
        summary.refresh_from_db()
        self.assertIsNone(summary.customer_menu_submitted_at)

    def test_customer_menu_is_read_only_within_72_hours_of_party(self):
        summary = self._create_summary()
        summary.party_date = timezone.localdate() + timedelta(days=1)
        summary.save(update_fields=("party_date",))
        public_url = reverse("customer_menu", args=(summary.customer_menu_token,))

        response = self.client.get(public_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Online menu changes are now closed")
        self.assertContains(response, "contact your Party Manager")
        self.assertContains(response, "customer-menu-lockable\" disabled", html=False)
        self.assertNotContains(response, "Submit food selection")

        data = self._customer_menu_data()
        data["owner_name"] = "Should Not Save"
        response = self.client.post(public_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your changes were not submitted")
        summary.refresh_from_db()
        self.assertEqual(summary.owner_name, "Rebecca Power")
        self.assertIsNone(summary.customer_menu_submitted_at)
        self.assertFalse(summary.menu_items.exists())

    def test_customer_submission_updates_party_menu_and_balance(self):
        summary = self._create_summary()
        response = self.client.post(
            reverse("customer_menu", args=(summary.customer_menu_token,)),
            self._customer_menu_data(),
        )
        self.assertRedirects(response, reverse("customer_menu_thanks", args=(summary.customer_menu_token,)))
        summary.refresh_from_db()
        self.assertEqual(summary.party_date.isoformat(), "2026-09-12")
        self.assertEqual(summary.party_time, "2:00pm-5:00pm")
        self.assertEqual(summary.food_ready, "Ready 30 minutes after the party starts")
        self.assertEqual(summary.adults_count, 18)
        self.assertEqual(summary.dietary_requirements, "One child has a nut allergy")
        self.assertEqual(summary.adult_food_avoid, "No shellfish")
        self.assertIsNotNone(summary.customer_menu_submitted_at)
        self.assertEqual(summary.menu_items.filter(category="kids", item="Nuggets & Chips").get().quantity, "7")
        self.assertFalse(summary.menu_items.filter(category="kids", item="Mini cupcakes").exists())
        self.assertEqual(summary.menu_items.filter(category="kids", item__startswith="Pizza").count(), 0)
        self.assertEqual(summary.menu_items.filter(category="adult", item__startswith="Pizza").count(), 4)
        self.assertEqual(summary.menu_items.filter(category="extra").count(), 2)
        self.assertEqual(summary.extra_food_total, Decimal("270.00"))
        fruit = summary.menu_items.get(category="extra", item="Fruit Platter")
        self.assertEqual(fruit.quantity, "2")
        self.assertEqual(fruit.amount, Decimal("156.00"))

    def test_customer_submission_accepts_null_origin_from_embedded_browser(self):
        summary = self._create_summary()
        browser = Client(enforce_csrf_checks=True)
        response = browser.post(
            reverse("customer_menu", args=(summary.customer_menu_token,)),
            self._customer_menu_data(),
            HTTP_ORIGIN="null",
        )
        self.assertRedirects(
            response,
            reverse("customer_menu_thanks", args=(summary.customer_menu_token,)),
        )
        summary.refresh_from_db()
        self.assertIsNotNone(summary.customer_menu_submitted_at)

    def test_essential_package_saves_two_pizzas_and_one_drink(self):
        summary = self._create_summary()
        data = self._customer_menu_data()
        data.update({
            "room_type": PartySummary.RoomType.SINGLE,
            "triple_pizza_0_qty": "1",
            "triple_pizza_1_qty": "1",
            "triple_pizza_2_qty": "0",
            "triple_pizza_3_qty": "0",
        })
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertRedirects(response, reverse("customer_menu_thanks", args=(summary.customer_menu_token,)))
        summary.refresh_from_db()
        adult_items = summary.menu_items.filter(category="adult")
        self.assertEqual(sum(int(row.quantity) for row in adult_items.filter(item__startswith="Pizza")), 2)
        self.assertEqual(adult_items.get(item="Soft drinks / juice").quantity, "1 jug")
        self.assertFalse(adult_items.filter(item__icontains="salad").exists())

    def test_private_package_saves_sandwiches_and_eight_drinks(self):
        summary = self._create_summary()
        data = self._triple_customer_menu_data()
        data.update({
            "room_type": PartySummary.RoomType.PRIVATE,
            "private_sandwich": "Finger sandwiches 16pcs (Tuna)",
            "private_sandwich_note": "No mayonnaise",
        })
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertRedirects(response, reverse("customer_menu_thanks", args=(summary.customer_menu_token,)))
        summary.refresh_from_db()
        adult_items = summary.menu_items.filter(category="adult")
        sandwich = adult_items.get(item="Finger sandwiches 16pcs (Tuna)")
        self.assertEqual(sandwich.notes, "No mayonnaise")
        self.assertEqual(adult_items.get(item="Soft drinks / juice").quantity, "8 jugs")

    def test_customer_kids_quantities_must_match_children(self):
        summary = self._create_summary()
        data = self._customer_menu_data()
        data["kids_hot_3_qty"] = "4"
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hot food quantities must add up")
        summary.refresh_from_db()
        self.assertIsNone(summary.customer_menu_submitted_at)
        self.assertFalse(summary.menu_items.exists())

    def test_customer_cannot_choose_more_than_two_kids_options(self):
        summary = self._create_summary()
        data = self._customer_menu_data()
        data["kids_hot_1_selected"] = "on"
        data["kids_hot_1_qty"] = "1"
        data["kids_hot_3_qty"] = "4"
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose no more than two hot food options")

    def test_southland_triple_menu_is_selected_by_room_type_and_saves_notes(self):
        summary = self._create_summary()
        response = self.client.post(
            reverse("customer_menu", args=(summary.customer_menu_token,)),
            self._triple_customer_menu_data(),
        )
        self.assertRedirects(response, reverse("customer_menu_thanks", args=(summary.customer_menu_token,)))
        summary.refresh_from_db()
        self.assertEqual(summary.room_type, PartySummary.RoomType.TRIPLE)
        self.assertEqual(summary.owner_name, "Triple Customer")
        self.assertEqual(summary.food_ready, "Ready at 3:15 PM")
        self.assertEqual(summary.kids_count, 25)
        pizza_rows = summary.menu_items.filter(category="adult", item__startswith="Pizza")
        self.assertEqual(pizza_rows.count(), 3)
        self.assertEqual(sum(int(row.quantity) for row in pizza_rows), 4)
        self.assertEqual(
            summary.menu_items.get(category="adult", item="Vege Fryer Platter").notes,
            "No onion",
        )
        self.assertEqual(
            summary.menu_items.get(category="adult", item="Seasonal fruit platter").notes,
            "No kiwi",
        )
        self.assertEqual(
            summary.menu_items.get(category="adult", item="Pesto pasta bowl without chicken").notes,
            "No parmesan",
        )
        self.assertEqual(summary.menu_items.get(category="adult", item="Soft drinks / juice").quantity, "6 jugs")

    def test_triple_pizza_flavour_quantities_must_add_up_to_four(self):
        summary = self._create_summary()
        data = self._triple_customer_menu_data()
        data["triple_pizza_2_qty"] = "0"
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pizza flavour quantities must add up to 4")
        summary.refresh_from_db()
        self.assertIsNone(summary.customer_menu_submitted_at)

    def test_triple_menu_requires_one_main_package_choice(self):
        summary = self._create_summary()
        data = self._triple_customer_menu_data()
        data["triple_taco"] = ""
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose one option")
        summary.refresh_from_db()
        self.assertIsNone(summary.customer_menu_submitted_at)

    def test_earlier_food_ready_requires_a_time(self):
        summary = self._create_summary()
        data = self._triple_customer_menu_data()
        data["food_ready_time"] = ""
        response = self.client.post(reverse("customer_menu", args=(summary.customer_menu_token,)), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter the earlier time")
