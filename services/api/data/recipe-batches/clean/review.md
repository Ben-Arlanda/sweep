# Times fixed from the steps

A step said it takes longer than its stage allowed. The stage now uses the step's time.

- **Chicken Tikka Masala** (batch_01.json): 'Marinate the chicken' stage is 10 min, a step says 30 min
- **Pulled Pork Sandwiches** (batch_02.json): 'Slow braise' stage is 225 min, a step says 300 min
- **Greek Chicken Souvlaki** (batch_02.json): 'Marinate the chicken' stage is 10 min, a step says 30 min
- **Overnight Oats with Berries** (batch_02.json): 'Portion and chill' stage is 3 min, a step says 240 min
- **Creamy Coleslaw** (batch_02.json): 'Toss and chill' stage is 5 min, a step says 15 min
- **Vanilla Panna Cotta** (batch_02.json): 'Set in moulds' stage is 5 min, a step says 240 min
- **Classic Tiramisu** (batch_02.json): 'Chill and finish' stage is 5 min, a step says 360 min
- **Portuguese Piri Piri Chicken** (batch_03.json): 'Marinate chicken' stage is 10 min, a step says 30 min
- **French Chocolate Mousse** (batch_03.json): 'Fold and chill' stage is 6 min, a step says 240 min
- **New York Baked Cheesecake** (batch_03.json): 'Chill before slicing' stage is 5 min, a step says 360 min
- **Japanese Matcha Shortbread** (batch_03.json): 'Shape and chill' stage is 10 min, a step says 30 min
- **Chinese Scallion Pancakes** (batch_03.json): 'Make dough' stage is 10 min, a step says 20 min
- **Korean Beef Bulgogi** (batch_04.json): 'Make the marinade' stage is 10 min, a step says 20 min
- **Australian Bircher Muesli** (batch_04.json): 'Soak oats' stage is 5 min, a step says 240 min
- **American Key Lime Pie** (batch_07.json): 'Bake the filling' stage is 15 min, a step says 30 min
- **Turkish Sütlaç Rice Pudding** (batch_08.json): 'Cool and chill' stage is 100 min, a step says 180 min
- **Spanish Salmorejo** (batch_10.json): 'Cook the dish' stage is 25 min, a step says 60 min
- **Chinese Hong Shao Rou** (batch_10.json): 'Cook the dish' stage is 25 min, a step says 75 min
- **Lebanese Riz bi Haleeb** (batch_10.json): 'Build the flavours' stage is 12 min, a step says 25 min
- **American Lemon Bars** (batch_10.json): 'Build the flavours' stage is 12 min, a step says 18 min; 'Finish and serve' stage is 5 min, a step says 120 min
- **Chinese Liangban Huanggua** (batch_10_part_2.json): 'Toss and serve' stage is 5 min, a step says 15 min
- **Lebanese Manakish Zaatar** (batch_11_part_1.json): 'Prepare ingredients' stage is 20 min, a step says 60 min
- **Chinese Congee with Ginger Chicken** (batch_11_part_1.json): 'Build the flavours' stage is 20 min, a step says 45 min
- **French Lentil Salad with Mustard** (batch_11_part_1.json): 'Build the flavours' stage is 8 min, a step says 20 min
- **Mexican Elote Salad** (batch_11_part_1.json): 'Build the flavours' stage is 4 min, a step says 10 min
- **Spanish Arroz con Leche** (batch_11_part_1.json): 'Build the flavours' stage is 13 min, a step says 30 min

# Ingredient lines rewritten (4g step 3)

Lines no Ingredient could match, split or made specific.

