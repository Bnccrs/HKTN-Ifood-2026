"""Simulador iFood + Agente Nutri (Streamlit).

Rodar:  streamlit run app.py
"""

import hashlib
import html
import json
from datetime import datetime

import streamlit as st

try:  # carrega .env se python-dotenv estiver instalado
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agent.mock import empty_prefs, send_message
from data import DISHES, DISH_BY_ID, RESTAURANT_BY_ID, RESTAURANTS, TAG_LABELS, brl
from voice import TranscriptionError, synthesize, transcribe

st.set_page_config(page_title="Agente Ifit · Simulador iFood", page_icon="🍽️", layout="wide")

CSS = """
<style>
.topbar { background:#ea1d2c; color:#fff; padding:10px 18px; border-radius:12px; margin-bottom:12px;
          display:flex; align-items:baseline; gap:12px; }
.topbar .logo { font-weight:800; font-size:26px; font-style:italic; letter-spacing:-1px; }
.topbar .sub { font-size:13px; opacity:.9; }
.card { border:1px solid #e8e4e2; border-radius:12px; background:#fff; overflow:hidden; margin-top:4px; }
.card.rec { border:2px solid #ea1d2c; box-shadow:0 6px 18px #ea1d2c22; }
.card .badge { background:#ea1d2c; color:#fff; font-size:11px; font-weight:700; padding:4px 10px; }
.card .art { height:70px; display:flex; align-items:center; justify-content:center; font-size:38px; }
.card .body { padding:8px 12px 10px; }
.card h4 { margin:0 0 2px; font-size:15px; }
.card .meta { color:#7a7573; font-size:12px; }
.card .desc { color:#7a7573; font-size:12px; margin:4px 0 6px; line-height:1.35; }
.chips { display:flex; flex-wrap:wrap; gap:4px; margin-bottom:4px; }
.chip { font-size:11px; background:#f5f3f2; border-radius:6px; padding:2px 6px; }
.tag { font-size:11px; border-radius:999px; padding:2px 8px; background:#eef6f0; color:#226b3d; }
.tag.warn { background:#fdf3e2; color:#b7791f; }
.tag.ok { background:#e8f3fb; color:#1d6fa5; }
.tag.bad { background:#fde8e8; color:#c4131f; }
.reason { font-size:12px; background:#fff4f4; color:#c4131f; border-radius:8px; padding:6px 8px; margin-top:4px; }
.price { font-weight:700; margin-top:6px; }
.pref-label { font-size:11px; text-transform:uppercase; letter-spacing:.04em; color:#7a7573; margin:8px 0 4px; }
</style>
"""

WELCOME = {
    "role": "agent",
    "text": "Oi! Me conta o que você quer comer, suas restrições e quanto quer gastar. Pode falar ou digitar.",
}

SUGGESTIONS = [
    "Sou intolerante a lactose, quero algo leve e proteico até R$ 40",
    "Sou vegano e quero algo com bastante proteína",
    "Quero comer low carb, gosto de peixe",
]


# ----------------------------------------------------------------------------
# Estado
# ----------------------------------------------------------------------------

def init_state():
    ss = st.session_state
    ss.setdefault("messages", [WELCOME])
    ss.setdefault("prefs", empty_prefs())
    ss.setdefault("recs", [])
    ss.setdefault("tool_log", [])
    ss.setdefault("cart", [])
    ss.setdefault("last_audio_hash", None)
    ss.setdefault("audio_n", 0)
    ss.setdefault("tts_on", True)


def reset_demo():
    ss = st.session_state
    ss.messages = [WELCOME]
    ss.prefs = empty_prefs()
    ss.recs = []
    ss.tool_log = []
    ss.cart = []
    ss.last_audio_hash = None
    ss.audio_n += 1  # recria o widget de áudio (limpa a gravação)


def add_to_cart(dish_id: str):
    st.session_state.cart.append(dish_id)


