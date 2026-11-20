from django.db import migrations


THEMES = (
    ("Animal Crossing", "favourites", "animal-crossing", 1),
    ("Barbie", "favourites", "barbie", 2),
    ("Blippi & Construction", "adventure", "blippi-construction", 2),
    ("Bluey", "favourites", "bluey", 1),
    ("Butterfly", "magic", "butterfly", 4),
    ("Dinosaurs", "adventure", "dinosaurs", 3),
    ("Disney Cars", "adventure", "disney-cars", 2),
    ("Fire Engines & Trucks", "adventure", "fire-engines-trucks", 2),
    ("Frozen", "magic", "frozen", 4),
    ("Gabby's Dollhouse", "favourites", "gabbys-dollhouse", 2),
    ("Hello Kitty & Friends", "favourites", "hello-kitty-friends", 2),
    ("K-pop Demon Hunters", "favourites", "k-pop-demon-hunters", 6),
    ("Mermaid", "magic", "mermaid", 4),
    ("Mickey, Minnie & Daisy", "favourites", "mickey-minnie-daisy", 4),
    ("Paw Patrol", "favourites", "paw-patrol", 6),
    ("Peppa Pig", "favourites", "peppa-pig", 2),
    ("Pokémon", "favourites", "pokemon", 3),
    ("Princesses", "magic", "princesses", 3),
    ("Rainbow", "magic", "rainbow", 2),
    ("Spider-Man", "adventure", "spider-man", 2),
    ("Super Mario", "favourites", "super-mario", 2),
    ("Superheroes", "adventure", "superheroes", 2),
    ("Sweet Strawberries", "magic", "sweet-strawberries", 1),
    ("Tangled", "magic", "tangled", 2),
    ("Teletubbies", "favourites", "teletubbies", 1),
    ("Thomas & Friends", "adventure", "thomas-friends", 2),
    ("Toy Story", "favourites", "toy-story", 2),
    ("Unicorn", "magic", "unicorn", 2),
    ("We're Going on a Bear Hunt", "adventure", "were-going-on-a-bear-hunt", 2),
    ("Wild Animals", "adventure", "wild-animals", 2),
)

SEARCH_TERMS = {
    "Blippi & Construction": "building trucks digger",
    "Frozen": "snow ice elsa",
    "Gabby's Dollhouse": "gabby cats",
    "Hello Kitty & Friends": "sanrio my melody kuromi",
    "Mickey, Minnie & Daisy": "disney mouse",
    "Paw Patrol": "chase marshall skye",
    "Pokémon": "pokemon pikachu",
    "Spider-Man": "spiderman superhero",
    "Superheroes": "hero marvel avengers",
    "We're Going on a Bear Hunt": "bear woodland",
    "Wild Animals": "jungle safari zoo",
}


def replace_theme_catalog(apps, schema_editor):
    Theme = apps.get_model("accounts", "SouthlandShowcaseTheme")
    Photo = apps.get_model("accounts", "SouthlandShowcaseThemePhoto")

    Theme.objects.all().delete()
    for order, (name, category, folder, photo_count) in enumerate(THEMES, 1):
        theme = Theme.objects.create(
            name=name,
            category=category,
            search_terms=SEARCH_TERMS.get(name, ""),
            sort_order=order,
            description="Available in the Southland theme gallery.",
        )
        Photo.objects.bulk_create([
            Photo(
                theme=theme,
                static_path=f"package_showcase/southland/themes/{folder}/{number:02d}.jpg",
                sort_order=number,
            )
            for number in range(1, photo_count + 1)
        ])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_southlandshowcaseinvite_choices")]
    operations = [
        migrations.RunPython(replace_theme_catalog, migrations.RunPython.noop),
    ]