- **Spaghetti Bolognese**: 'Salt and black pepper' → two lines
- **Chicken Tikka Masala**: 'Fresh coriander and cooked basmati rice, to serve' → ['Fresh coriander, to serve', 'Cooked basmati rice, to serve']
- **Classic Beef Lasagne**: 'Salt and pepper' → two lines
- **Fluffy Buttermilk Pancakes**: 'Maple syrup and berries, to serve' → ['Maple syrup, to serve', 'Berries, to serve']
- **Greek Salad**: 'Salt and freshly ground black pepper' → two lines
- **Chicken Caesar Salad**: 'Salt and pepper' → two lines
- **Mushroom Risotto**: 'Salt and black pepper' → two lines
- **Korean Kimchi Fried Rice**: '400 g cooked chilled rice' → ['400 g cooked rice, chilled']
- **American Turkey Chilli**: '200 ml stock' → ['200 ml chicken stock']
- **Brazilian Black Bean Stew**: '500 ml stock' → ['500 ml vegetable stock']
- **Italian Arancini**: '500 g cold cooked risotto' → ['500 g cooked risotto rice, cold']
- **Italian Arancini**: '100 g thick tomato sauce' → ['100 g passata, simmered until thick']
- **Vietnamese Beef Pho**: '1 litre water plus extra' → ['1 litre water, plus extra']
- **Middle Eastern Falafel Wraps**: '200 g tahini yoghurt sauce' → ['150 g Greek yoghurt, mixed with the tahini', '2 tbsp tahini']
- **Swedish Meatballs with Cream Sauce**: '500 g beef and pork mince' → ['250 g beef mince', '250 g pork mince']
- **Japanese Chicken Yakitori**: '12 bamboo skewers' → removed
- **Hungarian Chicken Paprikash**: 'salt and black pepper, to taste' → two lines
- **Turkish Mercimek Çorbası**: 'salt and black pepper, to taste' → two lines
- **Italian Arancini al Ragù**: '150 g thick cooked beef ragù' → ['150 g beef ragù, thick (leftover or from a jar)']
- **Greek Spanakorizo**: 'salt and black pepper' → two lines
- **Mexican Enfrijoladas**: '150 ml stock' → ['150 ml vegetable stock']

# Lines added because the method uses them (4g pass 2)

Salt and pepper the method seasons with, and serving suggestions as optional lines.