def run_turn(text: str, via: str) -> str:
    """Manda a fala/texto para o agente e atualiza o estado. Devolve a resposta."""
    ss = st.session_state
    ss.messages.append({"role": "user", "text": text, "via": via})
    history = [{"role": m["role"], "text": m["text"]} for m in ss.messages]
    try:
        res = send_message(text, ss.prefs, history)
    except Exception as exc:  # backend fora do ar, etc.
        reply = f"Tive um problema para falar com o agente ({exc}). Tenta de novo?"
        ss.messages.append({"role": "agent", "text": reply})
        return reply

    ss.prefs = res.get("preferences", ss.prefs)
    if isinstance(res.get("recommendations"), list):
        ss.recs = res["recommendations"]
    now = datetime.now().strftime("%H:%M:%S")
    for call in res.get("tool_calls", []):
        ss.tool_log.append({**call, "at": now})
    ss.messages.append({"role": "agent", "text": res["reply"]})
    return res["reply"]


# ----------------------------------------------------------------------------
# Renderização
# ----------------------------------------------------------------------------

def card_html(dish: dict, reason: str | None = None, rank: int | None = None) -> str:
    rest = RESTAURANT_BY_ID[dish["restaurant_id"]]
    e = html.escape
    badge = f'<div class="badge">⭐ Indicado pelo agente · #{rank}</div>' if reason else ""
    macros = "".join(
        f'<span class="chip">{v}</span>'
        for v in (f'{dish["kcal"]} kcal', f'{dish["protein"]}g prot', f'{dish["carbs"]}g carb', f'{dish["fat"]}g gord')
    )
    tags = "".join(f'<span class="tag">{e(TAG_LABELS[t])}</span>' for t in dish["tags"])
    reason_html = f'<div class="reason">💬 {e(reason)}</div>' if reason else ""
    return f"""
    <div class="card {'rec' if reason else ''}">
      {badge}
      <div class="art" style="background:linear-gradient(135deg,{rest['color']}22,{rest['color']}55)">{dish['emoji']}</div>
      <div class="body">
        <h4>{e(dish['name'])}</h4>
        <div class="meta">{e(rest['name'])} · ⭐ {rest['rating']} · {e(rest['eta'])}</div>
        <div class="desc">{e(dish['description'])}</div>
        <div class="chips">{macros}</div>
        <div class="chips">{tags}</div>
        {reason_html}
        <div class="price">{brl(dish['price'])}</div>
      </div>
    </div>
    """


def render_cards(items, prefix: str, per_row: int = 3):
    """items: lista de (dish, reason, rank)."""
    for start in range(0, len(items), per_row):
        cols = st.columns(per_row)
        for col, (dish, reason, rank) in zip(cols, items[start:start + per_row]):
            with col:
                st.markdown(card_html(dish, reason, rank), unsafe_allow_html=True)
                st.button(
                    f"Adicionar · {brl(dish['price'])}",
                    key=f"{prefix}_{dish['id']}",
                    on_click=add_to_cart,
                    args=(dish["id"],),
                    use_container_width=True,
                )


def render_prefs(prefs: dict):
    groups = [
        ("restrictions", "Restrições", "warn"),
        ("goals", "Objetivos", "ok"),
        ("likes", "Gostos", ""),
        ("dislikes", "Não gosta", "bad"),
    ]
    if not prefs["budget"] and not any(prefs[k] for k, _, _ in groups):
        st.caption("O agente ainda não aprendeu nada sobre você. Fale ou digite suas preferências.")
        return
    out = []
    for key, label, cls in groups:
        if prefs[key]:
            pills = "".join(f'<span class="tag {cls}">{html.escape(v)}</span> ' for v in prefs[key])
            out.append(f'<div class="pref-label">{label}</div><div class="chips">{pills}</div>')
    if prefs["budget"]:
        out.append(f'<div class="pref-label">Orçamento máximo</div><span class="tag">R$ {prefs["budget"]}</span>')
    st.markdown("".join(out), unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------

init_state()
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="topbar"><span class="logo">ifood</span>'
    '<span class="sub">simulador · Agente Nutri</span></div>',
    unsafe_allow_html=True,
)

left, right = st.columns([5, 7], gap="large")

