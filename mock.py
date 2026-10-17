"""Camada do agente.

Contrato (o mesmo que um backend /chat real deve seguir):

    entrada:  message (str), preferences (dict), history (list[{"role","text"}])
    saída:    {
        "reply": str,                                  # 1-2 frases, boas para voz
        "preferences": {restrictions, goals, likes, dislikes, budget},
        "recommendations": [{"dish_id": str, "reason": str}],
        "tool_calls": [{"name": str, "args": dict, "result": dict}],
    }

Sem AGENT_API_URL, usa um agente simulado local (regras simples) só para testar a interface.
Com AGENT_API_URL, faz POST {AGENT_API_URL}/chat com esse mesmo contrato.
"""

import json
import os
import re
import unicodedata

from data import DISHES, DISH_BY_ID, RESTAURANT_BY_ID, brl


def empty_prefs() -> dict:
    return {"restrictions": [], "goals": [], "likes": [], "dislikes": [], "budget": None}


def send_message(message: str, preferences: dict, history: list) -> dict:
    api_url = os.getenv("AGENT_API_URL", "").strip()
    if api_url:
        import requests

        resp = requests.post(
            f"{api_url.rstrip('/')}/chat",
            json={"message": message, "preferences": preferences, "history": history},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    return mock_agent(message, preferences)


# ---------------------------------------------------------------------------
# Agente 
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


LIKE_WORDS = [
    "massa", "sushi", "japonesa", "hamburguer", "salada", "frango", "carne",
    "peixe", "salmao", "pizza", "bowl", "arroz", "ovo", "feijao",
]

# Sinônimos para casar o que o usuário diz com nomes/descrições dos pratos.
SYNONYMS = {
    "peixe": ["peixe", "salmao", "tilapia", "sashimi", "atum"],
    "carne": ["carne", "bife", "patinho", "burger", "hamburguer", "feijoada"],
    "massa": ["massa", "espaguete", "fettuccine", "penne", "lasanha", "yakisoba", "macarrao"],
    "japonesa": ["japonesa", "sushi", "sashimi", "temaki", "yakisoba"],
    "hamburguer": ["hamburguer", "burger"],
}

RESTRICTION_TAG = {
    "sem lactose": "sem_lactose",
    "sem glúten": "sem_gluten",
    "vegano": "vegano",
    "vegetariano": "vegetariano",
}


def _matches(haystack: str, word: str) -> bool:
    return any(w in haystack for w in SYNONYMS.get(word, [word]))


def _extract_prefs(text: str, prefs: dict):
    t = _norm(text)
    new = json.loads(json.dumps(prefs))
    changes: dict = {}

    def add(key, val):
        if val not in new[key]:
            new[key].append(val)
            changes.setdefault(key, []).append(val)

    if "lactose" in t:
        add("restrictions", "sem lactose")
    if re.search(r"gluten|celiac", t):
        add("restrictions", "sem glúten")
    if "vegan" in t:
        add("restrictions", "vegano")
    elif "vegetarian" in t:
        add("restrictions", "vegetariano")

    if re.search(r"proteic|proteina|hipertrofia|massa muscular|ganhar massa", t):
        add("goals", "alto em proteína")
    if re.search(r"low carb|baixo carbo|sem carbo|cetogen", t):
        add("goals", "low carb")
    if re.search(r"leve|emagrec|baixa caloria|pouca caloria|secar", t):
        add("goals", "leve")

    m = re.search(r"(?:ate|maximo de|r\$)\s*(?:r\$)?\s*(\d{1,3})", t)
    if m:
        new["budget"] = int(m.group(1))
        changes["budget"] = new["budget"]

    for dm in re.finditer(r"(?:nao gosto de|nao como|odeio)\s+([a-z]+)", t):
        add("dislikes", dm.group(1))

    t_likes = re.sub(r"massa muscular|ganhar massa", "", t)
    for w in LIKE_WORDS:
        if w in t_likes and w not in new["dislikes"]:
            add("likes", w)

    return new, changes


def _has_prefs(p: dict) -> bool:
    return bool(p["restrictions"] or p["goals"] or p["likes"] or p["dislikes"] or p["budget"])


def _haystack(dish: dict) -> str:
    r = RESTAURANT_BY_ID[dish["restaurant_id"]]
    return _norm(f'{dish["name"]} {dish["description"]} {r["cuisine"]}')


def _rank(prefs: dict, top_n: int = 3) -> list:
    scored = []
    for dish in DISHES:
        ok = True
        for r in prefs["restrictions"]:
            tag = RESTRICTION_TAG[r]
            if tag == "vegetariano":
                ok = ok and ("vegetariano" in dish["tags"] or "vegano" in dish["tags"])
            else:
                ok = ok and tag in dish["tags"]
        if prefs["budget"] and dish["price"] > prefs["budget"]:
            ok = False
        if any(_matches(_haystack(dish), w) for w in prefs["dislikes"]):
            ok = False
        if not ok:
            continue

        score = 0.0
        why = list(prefs["restrictions"])
        if "alto em proteína" in prefs["goals"]:
            score += dish["protein"] / 10
            if dish["protein"] >= 25:
                why.append(f'{dish["protein"]}g de proteína')
        if "low carb" in prefs["goals"]:
            score += (2 if "low_carb" in dish["tags"] else 0) - dish["carbs"] / 40
            if "low_carb" in dish["tags"]:
                why.append(f'só {dish["carbs"]}g de carboidrato')
        if "leve" in prefs["goals"]:
            score += (700 - dish["kcal"]) / 200
            if dish["kcal"] <= 500:
                why.append(f'leve, {dish["kcal"]} kcal')
        for like in prefs["likes"]:
            if _matches(_haystack(dish), like):
                score += 1.5
                why.append(f"combina com seu gosto por {like}")
        if prefs["budget"]:
            why.append(f'{brl(dish["price"])} dentro do orçamento')

        reason = ", ".join(why)
        reason = (reason[0].upper() + reason[1:]) if reason else "Opção equilibrada"
        scored.append({"dish_id": dish["id"], "score": score, "reason": reason})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def mock_agent(message: str, preferences: dict) -> dict:
    new_prefs, changes = _extract_prefs(message, preferences)
    tool_calls = []

    if changes:
        tool_calls.append({"name": "update_preferences", "args": changes, "result": {"ok": True, "preferences": new_prefs}})

    if not _has_prefs(new_prefs):
        return {
            "reply": "Oi! Sou seu assistente de nutrição. Você tem alguma restrição, algum objetivo ou um valor máximo pra gastar?",
            "preferences": new_prefs,
            "recommendations": [],
            "tool_calls": tool_calls,
        }

    top = _rank(new_prefs)
    rest_ids = list(dict.fromkeys(DISH_BY_ID[t["dish_id"]]["restaurant_id"] for t in top))

    tool_calls.append({
        "name": "search_restaurants",
        "args": {"filters": new_prefs["restrictions"], "query": " ".join(new_prefs["likes"]) or None},
        "result": {"count": len(rest_ids), "ids": rest_ids},
    })
    for rid in rest_ids:
        tool_calls.append({
            "name": "get_menu",
            "args": {"restaurant_id": rid},
            "result": {"items": sum(1 for d in DISHES if d["restaurant_id"] == rid)},
        })

    if not top:
        return {
            "reply": "Não achei pratos com esses filtros. Quer aumentar o orçamento ou flexibilizar alguma restrição?",
            "preferences": new_prefs,
            "recommendations": [],
            "tool_calls": tool_calls,
        }

    tool_calls.append({"name": "recommend", "args": {"items": [t["dish_id"] for t in top]}, "result": {"ok": True}})

    best = DISH_BY_ID[top[0]["dish_id"]]
    best_rest = RESTAURANT_BY_ID[best["restaurant_id"]]
    r0 = top[0]["reason"]
    return {
        "reply": f'Separei {len(top)} opções pra você. Minha favorita é {best["name"]}, do {best_rest["name"]}: {r0[0].lower() + r0[1:]}.',
        "preferences": new_prefs,
        "recommendations": [{"dish_id": t["dish_id"], "reason": t["reason"]} for t in top],
        "tool_calls": tool_calls,
    }