- **Fluffy Buttermilk Pancakes**: + Yoghurt, to serve (optional)
- **Chicken Parmesan**: + Salt
- **Beef Stroganoff**: + Salt
- **Lamb Kofta with Yoghurt**: + Salt
- **Classic Fish Tacos**: + Salt
- **Chicken Fajitas**: + Salt
- **Chickpea and Spinach Curry**: + Salt; Basmati rice, to serve (optional); Flatbread, to serve (optional)
- **Creamy Mushroom Pasta**: + Black pepper
- **Moroccan Chicken Tagine**: + Salt; Couscous, to serve (optional)
- **Chicken Noodle Soup**: + Salt
- **Spinach and Ricotta Cannelloni**: + Salt
- **Turkey Meatballs in Tomato Sauce**: + Salt
- **Lentil Shepherd's Pie**: + Salt
- **Greek Chicken Souvlaki**: + Salt
- **Crispy Tofu Rice Bowls**: + Salt
- **Tuna and White Bean Salad**: + Salt
- **Roasted Vegetable Couscous**: + Salt
- **Turkey and Avocado Wraps**: + Salt
- **Falafel Pita Pockets**: + Salt; Lettuce, to serve (optional); Tomato, to serve (optional)
- **Tomato and Red Pepper Soup**: + Salt
- **Breakfast Burritos**: + Salt
- **Banana Oat Pancakes**: + Yoghurt, to serve (optional)
- **Shakshuka with Feta**: + Salt; Crusty bread, to serve (optional)
- **Baked Oatmeal with Apple**: + Yoghurt, to serve (optional)
- **Breakfast Hash with Potatoes**: + Salt
- **Garlic Green Beans with Almonds**: + Black pepper
- **Creamy Coleslaw**: + Salt
- **Crispy Smashed Potatoes**: + Yoghurt, to serve (optional)
- **Roasted Cauliflower with Tahini**: + Salt
- **Garlic Butter Mushrooms**: + Salt; Black pepper
- **Classic Apple Crumble**: + Vanilla ice cream, to serve (optional)
- **Turkish Red Lentil Soup**: + Salt
- **Mexican Pozole Verde**: + Salt
- **French Ratatouille**: + Salt
- **Indian Palak Paneer**: + Rice, to serve (optional)
- **Greek Spanakopita**: + Salt
- **Ethiopian Misir Wot**: + Rice, to serve (optional)
- **Portuguese Piri Piri Chicken**: + Potatoes, to serve (optional)
- **American Turkey Chilli**: + Salt; Rice, to serve (optional); Yoghurt, to serve (optional)
- **Vietnamese Banh Mi Sandwich**: + Salt
- **Italian Minestrone**: + Salt
- **American Cobb Salad**: + Salt
- **Mexican Huevos Rancheros**: + Salt
- **Indian Poha with Peanuts**: + Salt
- **Korean Beef Bulgogi**: + Rice, to serve (optional); Lettuce, to serve (optional)
- **Italian Chicken Cacciatore**: + Salt; Polenta, to serve (optional); Crusty bread, to serve (optional)
- **Indian Butter Chicken**: + Rice, to serve (optional)
- **Turkish Lamb Köfte**: + Chopped tomato, to serve (optional); Cucumber, to serve (optional); Yoghurt, to serve (optional)
- **Vietnamese Beef Pho**: + Salt
- **Indian Cucumber Raita**: + Flatbread, to serve (optional)
- **Mexican Refried Beans**: + Rice, to serve (optional)
- **Turkish Ezme Salad**: + Salt; Flatbread, to serve (optional)
- **American Fluffy Banana Pancakes**: + Yoghurt, to serve (optional); Maple syrup, to serve (optional)
- **Japanese Tamagoyaki Omelette**: + Rice, to serve (optional)
- **Mexican Breakfast Chilaquiles Rojos**: + Salt
- **Italian Panzanella Salad**: + Black pepper
- **Mexican Black Bean Quesadillas**: + Salsa, to serve (optional); Yoghurt, to serve (optional); Avocado, to serve (optional)
- **French Niçoise Salad**: + Salt
- **British Apple Crumble**: + Vanilla ice cream, to serve (optional)
- **Tuscan White Bean and Kale Soup**: + Salt; Sourdough, to serve (optional)
- **Turkish Imam Bayildi**: + Salt
- **Indian Chana Masala**: + Salt; Basmati rice, to serve (optional)
- **Japanese Miso Glazed Aubergine**: + Rice, to serve (optional)
- **Greek Gigantes Plaki**: + Salt
- **Middle Eastern Fattoush Salad**: + Salt
- **Chinese Smashed Cucumber Salad**: + Salt
- **Japanese Tamagoyaki Rolled Omelette**: + Rice, to serve (optional)
- **American Breakfast Burritos**: + Salt
- **Italian Panzanella Bread Salad**: + Salt
- **Greek Spanakopita Triangles**: + Salt
- **Indian Vegetable Upma**: + Salt
- **American Macaroni Salad**: + Salt
- **Italian Lemon Ricotta Cake**: + Icing sugar, to serve (optional)
- **Egyptian Koshari**: + Salt
- **Persian Zereshk Polo with Chicken**: + Salt
- **Swedish Meatballs with Cream Sauce**: + Salt; Potatoes, to serve (optional); Jam, to serve (optional)
- **Colombian Arepas with Cheese**: + Avocado, to serve (optional); Eggs, to serve (optional)
- **Danish Æbleskiver Pancake Balls**: + Jam, to serve (optional)
- **Nepalese Aloo Tama Bamboo Shoot Curry**: + Salt; Rice, to serve (optional); Fresh coriander, to serve (optional)
- **Indian Masala Dosa**: + Salt
- **Vietnamese Pho Ga**: + Salt
- **Moroccan Harira**: + Salt; Bread, to serve (optional); Dates, to serve (optional)
- **Lebanese Fattoush**: + Salt
- **Italian Panzanella**: + Salt
- **Mexican Elote**: + Salt
- **Middle Eastern Baba Ganoush**: + Salt; Flatbread, to serve (optional)
- **Turkish Kisir**: + Salt; Lettuce, to serve (optional)
- **French Clafoutis**: + Icing sugar, to serve (optional)
- **Moroccan Zaalouk**: + Salt; Bread, to serve (optional)
- **Indian Rava Upma**: + Lemon wedges, to serve (optional)
- **Lebanese Batata Harra**: + Chilli oil, to serve (optional)
- **Italian Stracciatella Soup**: + Black pepper
- **Italian Torta Caprese**: + Icing sugar, to serve (optional)
- **French Pain Perdu**: + Icing sugar, to serve (optional)
- **Chinese Hong Shao Rou**: + Rice, to serve (optional)
- **Italian Insalata di Finocchi**: + Salt
- **Moroccan Briouats**: + Lemon wedges, to serve (optional)
- **Indian Chole Masala**: + Salt
- **French Lentil Salad with Mustard**: + Salt
- **Chinese Tomato and Egg Stir-Fry**: + Rice, to serve (optional)
- **Middle Eastern Muhammara**: + Flatbread, to serve (optional)
- **Georgian Chakhokhbili**: + Bread, to serve (optional)
- **Sri Lankan Pol Sambol**: + Rice, to serve (optional)
- **Turkish Ezogelin Soup**: + Salt
- **Ethiopian Shiro Wat**: + Salt; Flatbread, to serve (optional)
- **Filipino Ginataang Kalabasa**: + Rice, to serve (optional)
- **Greek Kolokithokeftedes**: + Salt
- **Algerian Hmiss**: + Bread, to serve (optional)

# Duplicates removed (4g step 2, approved 2026-11-19)

The richest version of each dish kept (see duplicates.json).

