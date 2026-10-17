"""Dados simulados do "iFood". Troque por chamadas à API real quando estiver liberada."""

RESTAURANTS = [
    {"id": "r1", "name": "Verde Bowl", "cuisine": "Saudável", "emoji": "🥗", "rating": 4.8, "eta": "25-35 min", "fee": 4.9, "color": "#2e9e5b"},
    {"id": "r2", "name": "Sakura Sushi", "cuisine": "Japonesa", "emoji": "🍣", "rating": 4.7, "eta": "35-45 min", "fee": 6.9, "color": "#e0527a"},
    {"id": "r3", "name": "Grelha Fit", "cuisine": "Fitness", "emoji": "🍗", "rating": 4.6, "eta": "30-40 min", "fee": 3.9, "color": "#e8863a"},
    {"id": "r4", "name": "Pasta & Cia", "cuisine": "Italiana", "emoji": "🍝", "rating": 4.5, "eta": "40-50 min", "fee": 5.9, "color": "#c8453a"},
    {"id": "r5", "name": "Burger Lab", "cuisine": "Hambúrguer", "emoji": "🍔", "rating": 4.4, "eta": "25-35 min", "fee": 0.0, "color": "#a9642b"},
    {"id": "r6", "name": "Raízes Veganas", "cuisine": "Vegana", "emoji": "🌱", "rating": 4.7, "eta": "30-40 min", "fee": 4.5, "color": "#5a9e3a"},
    {"id": "r7", "name": "Casa do Feijão", "cuisine": "Brasileira", "emoji": "🍛", "rating": 4.6, "eta": "30-45 min", "fee": 3.5, "color": "#8a5a2b"},
    {"id": "r8", "name": "Pizza Forno", "cuisine": "Pizza", "emoji": "🍕", "rating": 4.3, "eta": "35-50 min", "fee": 5.0, "color": "#d9534f"},
]


def _d(id, rid, name, description, price, kcal, protein, carbs, fat, tags, emoji):
    return {
        "id": id, "restaurant_id": rid, "name": name, "description": description,
        "price": price, "kcal": kcal, "protein": protein, "carbs": carbs, "fat": fat,
        "tags": tags, "emoji": emoji,
    }