# --- Coluna do agente: a conversa é desenhada depois (precisa do estado atualizado)
with left:
    st.subheader("Agente")
    chat_box = st.container(height=420)

    suggestion = None
    if len(st.session_state.messages) <= 1:
        for s in SUGGESTIONS:
            if st.button(s, key=f"sug_{s}", use_container_width=True):
                suggestion = s

    audio = st.audio_input(
        "🎙 Clique para gravar, fale e clique de novo para parar",
        sample_rate=16000,
        key=f"audio_{st.session_state.audio_n}",
    )
    status_box = st.empty()

typed = st.chat_input("Ou digite aqui...")

# --- Descobre o que o usuário disse neste ciclo (sugestão > texto > voz)
user_text, via = None, "texto"
if suggestion:
    user_text = suggestion
elif typed:
    user_text = typed
elif audio is not None:
    data = audio.getvalue()
    audio_hash = hashlib.md5(data).hexdigest()
    if audio_hash != st.session_state.last_audio_hash:  # evita reprocessar a mesma gravação
        st.session_state.last_audio_hash = audio_hash
        try:
            with left, st.spinner("Transcrevendo..."):
                transcript = transcribe(data)
        except TranscriptionError as exc:
            status_box.error(f"Não consegui transcrever: {exc}")
        else:
            if transcript:
                user_text, via = transcript, "voz"
            else:
                status_box.warning("Não entendi o áudio. Tenta falar de novo?")

# --- Processa a rodada
reply_audio = None
if user_text:
    with left, st.spinner("Pensando..."):
        reply = run_turn(user_text, via)
    if st.session_state.tts_on:
        reply_audio = synthesize(reply)

# --- Desenha a conversa com o estado já atualizado
with chat_box:
    for m in st.session_state.messages:
        if m["role"] == "user":
            with st.chat_message("user"):
                st.write(("🎙 " if m.get("via") == "voz" else "") + m["text"])
        else:
            with st.chat_message("assistant"):
                st.write(m["text"])

if reply_audio:
    with left:
        st.audio(reply_audio, format="audio/mp3", autoplay=True)

# --- Vitrine
with right:
    recs = [
        (DISH_BY_ID[r["dish_id"]], r["reason"], i + 1)
        for i, r in enumerate(st.session_state.recs)
        if r["dish_id"] in DISH_BY_ID
    ]
    if recs:
        st.subheader("⭐ Recomendados para você")
        render_cards(recs, "rec")

    st.subheader("Restaurantes")
    options = ["Todos"] + [f'{r["emoji"]} {r["name"]}' for r in RESTAURANTS]
    choice = st.radio("Filtrar por restaurante", options, horizontal=True, label_visibility="collapsed")
    selected = None if choice == "Todos" else RESTAURANTS[options.index(choice) - 1]
    if selected:
        st.caption(
            f'{selected["cuisine"]} · ⭐ {selected["rating"]} · {selected["eta"]} · '
            f'entrega {"grátis" if selected["fee"] == 0 else brl(selected["fee"])}'
        )

    rec_ids = {d["id"] for d, _, _ in recs}
    menu = [
        (d, None, None)
        for d in DISHES
        if d["id"] not in rec_ids and (selected is None or d["restaurant_id"] == selected["id"])
    ]
    st.subheader(selected["name"] if selected else "Cardápio completo")
    render_cards(menu, "menu")

# --- Barra lateral: perfil, carrinho, log
with st.sidebar:
    st.header("Perfil do usuário")
    render_prefs(st.session_state.prefs)

    st.divider()
    cart = [DISH_BY_ID[i] for i in st.session_state.cart]
    st.metric("🛍 Carrinho simulado", f"{len(cart)} itens", brl(sum(d["price"] for d in cart)), delta_color="off")

    st.divider()
    st.toggle("Voz do agente (TTS)", key="tts_on")
    st.button("Reiniciar demo", on_click=reset_demo, use_container_width=True)

    st.divider()
    log = st.session_state.tool_log
    with st.expander(f"Log de tool calls ({len(log)})", expanded=bool(log)):
        if not log:
            st.caption("Nenhuma chamada ainda.")
        for entry in reversed(log):  # mais recentes primeiro
            st.markdown(f"**`{entry['name']}`** · {entry['at']}")
            st.code(
                json.dumps({"args": entry["args"], "result": entry["result"]}, ensure_ascii=False, indent=1),
                language="json",
            )