- Moroccan Chicken Tagine (batch_02.json)
- Pulled Pork Sandwiches (batch_02.json)
- Caprese Panini (batch_02.json)
- Overnight Oats with Berries (batch_02.json)
- Breakfast Burritos (batch_02.json)
- Shakshuka with Feta (batch_02.json)
- Classic Apple Crumble (batch_02.json)
- Turkish Red Lentil Soup (batch_03.json)
- Lebanese Mujadara (batch_03.json)
- Chinese Mapo Tofu (batch_03.json)
- Greek Spanakopita (batch_03.json)
- German Potato Salad (batch_03.json)
- Middle Eastern Fattoush (batch_03.json)
- Mexican Elote Corn (batch_03.json)
- French Dauphinoise Potatoes (batch_03.json)
- Tunisian Brik with Egg (batch_03.json)
- Greek Honey Yoghurt Parfait (batch_03.json)
- Vietnamese Fresh Spring Rolls (batch_04.json)
- French Niçoise Salad (batch_04.json)
- Turkish Lentil Köfte (Mercimek Köftesi) (batch_04.json)
- Japanese Dorayaki Pancakes (batch_04.json)
- Indian Cardamom Rice Pudding (Kheer) (batch_04.json)
- Turkish Imam Bayildi (batch_05.json)
- Spanish Garlic Prawns Gambas al Ajillo (batch_05.json)
- Japanese Miso Glazed Aubergine (batch_05.json)
- Italian Rosemary Focaccia (batch_05.json)
- French Gratin Dauphinois (batch_05.json)
- Japanese Tamagoyaki Rolled Omelette (batch_05.json)
- Vietnamese Banh Xeo Crispy Crepes (batch_05.json)
- Italian Panzanella Bread Salad (batch_05.json)
- Thai Larb Gai Chicken Salad (batch_05.json)
- Italian Caprese Stuffed Ciabatta (batch_05.json)
- Indian Vegetable Upma (batch_05.json)
- Korean Bibimbap (batch_06.json)
- Indian Masala Dosa (batch_06.json)
- Moroccan Harira (batch_06.json)
- Lebanese Fattoush (batch_06.json)
- French Quiche Lorraine (batch_06.json)
- Mexican Chilaquiles Rojos (batch_06.json)
- Indian Kheer (batch_06.json)
- Italian Panzanella (batch_06.json)
- American Macaroni and Cheese (batch_06.json)
- Japanese Tamagoyaki (batch_06.json)
- Turkish Lentil Soup Mercimek Corbasi (batch_06.json)
- Mexican Elote (batch_06.json)
- Spanish Tortilla de Patatas (batch_06.json)
- Indian Poha (batch_06.json)
- French Clafoutis (batch_06.json)
- Indian Rava Upma (batch_06.json)
- Chinese Tomato Egg Stir Fry (batch_06.json)
- Vietnamese Goi Cuon (batch_07.json)
- Turkish Mercimek Çorbası (batch_08.json)
- Italian Polenta with Mushrooms (batch_08.json)
- Brazilian Pão de Queijo (batch_08.json)
- Turkish Lentil Köfte (batch_09.json)
- American Shrimp and Grits (batch_10.json)
- French Clafoutis aux Cerises (batch_10_part_2.json)
- Indian Chole Masala (batch_11_part_1.json)
- Mexican Chicken Tinga Tostadas (batch_11_part_1.json)
- Spanish Arroz con Leche (batch_11_part_1.json)
- Chinese Tomato and Egg Stir-Fry (batch_11_part_2.json)
- Italian Affogato al Caffè (batch_11_part_2.json)
- Middle Eastern Muhammara (batch_11_part_2.json)
- Chinese Steamed Fish with Ginger (batch_11_part_2.json)
- Austrian Kaiserschmarrn (batch_11_part_2.json)
- Italian Zuppa Toscana with Kale (batch_11_part_2.json)

# Duplicates found by title (approved 2026-11-20)

- British Ploughmans Lunch
- Caribbean Jerk Chicken with Rice
- Colombian Arepas with Cheese
- German Apfelpfannkuchen
- Japanese Onigiri Rice Balls
- Japanese Sunomono Cucumber Salad
- Turkish Simit Sesame Rings
- Turkish Sütlaç Rice Pudding

# Titles

Claude's sentence-case titles, with 18 approved edits (titles.md).

# Quick View drift (judge flags, approved 2026-11-20)

- Char kway teow: quick step said dried prawns; the recipe uses fresh
- Black bean stew: two simmers (35 min, then 10 uncovered) were merged into one
- Æbleskiver: 5 minutes is per batch
- Pear Belle Hélène: the 20-minute cooling was written twice in the stages; removed the repeat; simmer added to quick steps
- 10 other flags left as they are (judge stricter than a cook: stage minutes vs step times, fine detail)
- Breakfast burritos: potatoes 12 min in the quick steps vs 18 in the stage (flagged by both judge versions)
