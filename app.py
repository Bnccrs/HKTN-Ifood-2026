"""Simulador iFood + Agente Nutri (Streamlit).

Rodar:  streamlit run app.py
"""

import hashlib
import html
import json
import re
from datetime import datetime

import streamlit as st

try:  # carrega .env se python-dotenv estiver instalado
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agent.mock import empty_prefs, send_message
from data import DISH_BY_ID, RESTAURANT_BY_ID, brl
from voice import TranscriptionError, synthesize, transcribe

st.set_page_config(page_title="Agente iFit · Simulador iFood", page_icon="🍽️", layout="wide")

CSS = """
<style>
/* página fixa: sem rolagem (só o chat e a barra lateral rolam por dentro) */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stAppScrollToBottomContainer"] { overflow:hidden !important; }
/* o cabeçalho guarda o botão de reabrir a barra lateral: fica transparente, sem menu e deploy */
header[data-testid="stHeader"] { background:transparent; pointer-events:none; }
[data-testid="stExpandSidebarButton"] { pointer-events:auto; }
[data-testid="stExpandSidebarButton"] span { color:#1e8f4e !important; }
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"] { display:none; }
.block-container { padding-top:1rem; padding-bottom:4.5rem; }
/* chat ocupa a altura que sobra na tela (o Streamlit fixa a altura no wrapper do container) */
[data-testid="stLayoutWrapper"]:has(> .st-key-chat) { flex-basis:max(240px, calc(100vh - 400px)) !important;
  height:max(240px, calc(100vh - 400px)) !important; }
.st-key-chat { height:100% !important; }
[data-testid="stAudio"] { display:none; }  /* resposta em voz toca sem ocupar espaço */
.topbar { background:linear-gradient(90deg,#1e8f4e,#43b36a); color:#fff; padding:6px 16px; border-radius:10px; margin-bottom:8px;
          display:flex; align-items:baseline; gap:12px; }
.topbar .logo { font-weight:800; font-size:22px; font-style:italic; letter-spacing:-1px; }
.topbar .sub { font-size:13px; opacity:.9; }
.empty { border:2px dashed #cfe5d6; border-radius:12px; color:#5f7a68; background:#f5fbf7; text-align:center;
         padding:120px 24px; font-size:15px; }
.card { display:flex; gap:10px; height:128px; border:1px solid #d6eadc; border-radius:12px; background:#fff; color:#1c2b22;
        overflow:hidden; }
.card.rec { border:2px solid #1e8f4e; }
.card .art { flex:0 0 104px; display:flex; align-items:center; justify-content:center; font-size:38px; overflow:hidden; }
.card .art img { width:100%; height:100%; object-fit:cover; }
.card .body { padding:8px 10px 8px 0; min-width:0; display:flex; flex-direction:column; gap:3px; }
.card h4 { margin:0; padding:0; color:#1c2b22; font-weight:700; font-size:14px; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.card .rank { color:#1e8f4e; font-weight:800; margin-right:4px; }
.card .meta { color:#4f5d54; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.card .macros { font-size:12px; font-weight:600; color:#3d3a39; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.chips { display:flex; flex-wrap:wrap; gap:4px; }
.tag { font-size:11px; border-radius:999px; padding:2px 8px; background:#eef6f0; color:#226b3d; }
.tag.warn { background:#fdf3e2; color:#b7791f; }
.tag.ok { background:#e8f3fb; color:#1d6fa5; }
.tag.bad { background:#fde8e8; color:#c4131f; }
.reason { font-size:12px; color:#1b6e40; line-height:1.3; display:-webkit-box; -webkit-line-clamp:3;
          -webkit-box-orient:vertical; overflow:hidden; }
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
    ss.setdefault("session_id", None)
    ss.setdefault("live_menu", [])     # pratos reais do iFood vindos da última busca do Gemini
    ss.setdefault("ifood_cart", None)  # carrinho real do iFood, montado pelo Gemini via MCP
    ss.setdefault("pending_text", None)  # mensagem gerada por um botão "Adicionar" do cardápio real


def reset_demo():
    ss = st.session_state
    ss.messages = [WELCOME]
    ss.prefs = empty_prefs()
    ss.recs = []
    ss.tool_log = []
    ss.cart = []
    ss.last_audio_hash = None
    ss.session_id = None  # nova conversa no agente
    ss.live_menu = []
    ss.ifood_cart = None
    ss.pending_text = None
    ss.audio_n += 1  # recria o widget de áudio (limpa a gravação)


def add_to_cart(dish_id: str):
    st.session_state.cart.append(dish_id)


def use_suggestion(text: str):
    st.session_state.pending_text = text


def confirm_add_to_ifood_cart(rank: int, item: dict):
    """O clique em "Adicionar" num prato real é a confirmação: o Gemini adiciona via MCP."""
    st.session_state.pending_text = (
        f'Confirmo: quero adicionar a opção {rank} ao carrinho: {item["name"]} — {item["restaurant"]} '
        f'(itemId {item["id"]}, merchantId {item["merchant_id"]}). Pode adicionar.'
    )


def run_turn(text: str, via: str) -> str:
    """Manda a fala/texto para o agente e atualiza o estado. Devolve a resposta."""
    ss = st.session_state
    ss.messages.append({"role": "user", "text": text, "via": via})
    history = [{"role": m["role"], "text": m["text"]} for m in ss.messages]
    try:
        res = send_message(text, ss.prefs, history, ss.session_id)
    except Exception as exc:  # backend fora do ar, etc.
        reply = f"Tive um problema para falar com o agente ({exc}). Tenta de novo?"
        ss.messages.append({"role": "agent", "text": reply})
        return reply

    ss.prefs = res.get("preferences", ss.prefs)
    ss.session_id = res.get("session_id", ss.session_id)
    if isinstance(res.get("recommendations"), list):
        ss.recs = res["recommendations"]
    if isinstance(res.get("menu"), list):
        ss.live_menu = res["menu"]
    if res.get("cart"):
        ss.ifood_cart = res["cart"]
    now = datetime.now().strftime("%H:%M:%S")
    for call in res.get("tool_calls", []):
        ss.tool_log.append({**call, "at": now})
    ss.messages.append({"role": "agent", "text": res["reply"]})
    return res["reply"]


def speakable(text: str, limit: int = 400) -> str:
    """Tira o markdown da resposta (o Gemini responde formatado) e encurta para a voz."""
    plain = re.sub(r"[*_#>`|]+|^\s*[-–]\s+|---+", "", text, flags=re.M)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain if len(plain) <= limit else plain[:limit].rsplit(" ", 1)[0] + "…"


# ----------------------------------------------------------------------------
# Renderização
# ----------------------------------------------------------------------------

LIVE_COLORS = ["#2e9e5b", "#e0527a", "#e8863a", "#c8453a", "#a9642b", "#5a9e3a", "#8a5a2b", "#d9534f"]


def live_dish(item: dict) -> dict:
    """Converte um prato real (agent.gemini_cli) para o formato dos cards do catálogo simulado."""
    color = LIVE_COLORS[int(hashlib.md5(item["restaurant"].encode()).hexdigest(), 16) % len(LIVE_COLORS)]
    return {
        **item,
        "emoji": "🍽️",
        "restaurant_info": {"name": item["restaurant"], "rating": None, "eta": item["eta"], "color": color},
    }


def card_html(dish: dict, reason: str | None = None, rank: int | None = None) -> str:
    rest = dish.get("restaurant_info") or RESTAURANT_BY_ID[dish["restaurant_id"]]
    e = html.escape
    macros = " · ".join(
        f"{value:g}{unit}"
        for value, unit in ((dish["kcal"], " kcal"), (dish["protein"], "g prot"), (dish["carbs"], "g carb"), (dish["fat"], "g gord"))
        if value is not None
    )
    image = dish.get("image_url") or ""
    art = f'<img src="{e(image)}" alt="">' if image.startswith(("https://", "http://")) else dish["emoji"]
    meta = " · ".join(p for p in (e(rest["name"]), f'⭐ {rest["rating"]}' if rest["rating"] else "", e(rest["eta"])) if p)
    rank_html = f'<span class="rank">#{rank}</span>' if rank else ""
    reason_html = f'<div class="reason">💬 {e(reason)}</div>' if reason else ""
    return f"""
    <div class="card {'rec' if rank == 1 else ''}">
      <div class="art" style="background:linear-gradient(135deg,{rest['color']}22,{rest['color']}55)">{art}</div>
      <div class="body">
        <h4 title="{e(dish['name'])}">{rank_html}{e(dish['name'])}</h4>
        <div class="meta">{meta}</div>
        <div class="macros">{macros}</div>
        {reason_html}
      </div>
    </div>
    """


def render_cards(items, prefix: str, per_row: int = 2, live: bool = False):
    """items: lista de (dish, reason, rank). live=True: pratos reais, adicionados pelo agente no iFood."""
    for start in range(0, len(items), per_row):
        cols = st.columns(per_row)
        for n, (col, (dish, reason, rank)) in enumerate(zip(cols, items[start:start + per_row]), start):
            with col:
                st.markdown(card_html(dish, reason, rank), unsafe_allow_html=True)
                st.button(
                    f"Adicionar · {brl(dish['price'])}",
                    key=f"{prefix}_{n}_{dish['id']}",
                    on_click=confirm_add_to_ifood_cart if live else add_to_cart,
                    args=(rank, dish) if live else (dish["id"],),
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
        return
    out = ['<div class="pref-label">Seu perfil</div>']
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
    '<div class="topbar"><span class="logo">iFit</span>'
    '<span class="sub">simulador · Agente Nutri</span></div>',
    unsafe_allow_html=True,
)

left, right = st.columns([5, 7], gap="medium")

# --- Coluna do agente: a conversa é desenhada depois (precisa do estado atualizado)
with left:
    chat_box = st.container(height=380, key="chat", autoscroll=True)
    with chat_box:
        history_area = st.container()
        suggestions_area = st.container()

    audio = st.audio_input(
        "Gravar mensagem de voz",
        sample_rate=16000,
        key=f"audio_{st.session_state.audio_n}",
        label_visibility="collapsed",
    )
    status_box = st.empty()

typed = st.chat_input("Digite o que você quer comer...")

# --- Descobre o que o usuário disse neste ciclo (sugestão/botão > texto > voz)
user_text, via = None, "texto"
if st.session_state.pending_text:  # sugestão ou botão "Adicionar"
    user_text, st.session_state.pending_text = st.session_state.pending_text, None
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
        reply_audio = synthesize(speakable(reply))

# --- Desenha a conversa com o estado já atualizado
with history_area:
    for m in st.session_state.messages:
        if m["role"] == "user":
            with st.chat_message("user"):
                st.write(("🎙 " if m.get("via") == "voz" else "") + m["text"])
        else:
            with st.chat_message("assistant"):
                st.write(m["text"])

if len(st.session_state.messages) <= 1:
    with suggestions_area:
        for s in SUGGESTIONS:
            st.button(s, key=f"sug_{s}", on_click=use_suggestion, args=(s,), use_container_width=True)

if reply_audio:
    with left:
        st.audio(reply_audio, format="audio/mp3", autoplay=True)

# --- Vitrine: só mostra pratos depois que o agente responder
with right:
    live = st.session_state.live_menu
    if live:
        items = [(live_dish(m), m["reason"] or None, i + 1) for i, m in enumerate(live)]
    else:  # agente simulado
        items = [
            (DISH_BY_ID[r["dish_id"]], r["reason"], i + 1)
            for i, r in enumerate(st.session_state.recs)
            if r["dish_id"] in DISH_BY_ID
        ]
    if items:
        st.markdown("**Opções para você** · clique em Adicionar para confirmar com o agente")
        render_cards(items[:4], "opt", live=bool(live))
    else:
        st.markdown(
            '<div class="empty">🍽️<br>Conte ao agente o que você quer comer.<br>'
            "As opções aparecem aqui.</div>",
            unsafe_allow_html=True,
        )

# --- Barra lateral: carrinho, perfil, opções
with st.sidebar:
    ifood_cart = st.session_state.ifood_cart
    if ifood_cart:
        count = sum(i["quantity"] for i in ifood_cart["items"])
        st.metric(f"🛍 Carrinho iFood · {count} itens", brl(ifood_cart["total"]))
        for item in ifood_cart["items"]:
            st.caption(f'{item["quantity"]}× {item["name"]} — {item["restaurant"]} · {brl(item["price"])}')
        st.caption("Finalize pagamento e pedido no app do iFood.")
    else:
        cart = [DISH_BY_ID[i] for i in st.session_state.cart]
        st.metric(f"🛍 Carrinho · {len(cart)} itens", brl(sum(d["price"] for d in cart)))

    render_prefs(st.session_state.prefs)

    st.divider()
    st.toggle("Voz do agente", key="tts_on")
    st.button("Nova conversa", on_click=reset_demo, use_container_width=True)

    log = st.session_state.tool_log
    with st.expander(f"Log de tool calls ({len(log)})"):
        if not log:
            st.caption("Nenhuma chamada ainda.")
        for entry in reversed(log):  # mais recentes primeiro
            st.markdown(f"**`{entry['name']}`** · {entry['at']}")
            st.code(
                json.dumps({"args": entry["args"], "result": entry["result"]}, ensure_ascii=False, indent=1),
                language="json",
            )