DISHES = [
    # Verde Bowl
    _d("d1", "r1", "Bowl de frango e quinoa", "Frango grelhado, quinoa, folhas, tomate-cereja e molho de ervas.", 34.9, 480, 38, 42, 12, ["sem_lactose", "high_protein"], "🥗"),
    _d("d2", "r1", "Caesar fit com frango", "Alface-americana, frango, parmesão e molho leve de iogurte.", 29.9, 390, 32, 14, 20, ["high_protein", "low_carb"], "🥬"),
    _d("d3", "r1", "Bowl de grão-de-bico e legumes", "Grão-de-bico, legumes assados, tahine e folhas verdes.", 31.9, 430, 16, 55, 14, ["vegano", "vegetariano", "sem_lactose"], "🥙"),
    # Sakura Sushi
    _d("d4", "r2", "Combo salmão 12 peças", "Sushis e hossomakis de salmão fresco.", 52.9, 560, 34, 70, 14, ["sem_lactose", "high_protein"], "🍣"),
    _d("d5", "r2", "Sashimi de salmão (10 fatias)", "Fatias de salmão fresco, acompanha shoyu e gengibre.", 44.9, 320, 36, 2, 18, ["sem_lactose", "sem_gluten", "low_carb", "high_protein"], "🐟"),
    _d("d6", "r2", "Temaki de pepino e cream cheese", "Cone de alga com arroz, pepino e cream cheese.", 24.9, 290, 8, 40, 9, ["vegetariano"], "🍙"),
    _d("d7", "r2", "Yakisoba de legumes", "Macarrão oriental salteado com legumes e shoyu.", 33.9, 520, 14, 78, 15, ["vegano", "vegetariano", "sem_lactose"], "🍜"),
    # Grelha Fit
    _d("d8", "r3", "Frango grelhado com batata-doce", "Filé de frango grelhado, batata-doce e brócolis.", 32.9, 520, 45, 48, 10, ["sem_lactose", "sem_gluten", "high_protein"], "🍗"),
    _d("d9", "r3", "Omelete de claras com espinafre", "Claras, espinafre e tomate, sem queijo.", 22.9, 280, 28, 6, 14, ["vegetariano", "sem_lactose", "sem_gluten", "low_carb", "high_protein"], "🍳"),
    _d("d10", "r3", "Tilápia grelhada com legumes", "Filé de tilápia com mix de legumes no vapor.", 36.9, 410, 40, 20, 14, ["sem_lactose", "sem_gluten", "low_carb", "high_protein"], "🐠"),
    _d("d11", "r3", "Patinho moído com purê de mandioca", "Carne magra moída e purê cremoso de mandioca.", 30.9, 590, 42, 55, 20, ["sem_lactose", "sem_gluten", "high_protein"], "🥩"),
    # Pasta & Cia
    _d("d12", "r4", "Fettuccine alfredo", "Massa fresca com molho cremoso de queijo.", 42.9, 780, 22, 85, 38, ["vegetariano"], "🍝"),
    _d("d13", "r4", "Espaguete ao sugo com manjericão", "Molho de tomate fresco, manjericão e azeite.", 34.9, 560, 16, 92, 12, ["vegano", "vegetariano", "sem_lactose"], "🍅"),
    _d("d14", "r4", "Penne integral com frango e brócolis", "Massa integral, frango desfiado e brócolis.", 38.9, 610, 38, 70, 18, ["sem_lactose", "high_protein"], "🍝"),
    _d("d15", "r4", "Lasanha bolonhesa", "Camadas de massa, molho de carne e queijo gratinado.", 41.9, 850, 36, 80, 42, [], "🧀"),
    # Burger Lab
    _d("d16", "r5", "Cheeseburger duplo", "Dois burgers, cheddar, picles e molho da casa.", 39.9, 920, 48, 52, 55, ["high_protein"], "🍔"),
    _d("d17", "r5", "Burger de frango sem pão", "Hambúrguer de frango grelhado servido sobre alface.", 33.9, 420, 40, 8, 22, ["sem_lactose", "sem_gluten", "low_carb", "high_protein"], "🥬"),
    _d("d18", "r5", "Burger de grão-de-bico vegano", "Burger vegetal no pão integral, com tomate e rúcula.", 35.9, 540, 18, 62, 22, ["vegano", "vegetariano", "sem_lactose"], "🌱"),
    # Raízes Veganas
    _d("d19", "r6", "Moqueca de palmito", "Palmito pupunha no leite de coco, com arroz de couve-flor.", 37.9, 450, 9, 48, 22, ["vegano", "vegetariano", "sem_lactose", "sem_gluten"], "🥥"),
    _d("d20", "r6", "Poke vegano de tofu", "Tofu marinado, edamame, manga, pepino e arroz.", 33.9, 410, 22, 48, 14, ["vegano", "vegetariano", "sem_lactose"], "🥢"),
    _d("d21", "r6", "Wrap de falafel", "Falafel assado, homus, folhas e picles de cebola roxa.", 28.9, 480, 15, 58, 20, ["vegano", "vegetariano", "sem_lactose"], "🌯"),
    # Casa do Feijão
    _d("d22", "r7", "PF bife acebolado", "Arroz, feijão, bife acebolado e salada.", 29.9, 720, 38, 85, 24, ["sem_lactose", "sem_gluten", "high_protein"], "🍛"),
    _d("d23", "r7", "Feijoada light individual", "Feijoada com cortes magros, couve e laranja.", 39.9, 640, 36, 52, 28, ["sem_lactose", "sem_gluten"], "🫘"),
    _d("d24", "r7", "Salada de lentilha com ovo", "Lentilha, ovo cozido, tomate e cebola roxa.", 24.9, 380, 20, 38, 14, ["vegetariano", "sem_lactose", "sem_gluten"], "🥗"),
    # Pizza Forno
    _d("d25", "r8", "Pizza margherita individual", "Molho de tomate, muçarela e manjericão.", 36.9, 780, 28, 96, 28, ["vegetariano"], "🍕"),
    _d("d26", "r8", "Pizza vegana de legumes", "Massa fina, molho de tomate e legumes grelhados, sem queijo.", 39.9, 650, 18, 90, 20, ["vegano", "vegetariano", "sem_lactose"], "🍕"),
]

TAG_LABELS = {
    "vegano": "vegano",
    "vegetariano": "vegetariano",
    "sem_lactose": "sem lactose",
    "sem_gluten": "sem glúten",
    "low_carb": "low carb",
    "high_protein": "alto em proteína",
}

RESTAURANT_BY_ID = {r["id"]: r for r in RESTAURANTS}
DISH_BY_ID = {d["id"]: d for d in DISHES}


def brl(value: float) -> str:
    return f"R$ {value:.2f}".replace(".", ",")
