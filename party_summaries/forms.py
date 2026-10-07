from django import forms
from django.forms import formset_factory

from accounts.models import Location, User

from .models import PartyIntakeLink, PartySummary


KIDS_HOT_FOOD_CHOICES = (
    ("Nuggets & Chips", "Nuggets & Chips"),
    ("Fish fingers & Chips", "Fish fingers & Chips"),
    ("Ham & Cheese Toast", "Ham & Cheese Toast"),
    ("Spring rolls & Chips", "Spring rolls & Chips"),
    ("Kid spaghetti", "Kid spaghetti"),
    ("Tomato & Cheese Toast", "Tomato & Cheese Toast"),
)
KIDS_DESSERT_CHOICES = (
    ("Mini cupcakes", "Mini cupcakes"),
    ("Yogurt berries smoothie", "Yogurt berries smoothie"),
)
KIDS_FOOD_TAGS = {
    "Nuggets & Chips": (("popular", "Popular"),),
    "Spring rolls & Chips": (("vegan", "Vegan"), ("vegetarian", "Vegetarian"), ("popular", "Popular")),
    "Tomato & Cheese Toast": (("vegetarian", "Vegetarian"),),
    "Mini cupcakes": (("vegetarian", "Vegetarian"), ("popular", "Popular")),
    "Yogurt berries smoothie": (("vegetarian", "Vegetarian"),),
}
ADULT_FRYER_CHOICES = (
    ("Mixed Fryer platter", "Mixed Fryer platter (spring rolls, karaage chicken, coconut crumbed prawn, fish fingers, wedges)"),
    ("Vege Fryer Platter", "Vege Fryer Platter (chips, sweet potato chips, wedges, spring rolls)"),
)
ADULT_STARTER_CHOICES = (
    ("Mini Burger sliders - 10pcs (Pork)", "Mini Burger sliders - 10pcs (Pork)"),
    ("Mini Burger sliders - 10pcs (Prawn)", "Mini Burger sliders - 10pcs (Prawn)"),
    ("Mini Burger sliders - 10pcs (Vege)", "Mini Burger sliders - 10pcs (Vege)"),
    ("Finger Sandwiches - 16pcs (Tuna)", "Finger Sandwiches - 16pcs (Tuna)"),
    ("Finger Sandwiches - 16pcs (Eggs)", "Finger Sandwiches - 16pcs (Eggs)"),
    ("Finger Sandwiches - 16pcs (Cheese & Tomato)", "Finger Sandwiches - 16pcs (Cheese & Tomato)"),
)
ADULT_MAIN_CHOICES = (
    ("Taco platter 12pcs (Karaage chicken)", "Taco platter - Karaage chicken (12 pieces)"),
    ("Taco platter 12pcs (Fish)", "Taco platter - Fish (12 pieces)"),
    ("Taco platter 12pcs (Black Beans)", "Taco platter - Black Beans (12 pieces)"),
    ("__four_pizzas__", "Four pizzas - Margherita, Pepperoni, Vegetarian and Cheese"),
)
ADULT_PASTA_CHOICES = (
    ("Chicken Pesto Pasta Bowl", "Chicken Pesto Pasta Bowl"),
    ("Pesto Pasta Bowl without chicken", "Pesto Pasta Bowl without chicken"),
    ("Greek Salad", "Greek Salad"),
)
TRIPLE_FRYER_CHOICES = (
    ("Mixed Fryer platter", "Mixed Fryer platter (spring rolls, karaage chicken, coconut crumbed prawn, fish fingers, wedges)"),
    ("Vege Fryer Platter", "Vege Fryer Platter (chips, sweet potato chips, wedges, spring rolls)"),
)
TRIPLE_PIZZA_CHOICES = (
    ("Pizza (Margherita, 10-inch)", "Margherita"),
    ("Pizza (Pepperoni, 10-inch)", "Pepperoni"),
    ("Pizza (Vegetarian, 10-inch)", "Vegetarian"),
    ("Pizza (Cheese, 10-inch)", "Cheese"),
)
TRIPLE_SALAD_CHOICES = (
    ("Greek salad bowl", "Greek salad bowl"),
    ("Caesar salad bowl", "Caesar salad bowl"),
)
TRIPLE_BURGER_CHOICES = (
    ("Mini burger platter 10pcs (Pork)", "Mini burger platter 10pcs (Pork)"),
    ("Mini burger platter 10pcs (Prawn)", "Mini burger platter 10pcs (Prawn)"),
    ("Mini burger platter 10pcs (Vegetarian)", "Mini burger platter 10pcs (Vegetarian)"),
)
TRIPLE_TACO_CHOICES = (
    ("Taco platter 12pcs (Karaage chicken)", "Taco platter 12pcs (Karaage chicken)"),
    ("Taco platter 12pcs (Fish)", "Taco platter 12pcs (Fish)"),
    ("Taco platter 12pcs (Black Beans)", "Taco platter 12pcs (Black Beans)"),
)
TRIPLE_PASTA_CHOICES = (
    ("Chicken pesto pasta bowl", "Chicken pesto pasta bowl"),
    ("Pesto pasta bowl without chicken", "Pesto pasta bowl without chicken (vegetarian)"),
)
TRIPLE_TOAST_CHOICES = (
    ("Smoked salmon toast 12pcs", "Smoked salmon toast (12 pieces)"),
    ("Mushroom toast 12pcs (vegetarian)", "Mushroom toast (12 pieces, vegetarian)"),
)
TRIPLE_SUSHI_CHOICES = (
    ("Japanese sushi platter (assorted)", "Assorted sushi"),
    ("Japanese sushi platter (vegetarian)", "Vegetarian sushi"),
)
PRIVATE_SANDWICH_CHOICES = (
    ("Finger sandwiches 16pcs (Tuna)", "Finger sandwiches 16pcs (Tuna)"),
    ("Finger sandwiches 16pcs (Eggs)", "Finger sandwiches 16pcs (Eggs)"),
    ("Finger sandwiches 16pcs (Cheese & Tomato)", "Finger sandwiches 16pcs (Cheese & Tomato)"),
)
EXTRA_MENU_OPTIONS = (
    ("Mixed fryer platter (assorted)", "88.00"), ("Mixed fryer platter (vege)", "88.00"),
    ("Mini burger sliders 10pcs (Pork)", "75.00"), ("Mini burger sliders 10pcs (Prawn)", "75.00"),
    ("Mini burger sliders 10pcs (Vege)", "75.00"), ("Mini burger sliders 10pcs (Chicken)", "75.00"),
    ("Mini burger sliders 10pcs (Beef)", "75.00"), ("Japanese sushi platter (assorted)", "88.00"),
    ("Japanese sushi platter (vege)", "88.00"), ("Taco platter 12pcs (Karaage chicken)", "68.00"),
    ("Taco platter 12pcs (Fish)", "68.00"), ("Taco platter 12pcs (Black Beans)", "68.00"),
    ("Fruit Platter", "78.00"), ("Finger Sandwiches 16pcs (Tuna)", "65.00"),
    ("Finger Sandwiches 16pcs (Eggs)", "65.00"), ("Finger Sandwiches 16pcs (Cheese & Tomato)", "65.00"),
    ("Mixed Grilled Platter", "128.00"), ("Grilled Salmon Platter", "128.00"),
    ("Lamb Souvlaki platter", "88.00"), ("Grilled chicken breast platter", "88.00"),
    ("Grilled Beef Skewer platter", "88.00"), ("Grilled Pork ribs platter", "88.00"),
    ("Grilled Lobster platter", "88.00"), ("Chicken pesto pasta bowl", "68.00"),
    ("Pesto pasta bowl without chicken", "68.00"), ("Greek Salad Bowl", "38.00"),
    ("Greek Salad Bowl with Grilled chicken", "48.00"), ("Beef Bolognese Spaghetti", "68.00"),
    ("Creamy Prawn Linguine", "68.00"), ("Cocktail Prawn Salad", "96.00"),
    ("Pizza (Cheese)", "19.00"), ("Pizza (Vege)", "19.00"),
    ("Pizza (Margherita)", "19.00"), ("Pizza (Pepperoni)", "19.00"),
    ("Chips Tray", "38.00"), ("Nuggets Tray", "38.00"),
    ("Spring rolls tray", "48.00"), ("Karaage Chicken Tray 15pcs", "48.00"),
    ("Wedges & Chips Tray", "38.00"), ("Calamari & Chips Tray", "38.00"),
    ("Smoked Salmon Avocado Toast 10pcs", "45.00"), ("Millennial Mushroom Toast 10pcs", "45.00"),
    ("Ham and Cheese Toast 10pcs", "35.00"), ("Cheese Toast 10pcs", "35.00"),
    ("Chicken Schnitzel Wrap platter 10 halves", "65.00"),
)


