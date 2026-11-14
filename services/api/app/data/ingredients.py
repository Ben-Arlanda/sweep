"""Starter Ingredients: common Australian groceries, AU names first, US names as aliases.

Reference data shared by every Household. Loaded by `app.seed.upsert_ingredients`, which
migrations call, so every database (dev, test, CI, later production) has the same set.
Slice 4's ingredient normalisation will grow this list.

Fields: name, category, base unit (g / ml / count), grams_per_ml (density, for converting
cups and millilitres to grams), is a default Staple, aliases.
"""

from decimal import Decimal
from typing import NamedTuple


class SeedIngredient(NamedTuple):
    name: str
    category: str
    default_unit: str
    grams_per_ml: Decimal | None = None
    is_default_staple: bool = False
    aliases: tuple[str, ...] = ()


D = Decimal

INGREDIENTS: tuple[SeedIngredient, ...] = (
    # Pantry staples: assumed present until someone marks them run out.
    SeedIngredient("salt", "pantry", "g", D("1.2"), True, ("table salt", "sea salt")),
    SeedIngredient("black pepper", "pantry", "g", None, True, ("pepper", "ground pepper")),
    SeedIngredient(
        "olive oil", "pantry", "ml", D("0.91"), True, ("extra virgin olive oil", "evoo")
    ),
    SeedIngredient("vegetable oil", "pantry", "ml", D("0.92"), True, ("canola oil", "cooking oil")),
    SeedIngredient("plain flour", "pantry", "g", D("0.53"), True, ("all-purpose flour", "flour")),
    SeedIngredient("white sugar", "pantry", "g", D("0.85"), True, ("sugar", "granulated sugar")),
    SeedIngredient("brown sugar", "pantry", "g", D("0.83"), False, ()),
    SeedIngredient("caster sugar", "pantry", "g", D("0.85"), False, ("superfine sugar",)),
    SeedIngredient("icing sugar", "pantry", "g", D("0.56"), False, ("powdered sugar",)),
    SeedIngredient(
        "bicarbonate soda", "pantry", "g", D("0.92"), True, ("bicarb soda", "baking soda")
    ),
    SeedIngredient("baking powder", "pantry", "g", D("0.9"), True, ()),
    SeedIngredient("cornflour", "pantry", "g", D("0.54"), False, ("cornstarch",)),
    SeedIngredient("soy sauce", "pantry", "ml", D("1.1"), True, ()),
    SeedIngredient("white vinegar", "pantry", "ml", D("1.0"), True, ("vinegar",)),
    SeedIngredient("garlic powder", "spices", "g", None, True, ()),
    SeedIngredient("ground cumin", "spices", "g", None, True, ("cumin",)),
    SeedIngredient("paprika", "spices", "g", None, True, ("smoked paprika",)),
    SeedIngredient("dried oregano", "spices", "g", None, True, ("oregano",)),
    SeedIngredient(
        "chilli flakes", "spices", "g", None, True, ("red pepper flakes", "chili flakes")
    ),
    SeedIngredient("ground cinnamon", "spices", "g", None, True, ("cinnamon",)),
    SeedIngredient("stock cubes", "pantry", "count", None, True, ("bouillon cubes", "stock cube")),
    # Pantry, tracked: decides whether a meal is possible.
    SeedIngredient("pasta", "pantry", "g", None, False, ("spaghetti", "penne", "fusilli")),
    SeedIngredient(
        "rice", "pantry", "g", D("0.85"), False, ("white rice", "jasmine rice", "basmati rice")
    ),
    SeedIngredient("rolled oats", "pantry", "g", D("0.41"), False, ("oats", "porridge oats")),
    SeedIngredient(
        "canned tomatoes", "pantry", "g", None, False, ("tinned tomatoes", "diced tomatoes")
    ),
    SeedIngredient("tomato paste", "pantry", "g", None, False, ("tomato puree",)),
    SeedIngredient("chickpeas", "pantry", "g", None, False, ("garbanzo beans",)),
    SeedIngredient("red lentils", "pantry", "g", None, False, ("lentils",)),
    SeedIngredient("coconut milk", "pantry", "ml", D("0.97"), False, ()),
    SeedIngredient("chicken stock", "pantry", "ml", D("1.0"), False, ("chicken broth",)),
    SeedIngredient("bread", "bakery", "count", None, False, ("loaf of bread", "sourdough")),
    SeedIngredient("tortillas", "bakery", "count", None, False, ("wraps",)),
    SeedIngredient("peanut butter", "pantry", "g", None, False, ()),
    SeedIngredient("honey", "pantry", "g", D("1.42"), False, ()),
    # Dairy and eggs
    SeedIngredient("milk", "dairy", "ml", D("1.03"), False, ("full cream milk", "whole milk")),
    SeedIngredient("butter", "dairy", "g", D("0.96"), False, ("unsalted butter", "salted butter")),
    SeedIngredient("eggs", "dairy", "count", None, False, ("egg", "free range eggs")),
    SeedIngredient(
        "cheddar cheese", "dairy", "g", None, False, ("cheddar", "tasty cheese", "cheese")
    ),
    SeedIngredient("parmesan", "dairy", "g", None, False, ("parmesan cheese", "parmigiano")),
    SeedIngredient("mozzarella", "dairy", "g", None, False, ("mozzarella cheese",)),
    SeedIngredient("feta", "dairy", "g", None, False, ("feta cheese",)),
    SeedIngredient(
        "greek yoghurt", "dairy", "g", D("1.03"), False, ("yoghurt", "yogurt", "greek yogurt")
    ),
    SeedIngredient("thickened cream", "dairy", "ml", D("1.0"), False, ("cream", "heavy cream")),
    SeedIngredient("sour cream", "dairy", "g", D("1.0"), False, ()),
    # Meat and seafood
    SeedIngredient(
        "chicken thigh", "meat", "g", None, False, ("chicken thighs", "chicken thigh fillets")
    ),
    SeedIngredient(
        "chicken breast", "meat", "g", None, False, ("chicken breasts", "chicken breast fillets")
    ),
    SeedIngredient("beef mince", "meat", "g", None, False, ("ground beef", "mince", "minced beef")),
    SeedIngredient("pork mince", "meat", "g", None, False, ("ground pork",)),
    SeedIngredient("lamb chops", "meat", "g", None, False, ("lamb cutlets",)),
    SeedIngredient(
        "beef steak", "meat", "g", None, False, ("steak", "rump steak", "scotch fillet")
    ),
    SeedIngredient("bacon", "meat", "g", None, False, ("bacon rashers", "streaky bacon")),
    SeedIngredient("sausages", "meat", "count", None, False, ("snags", "sausage")),
    SeedIngredient("salmon fillet", "seafood", "g", None, False, ("salmon", "salmon fillets")),
    SeedIngredient("prawns", "seafood", "g", None, False, ("shrimp", "king prawns")),
    SeedIngredient("canned tuna", "seafood", "g", None, False, ("tinned tuna", "tuna")),
    SeedIngredient("tofu", "meat", "g", None, False, ("firm tofu",)),
    # Fruit and vegetables
    SeedIngredient(
        "onion", "produce", "count", None, False, ("brown onion", "onions", "yellow onion")
    ),
    SeedIngredient("red onion", "produce", "count", None, False, ("spanish onion",)),
    SeedIngredient("garlic", "produce", "count", None, False, ("garlic cloves", "garlic bulb")),
    SeedIngredient("potatoes", "produce", "g", None, False, ("potato", "washed potatoes")),
    SeedIngredient("sweet potato", "produce", "g", None, False, ("kumara", "sweet potatoes")),
    SeedIngredient("carrots", "produce", "count", None, False, ("carrot",)),
    SeedIngredient("broccoli", "produce", "count", None, False, ()),
    SeedIngredient(
        "capsicum", "produce", "count", None, False, ("bell pepper", "red capsicum", "capsicums")
    ),
    SeedIngredient("zucchini", "produce", "count", None, False, ("courgette", "zucchinis")),
    SeedIngredient("eggplant", "produce", "count", None, False, ("aubergine",)),
    SeedIngredient("tomatoes", "produce", "count", None, False, ("tomato", "truss tomatoes")),
    SeedIngredient("cherry tomatoes", "produce", "g", None, False, ()),
    SeedIngredient("cucumber", "produce", "count", None, False, ("lebanese cucumber",)),
    SeedIngredient("lettuce", "produce", "count", None, False, ("cos lettuce", "iceberg lettuce")),
    SeedIngredient("baby spinach", "produce", "g", None, False, ("spinach",)),
    SeedIngredient("rocket", "produce", "g", None, False, ("arugula",)),
    SeedIngredient("mushrooms", "produce", "g", None, False, ("mushroom", "button mushrooms")),
    SeedIngredient("spring onions", "produce", "count", None, False, ("scallions", "green onions")),
    SeedIngredient("coriander", "produce", "count", None, False, ("cilantro", "fresh coriander")),
    SeedIngredient("parsley", "produce", "count", None, False, ("flat leaf parsley",)),
    SeedIngredient("basil", "produce", "count", None, False, ("fresh basil",)),
    SeedIngredient("ginger", "produce", "g", None, False, ("fresh ginger",)),
    SeedIngredient("lemons", "produce", "count", None, False, ("lemon",)),
    SeedIngredient("limes", "produce", "count", None, False, ("lime",)),
    SeedIngredient("avocado", "produce", "count", None, False, ("avocados",)),
    SeedIngredient("bananas", "produce", "count", None, False, ("banana",)),
    SeedIngredient("apples", "produce", "count", None, False, ("apple",)),
    SeedIngredient("frozen peas", "frozen", "g", None, False, ("peas",)),
)
