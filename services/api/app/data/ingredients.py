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
    SeedIngredient(
        "bread", "bakery", "count", None, False, ("loaf of bread", "sourdough", "crusty bread")
    ),
    SeedIngredient("tortillas", "bakery", "count", None, False, ("wraps",)),
    SeedIngredient("peanut butter", "pantry", "g", None, False, ()),
    SeedIngredient("honey", "pantry", "g", D("1.42"), False, ()),
    # Dairy and eggs
    SeedIngredient("milk", "dairy", "ml", D("1.03"), False, ("full cream milk", "whole milk")),
    SeedIngredient("butter", "dairy", "g", D("0.96"), False, ("unsalted butter", "salted butter")),
    SeedIngredient(
        "eggs",
        "dairy",
        "count",
        None,
        False,
        ("egg", "free range eggs", "egg whites", "egg white", "egg yolks", "egg yolk"),
    ),
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
    # Added in slice 4 so the Seed Recipes' lines have something to match.
    # Pantry: grains, pasta, noodles
    SeedIngredient("self-raising flour", "pantry", "g", D("0.53"), False, ("self raising flour",)),
    SeedIngredient("arborio rice", "pantry", "g", D("0.85"), False, ("risotto rice",)),
    SeedIngredient("couscous", "pantry", "g", D("0.7"), False, ()),
    SeedIngredient("quinoa", "pantry", "g", D("0.75"), False, ()),
    SeedIngredient("polenta", "pantry", "g", D("0.65"), False, ("cornmeal",)),
    SeedIngredient("pearl barley", "pantry", "g", D("0.8"), False, ("barley",)),
    SeedIngredient("bulgur", "pantry", "g", None, False, ("burghul", "bulgur wheat")),
    SeedIngredient("breadcrumbs", "pantry", "g", D("0.45"), False, ("dried breadcrumbs",)),
    SeedIngredient("panko breadcrumbs", "pantry", "g", None, False, ("panko",)),
    SeedIngredient("lasagne sheets", "pantry", "g", None, False, ("lasagna sheets",)),
    SeedIngredient("cannelloni tubes", "pantry", "g", None, False, ("cannelloni",)),
    SeedIngredient("egg noodles", "pantry", "g", None, False, ()),
    SeedIngredient("hokkien noodles", "pantry", "g", None, False, ()),
    SeedIngredient("rice noodles", "pantry", "g", None, False, ("rice stick noodles",)),
    SeedIngredient("rice vermicelli", "pantry", "g", None, False, ("vermicelli",)),
    SeedIngredient("udon noodles", "pantry", "g", None, False, ("udon",)),
    SeedIngredient("rice paper sheets", "pantry", "count", None, False, ("rice paper",)),
    SeedIngredient("dumpling wrappers", "chilled", "count", None, False, ("gow gee wrappers",)),
    # Pantry: cans and jars
    SeedIngredient("passata", "pantry", "g", D("1.0"), False, ("tomato passata",)),
    SeedIngredient("black beans", "pantry", "g", None, False, ()),
    SeedIngredient("kidney beans", "pantry", "g", None, False, ("red kidney beans",)),
    SeedIngredient("cannellini beans", "pantry", "g", None, False, ("white beans",)),
    SeedIngredient("brown lentils", "pantry", "g", None, False, ("canned lentils",)),
    SeedIngredient("refried beans", "pantry", "g", None, False, ()),
    SeedIngredient("corn kernels", "pantry", "g", None, False, ("canned corn", "sweetcorn")),
    SeedIngredient("creamed corn", "pantry", "g", None, False, ()),
    SeedIngredient("canned beetroot", "pantry", "g", None, False, ("sliced beetroot",)),
    SeedIngredient("canned pineapple", "pantry", "g", None, False, ("pineapple pieces",)),
    SeedIngredient("water chestnuts", "pantry", "g", None, False, ()),
    SeedIngredient("coconut cream", "pantry", "ml", D("1.0"), False, ()),
    SeedIngredient("beef stock", "pantry", "ml", D("1.0"), False, ("beef broth",)),
    SeedIngredient("vegetable stock", "pantry", "ml", D("1.0"), False, ("vegetable broth",)),
    SeedIngredient("dashi stock", "pantry", "ml", D("1.0"), False, ("dashi",)),
    SeedIngredient("kalamata olives", "pantry", "g", None, False, ("olives", "black olives")),
    SeedIngredient("tomato salsa", "pantry", "g", None, False, ("salsa",)),
    SeedIngredient("basil pesto", "pantry", "g", None, False, ("pesto",)),
    SeedIngredient("corn chips", "pantry", "g", None, False, ("tortilla chips",)),
    SeedIngredient("pickled ginger", "pantry", "g", None, False, ("sushi ginger",)),
    SeedIngredient("dried wakame", "pantry", "g", None, False, ("wakame",)),
    # Pantry: sauces, condiments, pastes
    SeedIngredient("tomato sauce", "pantry", "ml", D("1.1"), False, ("ketchup",)),
    SeedIngredient("barbecue sauce", "pantry", "ml", D("1.1"), False, ("bbq sauce",)),
    SeedIngredient("worcestershire sauce", "pantry", "ml", D("1.1"), False, ("worcestershire",)),
    SeedIngredient("mayonnaise", "pantry", "g", D("0.95"), False, ("mayo", "whole egg mayonnaise")),
    SeedIngredient("dijon mustard", "pantry", "g", None, False, ("mustard", "wholegrain mustard")),
    SeedIngredient("fish sauce", "pantry", "ml", D("1.2"), False, ()),
    SeedIngredient("oyster sauce", "pantry", "ml", D("1.2"), False, ()),
    SeedIngredient("hoisin sauce", "pantry", "ml", D("1.2"), False, ("hoisin",)),
    SeedIngredient("sweet chilli sauce", "pantry", "ml", D("1.3"), False, ("sweet chili sauce",)),
    SeedIngredient("kecap manis", "pantry", "ml", D("1.3"), False, ("sweet soy sauce",)),
    SeedIngredient("sesame oil", "pantry", "ml", D("0.92"), False, ()),
    SeedIngredient("rice vinegar", "pantry", "ml", D("1.0"), False, ()),
    SeedIngredient("red wine vinegar", "pantry", "ml", D("1.0"), False, ()),
    SeedIngredient("balsamic vinegar", "pantry", "ml", D("1.0"), False, ("balsamic",)),
    SeedIngredient("mirin", "pantry", "ml", D("1.1"), False, ()),
    SeedIngredient("gochujang", "pantry", "g", None, False, ("korean chilli paste",)),
    SeedIngredient("miso paste", "pantry", "g", None, False, ("miso", "white miso")),
    SeedIngredient("chilli bean paste", "pantry", "g", None, False, ("doubanjiang",)),
    SeedIngredient("tahini", "pantry", "g", D("0.95"), False, ()),
    SeedIngredient("tamarind paste", "pantry", "g", None, False, ("tamarind",)),
    SeedIngredient("green curry paste", "pantry", "g", None, False, ()),
    SeedIngredient("red curry paste", "pantry", "g", None, False, ()),
    SeedIngredient("madras curry paste", "pantry", "g", None, False, ("madras paste",)),
    SeedIngredient("rogan josh curry paste", "pantry", "g", None, False, ("rogan josh paste",)),
    SeedIngredient("biryani curry paste", "pantry", "g", None, False, ("biryani paste",)),
    SeedIngredient("tandoori paste", "pantry", "g", None, False, ()),
    SeedIngredient("laksa paste", "pantry", "g", None, False, ()),
    SeedIngredient("tom yum paste", "pantry", "g", None, False, ()),
    SeedIngredient("kimchi", "chilled", "g", None, False, ()),
    # Pantry: baking and sweet
    SeedIngredient("dried yeast", "pantry", "g", None, False, ("yeast", "instant yeast")),
    SeedIngredient("cocoa powder", "pantry", "g", D("0.5"), False, ("cocoa",)),
    SeedIngredient("dark chocolate", "pantry", "g", None, False, ("cooking chocolate",)),
    SeedIngredient("chocolate chips", "pantry", "g", None, False, ("choc chips",)),
    SeedIngredient("vanilla extract", "pantry", "ml", D("1.0"), False, ("vanilla",)),
    SeedIngredient("golden syrup", "pantry", "g", D("1.4"), False, ()),
    SeedIngredient("maple syrup", "pantry", "ml", D("1.32"), False, ()),
    SeedIngredient("strawberry jam", "pantry", "g", None, False, ("jam",)),
    SeedIngredient(
        "desiccated coconut", "pantry", "g", D("0.35"), False, ("shredded coconut", "coconut")
    ),
    SeedIngredient("sponge finger biscuits", "pantry", "g", None, False, ("savoiardi",)),
    SeedIngredient("granola", "pantry", "g", None, False, ()),
    SeedIngredient("coffee", "pantry", "g", None, False, ("strong coffee", "espresso")),
    # Pantry: nuts, seeds, dried fruit
    SeedIngredient("almonds", "pantry", "g", None, False, ("almond", "flaked almonds")),
    SeedIngredient("cashews", "pantry", "g", None, False, ("cashew nuts",)),
    SeedIngredient("peanuts", "pantry", "g", None, False, ("roasted peanuts",)),
    SeedIngredient("pine nuts", "pantry", "g", None, False, ()),
    SeedIngredient("walnuts", "pantry", "g", None, False, ()),
    SeedIngredient("pepitas", "pantry", "g", None, False, ("pumpkin seeds",)),
    SeedIngredient("sesame seeds", "pantry", "g", None, False, ()),
    SeedIngredient("sultanas", "pantry", "g", None, False, ("raisins",)),
    SeedIngredient("dates", "pantry", "g", None, False, ("medjool dates", "pitted dates")),
    SeedIngredient("dried apricots", "pantry", "g", None, False, ()),
    # Spices and dried herbs
    SeedIngredient("curry powder", "spices", "g", None, False, ()),
    SeedIngredient("garam masala", "spices", "g", None, False, ()),
    SeedIngredient("ground turmeric", "spices", "g", None, False, ("turmeric",)),
    SeedIngredient("chilli powder", "spices", "g", None, False, ("chili powder",)),
    SeedIngredient("cumin seeds", "spices", "g", None, False, ()),
    SeedIngredient("ground nutmeg", "spices", "g", None, False, ("nutmeg",)),
    SeedIngredient("star anise", "spices", "count", None, False, ()),
    SeedIngredient("cinnamon sticks", "spices", "count", None, False, ("cinnamon stick",)),
    SeedIngredient("ras el hanout", "spices", "g", None, False, ()),
    SeedIngredient("sumac", "spices", "g", None, False, ()),
    SeedIngredient("saffron threads", "spices", "g", None, False, ("saffron",)),
    SeedIngredient("dried chillies", "spices", "count", None, False, ("dried red chillies",)),
    SeedIngredient("bay leaves", "spices", "count", None, False, ("bay leaf",)),
    # Bakery and pastry
    SeedIngredient("baguette", "bakery", "count", None, False, ("french stick",)),
    SeedIngredient("bread rolls", "bakery", "count", None, False, ("rolls", "crusty rolls")),
    SeedIngredient("burger buns", "bakery", "count", None, False, ("hamburger buns",)),
    SeedIngredient("english muffins", "bakery", "count", None, False, ()),
    SeedIngredient("pita bread", "bakery", "count", None, False, ("pita", "lebanese bread")),
    SeedIngredient("puff pastry", "frozen", "count", None, False, ()),  # counted in sheets
    SeedIngredient("shortcrust pastry", "frozen", "count", None, False, ()),
    SeedIngredient("filo pastry", "chilled", "count", None, False, ("phyllo pastry", "filo")),
    SeedIngredient("potato gnocchi", "chilled", "g", None, False, ("gnocchi",)),
    # Dairy
    SeedIngredient("ricotta", "dairy", "g", None, False, ("ricotta cheese",)),
    SeedIngredient("cream cheese", "dairy", "g", None, False, ()),
    SeedIngredient("mascarpone", "dairy", "g", None, False, ()),
    SeedIngredient("halloumi", "dairy", "g", None, False, ("haloumi",)),
    SeedIngredient("paneer", "dairy", "g", None, False, ()),
    SeedIngredient("gruyere", "dairy", "g", None, False, ("gruyère", "swiss cheese")),
    SeedIngredient("blue cheese", "dairy", "g", None, False, ()),
    # Meat
    SeedIngredient(
        "beef chuck steak", "meat", "g", None, False, ("chuck steak", "gravy beef", "stewing beef")
    ),
    SeedIngredient("chicken drumsticks", "meat", "g", None, False, ("drumsticks",)),
    SeedIngredient("chicken wings", "meat", "g", None, False, ()),
    SeedIngredient("chicken mince", "meat", "g", None, False, ("ground chicken",)),
    SeedIngredient("whole chicken", "meat", "count", None, False, ()),
    SeedIngredient("lamb leg", "meat", "g", None, False, ("leg of lamb",)),
    SeedIngredient("lamb shoulder", "meat", "g", None, False, ()),
    SeedIngredient("lamb mince", "meat", "g", None, False, ("ground lamb",)),
    SeedIngredient("pork loin", "meat", "g", None, False, ("pork loin steaks", "pork steaks")),
    SeedIngredient("pork shoulder", "meat", "g", None, False, ("pork scotch",)),
    SeedIngredient("veal shanks", "meat", "count", None, False, ("osso buco",)),
    SeedIngredient("chorizo", "meat", "g", None, False, ()),
    SeedIngredient("ham", "meat", "g", None, False, ("sliced ham", "leg ham")),
    SeedIngredient("silken tofu", "meat", "g", None, False, ()),
    SeedIngredient("tofu puffs", "meat", "g", None, False, ()),
    # Seafood
    SeedIngredient(
        "white fish fillets", "seafood", "g", None, False, ("white fish", "fish fillets")
    ),
    SeedIngredient("cooked prawns", "seafood", "g", None, False, ()),
    # Fruit and vegetables
    SeedIngredient("pumpkin", "produce", "g", None, False, ("butternut pumpkin", "kent pumpkin")),
    SeedIngredient("cauliflower", "produce", "count", None, False, ()),
    SeedIngredient("cabbage", "produce", "count", None, False, ("green cabbage",)),
    SeedIngredient("red cabbage", "produce", "count", None, False, ("purple cabbage",)),
    SeedIngredient("wombok", "produce", "count", None, False, ("chinese cabbage", "napa cabbage")),
    SeedIngredient("bok choy", "produce", "count", None, False, ("baby bok choy", "pak choy")),
    SeedIngredient("broccolini", "produce", "count", None, False, ("baby broccoli",)),
    SeedIngredient("asparagus", "produce", "count", None, False, ()),  # counted in bunches
    SeedIngredient("celery", "produce", "count", None, False, ()),  # counted in bunches
    SeedIngredient("green beans", "produce", "g", None, False, ("string beans",)),
    SeedIngredient("snow peas", "produce", "g", None, False, ("mangetout",)),
    SeedIngredient("bean sprouts", "produce", "g", None, False, ("beansprouts",)),
    SeedIngredient("corn cobs", "produce", "count", None, False, ("corn on the cob", "corn cob")),
    SeedIngredient("radishes", "produce", "count", None, False, ("radish",)),
    # In Australia "shallots" can also mean spring onions; this is the small onion.
    SeedIngredient("shallots", "produce", "count", None, False, ("eschalots", "french shallots")),
    SeedIngredient(
        "red chillies", "produce", "count", None, False, ("red chilli", "chilli", "fresh chilli")
    ),
    SeedIngredient("lemongrass", "produce", "count", None, False, ("lemon grass",)),
    SeedIngredient(
        "kaffir lime leaves", "produce", "count", None, False, ("makrut lime leaves", "lime leaves")
    ),
    SeedIngredient("mint", "produce", "count", None, False, ("fresh mint", "mint leaves")),
    SeedIngredient("dill", "produce", "count", None, False, ("fresh dill",)),
    SeedIngredient("chives", "produce", "count", None, False, ()),
    SeedIngredient("rosemary", "produce", "count", None, False, ("fresh rosemary",)),
    SeedIngredient("thyme", "produce", "count", None, False, ("fresh thyme",)),
    SeedIngredient("sage", "produce", "count", None, False, ("fresh sage",)),
    SeedIngredient("pears", "produce", "count", None, False, ("pear",)),
    SeedIngredient("pineapple", "produce", "count", None, False, ()),
    SeedIngredient("mangoes", "produce", "count", None, False, ("mango",)),
    SeedIngredient("kiwi fruit", "produce", "count", None, False, ("kiwifruit", "kiwi")),
    SeedIngredient("passionfruit", "produce", "count", None, False, ("passion fruit",)),
    SeedIngredient("strawberries", "produce", "g", None, False, ("strawberry",)),
    SeedIngredient("blueberries", "produce", "g", None, False, ()),
    # Frozen
    SeedIngredient(
        "frozen mixed berries", "frozen", "g", None, False, ("mixed berries", "frozen berries")
    ),
    SeedIngredient("edamame", "frozen", "g", None, False, ()),
    # Drinks (for cooking)
    SeedIngredient("red wine", "drinks", "ml", D("0.99"), False, ()),
    SeedIngredient("white wine", "drinks", "ml", D("0.99"), False, ("dry white wine",)),
)