class PartySummaryForm(forms.ModelForm):
    decoration_example_upload = forms.FileField(
        label="Decoration example",
        required=False,
        widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        help_text="JPG, PNG or WebP, up to 5 MB.",
    )
    remove_decoration_example = forms.BooleanField(
        label="Remove current decoration example",
        required=False,
    )
    class Meta:
        model = PartySummary
        fields = (
            "location", "party_date", "party_time", "owner_name", "owner_number",
            "food_ready", "room_type", "kids_count", "adults_count", "deposit_method",
            "kids_name", "gender", "age", "theme", "balloon_color", "special_note",
            "rsvp_information",
            "dietary_requirements", "voucher_menu_notes",
            "deposit_amount", "package_name", "package_amount", "other_charges",
        )
        labels = {
            "party_time": "Party time", "owner_name": "Owner name", "owner_number": "Owner number",
            "food_ready": "Food ready", "kids_count": "Kids", "adults_count": "Adults",
            "deposit_method": "Deposit method", "kids_name": "Kids name", "balloon_color": "Balloon color",
            "special_note": "Special note", "rsvp_information": "RSVP information",
            "deposit_amount": "Deposit paid", "package_name": "Package",
            "dietary_requirements": "Dietary requirements", "voucher_menu_notes": "Food voucher menu notes",
            "package_amount": "Package price", "other_charges": "Other charges / adjustments",
        }
        widgets = {
            "party_date": forms.DateInput(attrs={"type": "date"}),
            "party_time": forms.TextInput(attrs={"placeholder": "e.g. 5–8pm"}),
            "owner_number": forms.TextInput(attrs={"inputmode": "tel"}),
            "food_ready": forms.TextInput(attrs={"placeholder": "e.g. 5:30pm"}),
            "kids_count": forms.NumberInput(attrs={"min": 0}),
            "adults_count": forms.NumberInput(attrs={"min": 0}),
            "special_note": forms.Textarea(attrs={"rows": 4}),
            "rsvp_information": forms.Textarea(attrs={"rows": 2}),
            "dietary_requirements": forms.Textarea(attrs={"rows": 2, "class": "compact-dietary-input"}),
            "voucher_menu_notes": forms.Textarea(attrs={"rows": 3}),
            "deposit_amount": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "package_amount": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "other_charges": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for name in ("kids_count", "adults_count", "deposit_amount", "package_name", "package_amount", "other_charges"):
            self.fields[name].required = False
        self.fields["location"].queryset = Location.objects.order_by("name")
        location = None
        if self.is_bound and self.data.get("location"):
            location = Location.objects.filter(pk=self.data.get("location")).first()
        elif self.instance and not self.instance._state.adding:
            location = self.instance.location
        elif user.location_id:
            location = user.location
        if location is None:
            location = Location.objects.filter(code=Location.Code.SOUTHLAND).first()
        self.package_location_code = location.code if location else Location.Code.SOUTHLAND
        if self.package_location_code == Location.Code.CANBERRA:
            self.fields["room_type"].choices = (
                (PartySummary.RoomType.SINGLE, "Single room"),
                (PartySummary.RoomType.DOUBLE_LITE, "Double room Lite"),
                (PartySummary.RoomType.DOUBLE, "Double room"),
                (PartySummary.RoomType.PRIVATE_2HOUR, "Private 2 hour"),
                (PartySummary.RoomType.PRIVATE_3HOUR, "Private 3 hour"),
            )
        else:
            self.fields["room_type"].choices = (
                (PartySummary.RoomType.SINGLE, PartySummary.RoomType.SINGLE.label),
                (PartySummary.RoomType.DOUBLE, PartySummary.RoomType.DOUBLE.label),
                (PartySummary.RoomType.TRIPLE, PartySummary.RoomType.TRIPLE.label),
                (PartySummary.RoomType.PRIVATE, PartySummary.RoomType.PRIVATE.label),
                (PartySummary.RoomType.SMALL_GATHERING, PartySummary.RoomType.SMALL_GATHERING.label),
            )
        self.fields["package_name"].choices = [
            ("", "---------"),
            *PartySummary.package_choices_for_location(self.package_location_code),
            (PartySummary.Package.CUSTOM, PartySummary.Package.CUSTOM.label),
        ]
        if user.role == User.Role.STAFF:
            self.fields.pop("location")

    def clean(self):
        cleaned = super().clean()
        cleaned["kids_count"] = cleaned.get("kids_count") or 0
        cleaned["adults_count"] = cleaned.get("adults_count") or 0
        cleaned["deposit_amount"] = cleaned.get("deposit_amount") or 0
        cleaned["other_charges"] = cleaned.get("other_charges") or 0
        package = cleaned.get("package_name") or PartySummary.Package.CUSTOM
        cleaned["package_name"] = package
        location = cleaned.get("location")
        if location is None and self.user.location_id:
            location = self.user.location
        if location is None and self.instance and not self.instance._state.adding:
            location = self.instance.location
        prices = PartySummary.package_prices_for_location(location.code if location else None)
        if package in prices and cleaned.get("package_amount") in (None, 0):
            cleaned["package_amount"] = prices[package]
        else:
            cleaned["package_amount"] = cleaned.get("package_amount") or 0
        return cleaned

    def clean_decoration_example_upload(self):
        upload = self.cleaned_data.get("decoration_example_upload")
        if not upload:
            return upload
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose an image smaller than 5 MB.")
        if upload.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise forms.ValidationError("Choose a JPG, PNG or WebP image.")
        return upload


class PartyIntakeLinkForm(forms.ModelForm):
    class Meta:
        model = PartyIntakeLink
        fields = ("location", "owner_name", "owner_number", "owner_email")
        labels = {
            "owner_name": "Customer name",
            "owner_number": "Customer phone",
            "owner_email": "Customer email (optional)",
        }
        widgets = {
            "owner_number": forms.TextInput(attrs={"inputmode": "tel"}),
            "owner_email": forms.EmailInput(attrs={"placeholder": "Used only as a reference for now"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["location"].queryset = Location.objects.order_by("name")
        if user.role == User.Role.STAFF:
            self.fields.pop("location")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user.role == User.Role.STAFF:
            instance.location = self.user.location
        if commit:
            instance.save()
        return instance


class CustomerPartyIntakeForm(forms.Form):
    party_date = forms.DateField(label="Party date", widget=forms.DateInput(attrs={"type": "date"}))
    party_time = forms.CharField(
        label="Party time", max_length=80,
        widget=forms.TextInput(attrs={"placeholder": "e.g. 1:00pm–3:00pm"}),
    )
    theme = forms.CharField(label="Party theme", max_length=200)
    kids_name = forms.CharField(label="Kid's name", max_length=250)
    age = forms.CharField(label="Turning age", max_length=40)
    rsvp_information = forms.CharField(
        label="RSVP information", max_length=1000,
        help_text="For example: RSVP contact name, phone number and RSVP deadline.",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "e.g. RSVP to Flora on 0400 000 000 by 20 October"}),
    )


class CustomerMenuForm(forms.Form):
    party_date = forms.DateField(label="Party date", widget=forms.DateInput(attrs={"type": "date"}))
    party_time = forms.CharField(label="Party time", max_length=80, widget=forms.TextInput(attrs={"placeholder": "e.g. 2:00pm-5:00pm"}))
    owner_name = forms.CharField(label="Owner name", max_length=200)
    owner_number = forms.CharField(label="Owner number", max_length=50, widget=forms.TextInput(attrs={"inputmode": "tel"}))
    room_type = forms.ChoiceField(label="Room type", choices=())
    kids_count = forms.IntegerField(label="Number of children", min_value=1, max_value=100)
    adults_count = forms.IntegerField(label="Number of adults", min_value=0, max_value=150)
    dietary_requirements = forms.CharField(
        label="Allergies or dietary requirements", required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Please include the guest's name and requirement."}),
    )
    food_ready_choice = forms.ChoiceField(
        label="When should the food be ready?",
        choices=(("after_30", "Ready 30 minutes after the party starts"), ("earlier", "Ready earlier at a specific time")),
        widget=forms.RadioSelect,
    )
    food_ready_time = forms.TimeField(
        label="Earlier ready time", required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    adult_fryer = forms.ChoiceField(label="Fryer platter - pick one", choices=ADULT_FRYER_CHOICES, required=False, widget=forms.RadioSelect)
    adult_food_avoid = forms.CharField(label="Food to avoid", required=False, max_length=250)
    voucher_menu_notes = forms.CharField(
        label="Notes", required=False, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Add any notes for your adult food order."}),
    )
    adult_starter = forms.ChoiceField(label="Burger or sandwiches - pick one", choices=ADULT_STARTER_CHOICES, required=False, widget=forms.RadioSelect)
    adult_main = forms.ChoiceField(label="Taco platter or four pizzas - pick one", choices=ADULT_MAIN_CHOICES, required=False, widget=forms.RadioSelect)
    adult_pasta = forms.ChoiceField(label="Pasta or salad - pick one", choices=ADULT_PASTA_CHOICES, required=False, widget=forms.RadioSelect)

    triple_fryer = forms.ChoiceField(label="Mixed fryer platter", choices=TRIPLE_FRYER_CHOICES, required=False, widget=forms.RadioSelect)
    triple_fryer_note = forms.CharField(label="Fryer platter notes", required=False, max_length=500)
    triple_fruit_note = forms.CharField(label="Any fruit to avoid / fruit platter notes", required=False, max_length=500)
    triple_pizza_note = forms.CharField(label="Pizza notes", required=False, max_length=500)
    triple_salad = forms.ChoiceField(label="Salad bowl", choices=TRIPLE_SALAD_CHOICES, required=False, widget=forms.RadioSelect)
    triple_salad_note = forms.CharField(label="Salad notes", required=False, max_length=500)
    triple_burger = forms.ChoiceField(label="Mini burger platter flavour", choices=TRIPLE_BURGER_CHOICES, required=False, widget=forms.RadioSelect)
    triple_burger_note = forms.CharField(label="Mini burger notes", required=False, max_length=500)
    triple_taco = forms.ChoiceField(label="Taco platter flavour", choices=TRIPLE_TACO_CHOICES, required=False, widget=forms.RadioSelect)
    triple_taco_note = forms.CharField(label="Taco notes", required=False, max_length=500)
    triple_pasta = forms.ChoiceField(label="Pesto pasta bowl", choices=TRIPLE_PASTA_CHOICES, required=False, widget=forms.RadioSelect)
    triple_pasta_note = forms.CharField(label="Pesto pasta notes", required=False, max_length=500)
    triple_toast = forms.ChoiceField(label="Toast platter", choices=TRIPLE_TOAST_CHOICES, required=False, widget=forms.RadioSelect)
    triple_toast_note = forms.CharField(label="Toast notes", required=False, max_length=500)
    triple_sushi = forms.ChoiceField(label="Sushi platter", choices=TRIPLE_SUSHI_CHOICES, required=False, widget=forms.RadioSelect)
    triple_sushi_note = forms.CharField(label="Sushi notes", required=False, max_length=500)
    private_sandwich = forms.ChoiceField(label="Finger sandwiches", choices=PRIVATE_SANDWICH_CHOICES, required=False, widget=forms.RadioSelect)
    private_sandwich_note = forms.CharField(label="Finger sandwiches notes", required=False, max_length=500)
    triple_drinks_note = forms.CharField(label="Soft drinks / juice notes", required=False, max_length=500)

    def __init__(self, *args, **kwargs):
        venue_code = kwargs.pop("venue_code", None)
        super().__init__(*args, **kwargs)
        self.is_canberra = venue_code == Location.Code.CANBERRA
        if self.is_canberra:
            self.fields["room_type"].choices = (
                (PartySummary.RoomType.SINGLE, "Single room"),
                (PartySummary.RoomType.DOUBLE_LITE, "Double room Lite"),
                (PartySummary.RoomType.DOUBLE, "Double room"),
                (PartySummary.RoomType.PRIVATE_2HOUR, "Private 2 hour"),
                (PartySummary.RoomType.PRIVATE_3HOUR, "Private 3 hour"),
            )
        else:
            self.fields["room_type"].choices = (
                (PartySummary.RoomType.SINGLE, "Essential (single room)"),
                (PartySummary.RoomType.DOUBLE, "Signature (double room)"),
                (PartySummary.RoomType.TRIPLE, "Ultimate (triple room)"),
                (PartySummary.RoomType.PRIVATE, "Private (whole venue hire)"),
            )
        note_fields = [name for name in self.fields if name.endswith("_note")]
        for name in note_fields:
            self.fields[name].widget.attrs.update({"placeholder": "Optional notes", "class": "menu-note-input"})
        for index, (_value, label) in enumerate(TRIPLE_PIZZA_CHOICES):
            self.fields[f"triple_pizza_{index}_qty"] = forms.IntegerField(
                label=f"{label} pizzas", min_value=0, max_value=4, required=False,
                widget=forms.NumberInput(attrs={"inputmode": "numeric", "min": 0, "max": 4}),
            )
        for prefix, choices in (
            ("kids_hot", KIDS_HOT_FOOD_CHOICES),
            ("kids_dessert", KIDS_DESSERT_CHOICES),
        ):
            for index, (_value, label) in enumerate(choices):
                self.fields[f"{prefix}_{index}_selected"] = forms.BooleanField(label=label, required=False)
                self.fields[f"{prefix}_{index}_qty"] = forms.IntegerField(
                    label=f"Number of {label} meals", min_value=1, max_value=100, required=False,
                    widget=forms.NumberInput(attrs={"inputmode": "numeric", "placeholder": "Qty", "disabled": True}),
                )
        for index, (name, price) in enumerate(EXTRA_MENU_OPTIONS):
            self.fields[f"extra_{index}_selected"] = forms.BooleanField(label=name, required=False)
            self.fields[f"extra_{index}_qty"] = forms.IntegerField(
                label=f"Quantity of {name}", min_value=1, max_value=50, required=False,
                widget=forms.NumberInput(attrs={"inputmode": "numeric", "placeholder": "Qty", "disabled": True, "data-unit-price": price}),
            )

        # Disabled fields are not submitted, but saved selections must remain editable on GET.
        for prefix, choices in (
            ("kids_hot", KIDS_HOT_FOOD_CHOICES),
            ("kids_dessert", KIDS_DESSERT_CHOICES),
        ):
            for index, _choice in enumerate(choices):
                if self.initial.get(f"{prefix}_{index}_selected") or self.data.get(f"{prefix}_{index}_selected"):
                    self.fields[f"{prefix}_{index}_qty"].widget.attrs.pop("disabled", None)
        for index, _option in enumerate(EXTRA_MENU_OPTIONS):
            if self.initial.get(f"extra_{index}_selected") or self.data.get(f"extra_{index}_selected"):
                self.fields[f"extra_{index}_qty"].widget.attrs.pop("disabled", None)

    def _rows(self, prefix, choices):
        return [
            {
                "label": label,
                "selected": self[f"{prefix}_{index}_selected"],
                "quantity": self[f"{prefix}_{index}_qty"],
                "tags": KIDS_FOOD_TAGS.get(value, ()),
            }
            for index, (value, label) in enumerate(choices)
        ]

    @property
    def kids_hot_rows(self):
        return self._rows("kids_hot", KIDS_HOT_FOOD_CHOICES)

    @property
    def kids_dessert_rows(self):
        return self._rows("kids_dessert", KIDS_DESSERT_CHOICES)

    @property
    def extra_rows(self):
        return [
            {
                "name": name,
                "price": price,
                "selected": self[f"extra_{index}_selected"],
                "quantity": self[f"extra_{index}_qty"],
            }
            for index, (name, price) in enumerate(EXTRA_MENU_OPTIONS)
        ]

    @property
    def extra_groups(self):
        rows = self.extra_rows
        return [
            {"title": "Platters to share", "rows": rows[0:23]},
            {"title": "Salad and pasta bowls", "rows": rows[23:30]},
            {"title": "Pizzas", "rows": rows[30:34]},
            {"title": "Fryer trays", "rows": rows[34:40]},
            {"title": "Toast and wraps", "rows": rows[40:45]},
        ]

    @property
    def triple_pizza_rows(self):
        return [
            {"label": label, "quantity": self[f"triple_pizza_{index}_qty"]}
            for index, (_value, label) in enumerate(TRIPLE_PIZZA_CHOICES)
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("food_ready_choice") == "earlier" and not cleaned.get("food_ready_time"):
            self.add_error("food_ready_time", "Enter the earlier time when the food should be ready.")
        kids_count = cleaned.get("kids_count")
        if kids_count:
            self._validate_checkbox_group(cleaned, "kids_hot", KIDS_HOT_FOOD_CHOICES, kids_count, "hot food")
            if self.is_canberra:
                self._validate_checkbox_group(cleaned, "kids_dessert", KIDS_DESSERT_CHOICES, kids_count, "dessert")
        room_type = cleaned.get("room_type")
        package_required_choices = {
            PartySummary.RoomType.SINGLE: ("triple_fryer",),
            PartySummary.RoomType.DOUBLE: (
                "triple_fryer", "triple_salad", "triple_burger", "triple_toast",
            ),
            PartySummary.RoomType.TRIPLE: (
                "triple_fryer", "triple_salad", "triple_burger", "triple_taco",
                "triple_pasta", "triple_toast", "triple_sushi",
            ),
            PartySummary.RoomType.PRIVATE: (
                "triple_fryer", "triple_salad", "triple_burger", "triple_taco",
                "triple_pasta", "private_sandwich", "triple_toast", "triple_sushi",
            ),
        }
        if self.is_canberra and room_type == PartySummary.RoomType.DOUBLE:
            self._validate_required_choices(
                cleaned, ("adult_fryer", "adult_starter", "adult_main", "adult_pasta"),
            )
            if cleaned.get("adult_main") == "__four_pizzas__":
                pizza_total = sum(
                    cleaned.get(f"triple_pizza_{index}_qty") or 0
                    for index in range(len(TRIPLE_PIZZA_CHOICES))
                )
                if pizza_total != 4:
                    self.add_error(
                        None,
                        f"The pizza flavour quantities must add up to 4. You currently have {pizza_total}.",
                    )
        elif not self.is_canberra and room_type in package_required_choices:
            self._validate_required_choices(cleaned, package_required_choices[room_type])
            pizza_total = sum(
                cleaned.get(f"triple_pizza_{index}_qty") or 0
                for index in range(len(TRIPLE_PIZZA_CHOICES))
            )
            pizza_target = 2 if room_type == PartySummary.RoomType.SINGLE else 4
            if pizza_total != pizza_target:
                self.add_error(
                    None,
                    f"The pizza flavour quantities must add up to {pizza_target}. You currently have {pizza_total}.",
                )
        self._validate_extra_items(cleaned)
        return cleaned

    def _validate_required_choices(self, cleaned, names):
        for name in names:
            if not cleaned.get(name):
                self.add_error(name, "Choose one option.")

    def _validate_checkbox_group(self, cleaned, prefix, choices, kids_count, label):
        selected_count = 0
        total = 0
        for index, _choice in enumerate(choices):
            selected_name = f"{prefix}_{index}_selected"
            quantity_name = f"{prefix}_{index}_qty"
            selected = cleaned.get(selected_name, False)
            quantity = cleaned.get(quantity_name)
            if selected:
                selected_count += 1
                if quantity is None:
                    self.add_error(quantity_name, "Enter the number of children for this choice.")
                else:
                    total += quantity
            elif quantity:
                self.add_error(selected_name, "Tick this option or remove its quantity.")
        if selected_count == 0:
            self.add_error(None, f"Choose at least one {label} option.")
        elif selected_count > 2:
            self.add_error(None, f"Choose no more than two {label} options.")
        if selected_count and total != kids_count:
            self.add_error(None, f"The {label} quantities must add up to the number of children ({kids_count}).")

    def _validate_extra_items(self, cleaned):
        for index, _option in enumerate(EXTRA_MENU_OPTIONS):
            selected_name = f"extra_{index}_selected"
            quantity_name = f"extra_{index}_qty"
            selected = cleaned.get(selected_name, False)
            quantity = cleaned.get(quantity_name)
            if selected and quantity is None:
                self.add_error(quantity_name, "Enter how many you would like.")
            elif not selected and quantity:
                self.add_error(selected_name, "Tick this add-on or remove its quantity.")


class StandardMenuItemForm(forms.Form):
    quantity = forms.CharField(required=False, max_length=40, widget=forms.TextInput(attrs={"placeholder": "Qty"}))
    item = forms.CharField(required=False, max_length=250, widget=forms.TextInput(attrs={"placeholder": "Select or type an item"}))
    notes = forms.CharField(required=False, max_length=500, widget=forms.TextInput(attrs={"placeholder": "Notes"}))
    amount = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "$0.00", "min": 0, "step": "0.01"}))

    def clean(self):
        cleaned = super().clean()
        if (cleaned.get("item") or "").strip().casefold() == "refillable water":
            cleaned["notes"] = ""
        return cleaned


class ExtraMenuItemForm(StandardMenuItemForm):
    amount = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "$0.00", "min": 0, "step": "0.01"}))


