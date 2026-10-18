"""Ponte entre o site e o agente Gemini CLI (GEMINI.md + iFood MCP em .gemini/settings.json).

Cada mensagem do site vira uma chamada headless:

    gemini -p "<mensagem>" -o stream-json --policy agent/web-policy.toml [--resume <session_id>]

executada na raiz do projeto, para o CLI carregar GEMINI.md e o servidor MCP "ifood".
Antes da mensagem vão as instruções de agent/web-instructions.md, que pedem ao Gemini um bloco
```ifit {json}``` no fim da resposta com os pratos apresentados e o estado do carrinho do iFood.
Esse bloco é removido do texto e devolvido em "menu" e "cart".
A memória da conversa fica na sessão do próprio Gemini CLI: devolvemos o session_id e o
front-end o manda de volta na próxima mensagem.

Variáveis de ambiente:
  GEMINI_BIN      — caminho do executável (padrão: "gemini" no PATH).
  GEMINI_MODEL    — opcional, força um modelo (ex.: gemini-flash-lite-latest).
  GEMINI_TIMEOUT  — segundos por mensagem (padrão: 180).
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = Path(__file__).resolve().parent / "web-policy.toml"
INSTRUCTIONS_FILE = Path(__file__).resolve().parent / "web-instructions.md"
DATA_BLOCK = re.compile(r"```ifit\s*(.*?)```", re.S)


class GeminiCLIError(Exception):
    """Falha ao falar com o Gemini CLI (não instalado, cota, timeout...)."""


def _command(message: str, session_id: str | None) -> list:
    binary = os.getenv("GEMINI_BIN") or shutil.which("gemini")
    if not binary:
        raise GeminiCLIError("Gemini CLI não encontrado (instale com: npm i -g @google/gemini-cli).")
    cmd = [
        binary, "-p", message,
        "-o", "stream-json",
        "--policy", str(POLICY_FILE),
        "--allowed-mcp-server-names", "ifood",
    ]
    if session_id:
        cmd += ["--resume", session_id]
    if os.getenv("GEMINI_MODEL"):
        cmd += ["-m", os.environ["GEMINI_MODEL"]]
    return cmd


def _error_hint(stderr: str) -> str:
    if "429" in stderr or "quota" in stderr.lower():
        return "cota da API do Gemini esgotada, tente mais tarde ou troque GEMINI_MODEL"
    lines = [ln.strip() for ln in stderr.splitlines() if ln.strip() and not ln.strip().startswith("at ")]
    return lines[-1][:300] if lines else "erro desconhecido"


def _number(value, default=None):
    if isinstance(value, (int, float)):
        return value
    match = re.search(r"\d+(?:[.,]\d+)?", str(value or ""))
    return float(match.group().replace(",", ".")) if match else default


def _menu_item(raw: dict) -> dict | None:
    if not isinstance(raw, dict) or not raw.get("name"):
        return None
    return {
        "id": str(raw.get("item_id") or raw["name"]),
        "merchant_id": raw.get("merchant_id"),
        "name": raw["name"],
        "restaurant": raw.get("restaurant") or "",
        "description": raw.get("description") or "",
        "price": _number(raw.get("price"), 0.0),
        "eta": raw.get("eta") or "",
        "kcal": _number(raw.get("kcal")),
        "protein": _number(raw.get("protein")),
        "carbs": _number(raw.get("carbs")),
        "fat": _number(raw.get("fat")),
        "tags": [str(t) for t in raw.get("tags") or []],
        "reason": raw.get("reason") or "",
        "image_url": raw.get("image_url") or None,
    }


def _cart(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    items = [
        {
            "item_id": i.get("item_id"),
            "name": i.get("name") or "",
            "restaurant": i.get("restaurant") or "",
            "price": _number(i.get("price"), 0.0),
            "quantity": int(_number(i.get("quantity"), 1)),
        }
        for i in raw.get("items") or []
        if isinstance(i, dict)
    ]
    total = _number(raw.get("total"))
    if total is None:
        total = sum(i["price"] * i["quantity"] for i in items)
    return {"cart_id": raw.get("cart_id"), "items": items, "total": total}


def _split_reply(text: str):
    """Separa o texto mostrado ao usuário do bloco ```ifit``` (menu + carrinho)."""
    blocks = DATA_BLOCK.findall(text)
    clean = DATA_BLOCK.sub("", text).strip()
    if not blocks:
        return clean, None, None
    try:
        data = json.loads(blocks[-1])
    except json.JSONDecodeError:
        return clean, None, None
    menu = [m for m in map(_menu_item, data.get("items") or []) if m]
    return clean, menu or None, _cart(data.get("cart"))


def gemini_cli_agent(message: str, preferences: dict, session_id: str | None = None) -> dict:
    timeout = int(os.getenv("GEMINI_TIMEOUT", "180"))
    try:
        proc = subprocess.run(
            _command(INSTRUCTIONS_FILE.read_text(encoding="utf-8") + message, session_id),
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        hint = f" ({_error_hint(stderr)})" if stderr.strip() else ""
        raise GeminiCLIError(f"o Gemini não respondeu em {timeout}s{hint}") from exc

    reply_parts, tool_calls, by_id = [], [], {}
    new_session = session_id
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "init":
            new_session = event.get("session_id") or new_session
        elif kind == "message" and event.get("role") == "assistant":
            reply_parts.append(event.get("content", ""))
        elif kind == "tool_use":
            call = {"name": event.get("tool_name"), "args": event.get("parameters", {}), "result": None}
            tool_calls.append(call)
            by_id[event.get("tool_id")] = call
        elif kind == "tool_result" and event.get("tool_id") in by_id:
            by_id[event["tool_id"]]["result"] = {
                k: v for k, v in event.items() if k not in ("type", "timestamp", "tool_id")
            }

    reply, menu, cart = _split_reply("".join(reply_parts))
    if not reply:
        raise GeminiCLIError(_error_hint(proc.stderr))

    return {
        "reply": reply,
        "preferences": preferences,  # o perfil fica na sessão do Gemini, não na barra lateral
        "recommendations": None,     # pratos reais do MCP não têm card no catálogo simulado
        "tool_calls": tool_calls,
        "session_id": new_session,
        "menu": menu,  # pratos reais desta resposta (None = mantém o cardápio atual)
        "cart": cart,  # carrinho do iFood após mudanças (None = não mudou)
    }
