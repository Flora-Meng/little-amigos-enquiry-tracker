from django.db import migrations


THEMES = (
    ("Spider-Man", "adventure", "superhero spiderman", (6,)),
    ("Frozen", "magic", "snow ice elsa", (7, 8)),
    ("Mermaid", "magic", "under the sea ocean", (9, 10)),
    ("Princesses", "magic", "princess disney", (11,)),
    ("Dinosaurs", "adventure", "dino jurassic", (12,)),
    ("Butterfly", "magic", "garden fairy", (13, 14)),
    ("Hello Kitty & Friends", "favourites", "sanrio my melody kuromi", (15,)),
    ("Superheroes", "adventure", "hero marvel avengers", (16,)),
    ("Teletubbies", "favourites", "tinky winky dipsy lala po", (17,)),
    ("Unicorn", "magic", "rainbow magical", (18,)),
    ("Rainbow", "magic", "colourful", (19,)),
    ("Barbie", "favourites", "pink doll", (20,)),
    ("Pokémon", "favourites", "pokemon pikachu", (21, 22)),
    ("Blippi & Construction", "adventure", "building trucks digger", (23,)),
    ("Peppa Pig", "favourites", "george pig", (24,)),
    ("Mickey, Minnie & Daisy", "favourites", "disney mouse", (25, 26)),
    ("Fire Engines & Trucks", "adventure", "firefighter vehicles", (27,)),
    ("Paw Patrol", "favourites", "chase marshall skye", (28, 29, 30)),
    ("Sweet Strawberries", "magic", "strawberry fruit pink", (31,)),
    ("Tangled", "magic", "rapunzel princess", (32,)),
    ("Bluey", "favourites", "bingo", (33,)),
    ("Disney Cars", "adventure", "lightning mcqueen racing", (34,)),
    ("Toy Story", "favourites", "woody buzz", (35,)),
    ("Thomas & Friends", "adventure", "train railway", (36,)),
    ("Wild Animals", "adventure", "jungle safari zoo", (37,)),
    ("Gabby's Dollhouse", "favourites", "gabby cats", (38,)),
    ("Super Mario", "favourites", "mario luigi nintendo", (39,)),
    ("K-pop Demon Hunters", "favourites", "kpop music", (40, 41, 42)),
    ("Animal Crossing", "favourites", "nintendo animals", (43,)),
    ("We're Going on a Bear Hunt", "adventure", "bear woodland", (44,)),
    ("Custom Printed Theme", "custom", "personalised custom name board", (47,)),
)

ADDONS = (
    ("Face painting", "1.5 hours $330 · 2 hours $380", 330, "Professional face painting for party guests.", 1),
    ("Customised cake", "From $188", 188, "Single-tier, two-tier and tall cake options. Name and number are included.", 1),
    ("Entertainer or mascot", "1 hour $380 · 3 hours $580", 380, "Choose a character entertainer or mascot appearance.", 1),
    ("Professional photographer", "$200 per hour · 2 hours $380", 200, "Professional party photography coverage.", 2),
    ("Party bags", "$8 per bag", 8, "Includes some lollies and a small toy.", 2),
)


def seed_showcase(apps, schema_editor):
    Theme = apps.get_model("accounts", "SouthlandShowcaseTheme")
    Photo = apps.get_model("accounts", "SouthlandShowcaseThemePhoto")
    Addon = apps.get_model("accounts", "SouthlandShowcaseAddon")

    for order, (name, category, search_terms, pages) in enumerate(THEMES, 1):
        theme = Theme.objects.create(
            name=name,
            category=category,
            search_terms=search_terms,
            sort_order=order,
            description=(
                "A personalised printed theme with backdrop, character cut-outs and a name board."
                if category == "custom" else "Available in room layouts shown in the gallery."
            ),
        )
        for photo_order, page in enumerate(pages, 1):
            Photo.objects.create(
                theme=theme,
                static_path=f"package_showcase/southland/theme-pages/page-{page:02d}.jpg",
                sort_order=photo_order,
            )

    for order, (name, price_label, price_from, details, page) in enumerate(ADDONS, 1):
        Addon.objects.create(
            name=name,
            price_label=price_label,
            price_from=price_from,
            details=details,
            static_path=f"package_showcase/southland/addon-pages/page-{page}.jpg",
            sort_order=order,
        )


def unseed_showcase(apps, schema_editor):
    apps.get_model("accounts", "SouthlandShowcaseAddon").objects.all().delete()
    apps.get_model("accounts", "SouthlandShowcaseTheme").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_southlandshowcaseaddon_southlandshowcasetheme_and_more")]
    operations = [migrations.RunPython(seed_showcase, unseed_showcase)]