class BillItemForm(forms.Form):
    name = forms.CharField(required=False, max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Charge name"}))
    amount = forms.DecimalField(required=False, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "$0.00", "step": "0.01"}))

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("name") or "").strip()
        amount = cleaned.get("amount")
        if amount is not None and not name:
            self.add_error("name", "Enter a name for this charge.")
        if name and amount is None:
            self.add_error("amount", "Enter the price for this charge.")
        cleaned["name"] = name
        return cleaned


def menu_formsets(*, data=None, initial=None, editing=False):
    initial = initial or {}
    adult_initial = initial.get("adult", [])
    kids_initial = initial.get("kids", [])
    extra_initial = initial.get("extra", [])
    bill_initial = initial.get("bill", [])
    options = {"can_delete": True, "max_num": 20, "validate_max": True}
    AdultSet = formset_factory(StandardMenuItemForm, extra=1 if editing else max(0, 8 - len(adult_initial)), **options)
    KidsSet = formset_factory(StandardMenuItemForm, extra=1 if editing else max(0, 3 - len(kids_initial)), **options)
    ExtraSet = formset_factory(ExtraMenuItemForm, extra=1 if editing else max(0, 5 - len(extra_initial)), **options)
    BillSet = formset_factory(BillItemForm, extra=1, **options)
    return {
        "adult_formset": AdultSet(data, prefix="adult", initial=adult_initial),
        "kids_formset": KidsSet(data, prefix="kids", initial=kids_initial),
        "extra_formset": ExtraSet(data, prefix="extra", initial=extra_initial),
        "bill_formset": BillSet(data, prefix="bill", initial=bill_initial),
    }
