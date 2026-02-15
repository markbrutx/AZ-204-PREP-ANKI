#!/usr/bin/env python3
"""
Push rich quiz cards to Anki via AnkiConnect.

Supports multiple card types:
  - single-choice: classic 1-of-4 (default, backward compatible)
  - multi-select: pick N correct answers (checkboxes)
  - ordering: arrange items in correct order (up/down buttons)
  - code-hotarea: click on lines with errors (clickable code)

Usage:
    python3 scripts/push-to-anki.py source/01-app-service/rich-cards-v2.json
    python3 scripts/push-to-anki.py source/*/rich-cards-v2.json
    python3 scripts/push-to-anki.py --delete-deck "AZ-204-PREP-ANKI::01-App Service"
"""

import html as html_mod
import json
import sys
import urllib.request
from pathlib import Path

ANKI_URL = "http://127.0.0.1:8765"
MODEL_NAME = "AZ204 PREP Interactive"
BATCH_SIZE = 10

REQUIRED_CARD_FIELDS = {"question", "explanation", "keyPoints", "reference"}

MODEL_FIELDS = [
    "Question",
    "Type",
    "Options",
    "Answer",
    "Explanation",
    "KeyPoints",
    "Reference",
    "OrderItems",
    "CodeBlock",
]

# ---------------------------------------------------------------------------
# Shared styles
# ---------------------------------------------------------------------------

CONTAINER = (
    "max-width: 600px; margin: 0 auto; font-size: 18px; "
    "line-height: 1.8; padding: 15px; font-family: Arial, sans-serif; "
    "color: #ffffff; background-color: #1a1a1a; border-radius: 8px;"
)

QUESTION_BOX = (
    "padding: 12px; background-color: #1e3a8a; "
    "border: 2px solid #3b82f6; border-left: 4px solid #60a5fa; "
    "border-radius: 4px; color: #ffffff;"
)

CORRECT_BOX = (
    "max-width: 600px; margin: 0 auto; "
    "background-color: #14532d; border: 2px solid #22c55e; "
    "padding: 15px; border-radius: 8px;"
)

EXPLANATION_BOX = (
    "max-width: 600px; margin: 20px auto; padding: 12px; "
    "background-color: #1e3a8a; border: 2px solid #3b82f6; "
    "border-radius: 6px; color: #ffffff;"
)

REFERENCE_BOX = (
    "max-width: 600px; margin: 20px auto; padding: 8px; "
    "background-color: #581c87; border: 2px solid #9333ea; "
    "border-radius: 4px;"
)

CODE_BG = "background-color: #0d1117;"


def esc(text: str) -> str:
    """Escape HTML special characters."""
    return html_mod.escape(str(text), quote=True)


# ---------------------------------------------------------------------------
# HTML generators — Front side
# ---------------------------------------------------------------------------


def wrap_question(text: str, card_type: str = "single-choice", correct_count: int = 0) -> str:
    hint = ""
    has_select_hint = "select" in text.lower()
    if card_type == "multi-select" and not has_select_hint:
        hint = (
            '<div style="margin-top: 10px; padding: 6px 12px; '
            "background-color: #854d0e; border: 1px solid #ca8a04; "
            'border-radius: 4px; color: #fde047; font-size: 14px;">'
            f"Select {correct_count} answer{'s' if correct_count > 1 else ''}"
            "</div>"
        )
    elif card_type == "ordering":
        hint = (
            '<div style="margin-top: 10px; padding: 6px 12px; '
            "background-color: #854d0e; border: 1px solid #ca8a04; "
            'border-radius: 4px; color: #fde047; font-size: 14px;">'
            "Drag or use arrows to arrange in correct order"
            "</div>"
        )
    elif card_type == "code-hotarea":
        hint = (
            '<div style="margin-top: 10px; padding: 6px 12px; '
            "background-color: #854d0e; border: 1px solid #ca8a04; "
            'border-radius: 4px; color: #fde047; font-size: 14px;">'
            "Click on the line(s) with errors"
            "</div>"
        )

    return (
        f'<div style="{CONTAINER}">'
        '<strong style="color: #ffffff; font-size: 20px;">Question:</strong>'
        "<br><br>"
        f'<div style="{QUESTION_BOX}">{esc(text)}</div>'
        f"{hint}"
        "</div>"
    )


# --- Single-choice options (clickable, highlight on click) ---
def wrap_options_single(options: list[str]) -> str:
    items = ""
    for i, opt in enumerate(options):
        letter = chr(65 + i)
        items += (
            '<li style="margin-bottom: 12px; cursor: pointer; padding: 8px; '
            "background-color: #2a2a2a; border-radius: 4px; "
            "border: 2px solid #444;\" "
            "onclick=\"var s=this.style; "
            "if(s.borderColor==='rgb(59, 130, 246)'){s.borderColor='#444';s.backgroundColor='#2a2a2a';}"
            "else{var p=this.parentNode.children;for(var j=0;j<p.length;j++){p[j].style.borderColor='#444';p[j].style.backgroundColor='#2a2a2a';}"
            "s.borderColor='#3b82f6';s.backgroundColor='#1e3a5a';}\">"
            f"<strong>{letter}.</strong> {esc(opt)}</li>"
        )
    return (
        f'<div style="{CONTAINER}">\n'
        '<strong style="color: #ffffff; font-size: 18px;">Options:</strong>\n'
        '<ul style="margin-top: 10px; margin-left: 20px; '
        f'line-height: 1.8; color: #ffffff; list-style: none; padding-left: 0;">\n{items}</ul>\n'
        "</div>"
    )


# --- Multi-select options (checkboxes, multiple selection) ---
def wrap_options_multi(options: list[str]) -> str:
    items = ""
    for i, opt in enumerate(options):
        letter = chr(65 + i)
        cb_id = f"cb_{i}"
        items += (
            '<li style="margin-bottom: 12px; cursor: pointer; padding: 8px; '
            f"background-color: #2a2a2a; border-radius: 4px; border: 2px solid #444;\" "
            f"id=\"opt_{i}\" "
            f"onclick=\"var cb=document.getElementById('{cb_id}');cb.checked=!cb.checked;"
            f"var el=document.getElementById('opt_{i}');"
            "if(cb.checked){el.style.borderColor='#3b82f6';el.style.backgroundColor='#1e3a5a';}"
            "else{el.style.borderColor='#444';el.style.backgroundColor='#2a2a2a';}\">"
            f'<input type="checkbox" id="{cb_id}" '
            "style=\"margin-right: 8px; width: 18px; height: 18px; vertical-align: middle; pointer-events: none;\" "
            f"onclick=\"event.stopPropagation()\">"
            f"<strong>{letter}.</strong> {esc(opt)}</li>"
        )
    return (
        f'<div style="{CONTAINER}">\n'
        '<strong style="color: #ffffff; font-size: 18px;">Options:</strong>\n'
        '<ul style="margin-top: 10px; margin-left: 20px; '
        f'line-height: 1.8; color: #ffffff; list-style: none; padding-left: 0;">\n{items}</ul>\n'
        "</div>"
    )


# --- Ordering items (up/down buttons, shuffle on load) ---
def wrap_order_items(items: list[str]) -> str:
    li_items = ""
    for i, item in enumerate(items):
        li_items += (
            f'<li id="ord_{i}" style="margin-bottom: 8px; padding: 10px; '
            "background-color: #2a2a2a; border-radius: 4px; border: 2px solid #444; "
            'display: flex; align-items: center; gap: 10px;">'
            f'<span style="min-width: 24px; color: #9ca3af;">{i + 1}.</span>'
            f'<span style="flex: 1;">{esc(item)}</span>'
            '<span style="display: flex; flex-direction: column; gap: 2px;">'
            f'<button onclick="moveItem(\'ord_{i}\',-1)" '
            "style=\"padding: 2px 8px; background: #374151; color: #fff; border: 1px solid #555; "
            'border-radius: 3px; cursor: pointer; font-size: 14px;">&#9650;</button>'
            f'<button onclick="moveItem(\'ord_{i}\',1)" '
            "style=\"padding: 2px 8px; background: #374151; color: #fff; border: 1px solid #555; "
            'border-radius: 3px; cursor: pointer; font-size: 14px;">&#9660;</button>'
            "</span>"
            "</li>"
        )

    script = (
        "<script>"
        "function moveItem(elId, dir) {"
        "  var list = document.getElementById('orderList');"
        "  var el = document.getElementById(elId);"
        "  if (!el) return;"
        "  var items = list.children;"
        "  var curIdx = -1;"
        "  for (var k = 0; k < items.length; k++) {"
        "    if (items[k] === el) { curIdx = k; break; }"
        "  }"
        "  if (curIdx < 0) return;"
        "  var target = curIdx + dir;"
        "  if (target < 0 || target >= items.length) return;"
        "  if (dir === -1) {"
        "    list.insertBefore(el, items[target]);"
        "  } else {"
        "    list.insertBefore(items[target], el);"
        "  }"
        "  renumber();"
        "}"
        "function renumber() {"
        "  var list = document.getElementById('orderList');"
        "  var items = list.children;"
        "  for (var i = 0; i < items.length; i++) {"
        "    items[i].querySelector('span').textContent = (i + 1) + '.';"
        "  }"
        "}"
        "function shuffleOrder() {"
        "  var list = document.getElementById('orderList');"
        "  var items = Array.prototype.slice.call(list.children);"
        "  for (var i = items.length - 1; i > 0; i--) {"
        "    var j = Math.floor(Math.random() * (i + 1));"
        "    var temp = items[i]; items[i] = items[j]; items[j] = temp;"
        "  }"
        "  for (var i = 0; i < items.length; i++) {"
        "    list.appendChild(items[i]);"
        "  }"
        "  renumber();"
        "}"
        "setTimeout(shuffleOrder, 0);"
        "</script>"
    )

    return (
        f'<div style="{CONTAINER}">\n'
        '<strong style="color: #ffffff; font-size: 18px;">Arrange in order:</strong>\n'
        f'<ul id="orderList" style="margin-top: 10px; list-style: none; padding-left: 0;">\n'
        f"{li_items}</ul>\n"
        f"{script}\n"
        "</div>"
    )


# --- Code hot area (clickable code lines) ---
def wrap_code_hotarea(code_lines: list[str], language: str = "text") -> str:
    lines_html = ""
    for i, line in enumerate(code_lines):
        escaped = esc(line)
        lines_html += (
            f'<div id="codeline_{i}" '
            "style=\"padding: 4px 10px; cursor: pointer; border-left: 3px solid transparent; "
            "font-family: 'Courier New', monospace; font-size: 14px; "
            "white-space: pre; color: #e6edf3;\" "
            f"onclick=\"var el=document.getElementById('codeline_{i}');"
            "if(el.style.backgroundColor==='rgb(30, 58, 90)'){el.style.backgroundColor='transparent';el.style.borderLeftColor='transparent';}"
            "else{el.style.backgroundColor='#1e3a5a';el.style.borderLeftColor='#3b82f6';}\">"
            f'<span style="color: #6e7681; margin-right: 12px; user-select: none;">{i + 1:2d}</span>'
            f"{escaped}"
            "</div>"
        )

    return (
        f'<div style="{CONTAINER}">\n'
        f'<strong style="color: #ffffff; font-size: 18px;">Code ({esc(language)}):</strong>\n'
        f'<div style="margin-top: 10px; {CODE_BG} border-radius: 6px; '
        'padding: 12px 0; overflow-x: auto; border: 1px solid #30363d;">\n'
        f"{lines_html}"
        "</div>\n</div>"
    )


# ---------------------------------------------------------------------------
# HTML generators — Back side (static correct answers)
# ---------------------------------------------------------------------------


def wrap_answer_single(letter: str, options: list[str]) -> str:
    idx = ord(letter.upper()) - ord("A")
    option_text = options[idx] if 0 <= idx < len(options) else ""
    display = f"{letter} ({esc(option_text)})" if option_text else letter
    return (
        f'<div style="{CORRECT_BOX}">'
        '<span style="color: #4ade80; font-weight: bold; font-size: 20px;">'
        "&#10004; Correct Answer:</span> "
        f'<strong style="font-size: 18px; color: #86efac;">{display}</strong>'
        "</div>"
    )


def wrap_answer_multi(letters: list[str], options: list[str]) -> str:
    items = ""
    for letter in letters:
        idx = ord(letter.upper()) - ord("A")
        option_text = options[idx] if 0 <= idx < len(options) else ""
        items += (
            f'<div style="margin: 4px 0; padding: 6px 10px; '
            f"background-color: #14532d; border: 1px solid #22c55e; "
            f'border-radius: 4px;">'
            f'<strong style="color: #86efac;">{letter}.</strong> '
            f'<span style="color: #bbf7d0;">{esc(option_text)}</span></div>'
        )
    return (
        f'<div style="{CORRECT_BOX}">'
        '<span style="color: #4ade80; font-weight: bold; font-size: 20px;">'
        f"&#10004; Correct Answers ({len(letters)}):</span>"
        f'<div style="margin-top: 8px;">{items}</div>'
        "</div>"
    )


def wrap_answer_ordering(order_items: list[str]) -> str:
    items = ""
    for i, item in enumerate(order_items):
        items += (
            f'<div style="margin: 4px 0; padding: 8px 12px; '
            f"background-color: #14532d; border: 1px solid #22c55e; "
            f'border-radius: 4px; display: flex; gap: 10px;">'
            f'<strong style="color: #4ade80; min-width: 24px;">{i + 1}.</strong>'
            f'<span style="color: #bbf7d0;">{esc(item)}</span></div>'
        )
    return (
        f'<div style="{CORRECT_BOX}">'
        '<span style="color: #4ade80; font-weight: bold; font-size: 20px;">'
        "&#10004; Correct Order:</span>"
        f'<div style="margin-top: 8px;">{items}</div>'
        "</div>"
    )


def wrap_answer_code_hotarea(code_lines: list[str], error_indices: list[int], language: str = "text") -> str:
    lines_html = ""
    for i, line in enumerate(code_lines):
        escaped = esc(line)
        is_error = i in error_indices
        bg = "#3b1219" if is_error else "transparent"
        border_color = "#ef4444" if is_error else "transparent"
        marker = ' <span style="color: #ef4444; font-weight: bold;">&larr; ERROR</span>' if is_error else ""

        lines_html += (
            f'<div style="padding: 4px 10px; '
            f"background-color: {bg}; border-left: 3px solid {border_color}; "
            "font-family: 'Courier New', monospace; font-size: 14px; "
            f'white-space: pre; color: #e6edf3;">'
            f'<span style="color: #6e7681; margin-right: 12px;">{i + 1:2d}</span>'
            f"{escaped}{marker}"
            "</div>"
        )

    error_box_style = CORRECT_BOX.replace("#14532d", "#1a1a1a").replace("#22c55e", "#ef4444")
    return (
        f'<div style="{error_box_style}">'
        '<span style="color: #ef4444; font-weight: bold; font-size: 20px;">'
        f"&#128681; Error Line{'s' if len(error_indices) > 1 else ''}:</span>"
        f'<div style="margin-top: 10px; {CODE_BG} border-radius: 6px; '
        'padding: 12px 0; overflow-x: auto; border: 1px solid #30363d;">\n'
        f"{lines_html}"
        "</div></div>"
    )


def wrap_explanation(text: str) -> str:
    return (
        f'<div style="{EXPLANATION_BOX}">'
        '<span style="color: #60a5fa; font-weight: bold; font-size: 20px;">'
        "&#128214; Explanation:</span><br><br>"
        f"{esc(text)}</div>"
    )


def wrap_key_points(points: list[str]) -> str:
    items = "".join(
        f'<li style="margin-bottom: 6px;">{esc(p)}</li>' for p in points
    )
    return (
        '<div style="max-width: 600px; margin: 20px auto; color: #ffffff;">\n'
        '<span style="color: #fb923c; font-weight: bold; font-size: 20px;">'
        "&#128273; Key Points:</span>\n"
        '<ul style="margin-top: 10px; margin-left: 20px; '
        f'line-height: 1.8; color: #ffffff;">\n{items}</ul>\n'
        "</div>"
    )


def wrap_reference(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "#"
    safe_url = esc(url)
    return (
        f'<div style="{REFERENCE_BOX}">'
        '<span style="color: #c084fc; font-weight: bold; font-size: 18px;">'
        "&#128279; Reference:</span><br>"
        f'<a href="{safe_url}" style="color: #a78bfa; text-decoration: underline;" '
        f'target="_blank">{safe_url}</a></div>'
    )


# ---------------------------------------------------------------------------
# AnkiConnect helpers
# ---------------------------------------------------------------------------


def anki_request(action: str, **params) -> dict:
    payload = json.dumps({"action": action, "version": 6, "params": params})
    req = urllib.request.Request(
        ANKI_URL,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if result.get("error"):
        raise RuntimeError(f"AnkiConnect error: {result['error']}")
    return result["result"]


def check_connection() -> bool:
    try:
        ver = anki_request("version")
        print(f"AnkiConnect v{ver} connected")
        return True
    except Exception as e:
        print(f"AnkiConnect not available: {e}", file=sys.stderr)
        return False


def ensure_deck(deck_name: str) -> None:
    anki_request("createDeck", deck=deck_name)


def ensure_model() -> None:
    """Create the AZ204 PREP Interactive model if it doesn't exist."""
    existing = anki_request("modelNames")
    if MODEL_NAME in existing:
        existing_fields = anki_request("modelFieldNames", modelName=MODEL_NAME)
        missing = [f for f in MODEL_FIELDS if f not in existing_fields]
        if missing:
            print(f"ERROR: Model '{MODEL_NAME}' is missing fields: {missing}", file=sys.stderr)
            print("Delete and recreate the model, or add fields manually.", file=sys.stderr)
            sys.exit(1)
        return

    print(f"Creating model '{MODEL_NAME}'...")

    front_template = "{{Question}}{{Options}}{{OrderItems}}{{CodeBlock}}"
    back_template = (
        "{{FrontSide}}<hr id=answer>"
        "{{Answer}}"
        "{{Explanation}}"
        "{{KeyPoints}}"
        "{{Reference}}"
    )

    anki_request(
        "createModel",
        modelName=MODEL_NAME,
        inOrderFields=MODEL_FIELDS,
        css=(
            ".card { background-color: #1a1a1a; color: #ffffff; "
            "font-family: Arial, sans-serif; font-size: 18px; }"
        ),
        cardTemplates=[
            {
                "Name": "Card 1",
                "Front": front_template,
                "Back": back_template,
            }
        ],
    )
    print(f"Model '{MODEL_NAME}' created")


# ---------------------------------------------------------------------------
# Card -> Note conversion (dispatch by type)
# ---------------------------------------------------------------------------


def validate_card(card: dict) -> None:
    """Validate required fields and type-specific schema."""
    card_id = card.get("id", "unknown")
    missing = REQUIRED_CARD_FIELDS - card.keys()
    if missing:
        raise ValueError(f"Card {card_id} missing required fields: {missing}")

    card_type = card.get("type", "single-choice")
    answer = card.get("answer")

    if card_type == "multi-select":
        if not isinstance(answer, list) or not all(isinstance(a, str) for a in answer):
            raise ValueError(f"Card {card_id}: multi-select answer must be a list of strings")
    elif card_type == "ordering":
        if not isinstance(answer, list) or not all(isinstance(a, int) for a in answer):
            raise ValueError(f"Card {card_id}: ordering answer must be a list of ints")
    elif card_type == "code-hotarea":
        if not isinstance(answer, list) or not all(isinstance(a, int) for a in answer):
            raise ValueError(f"Card {card_id}: code-hotarea answer must be a list of ints")


def card_to_note(card: dict, deck_name: str) -> dict:
    validate_card(card)

    card_type = card.get("type", "single-choice")
    options = card.get("options", [])
    order_items = card.get("orderItems", [])
    code_lines = card.get("codeLines", [])
    language = card.get("language", "text")
    answer = card.get("answer", "")

    correct_count = len(answer) if isinstance(answer, list) else 0

    question_html = wrap_question(card["question"], card_type, correct_count)

    if card_type == "single-choice":
        options_html = wrap_options_single(options)
        answer_html = wrap_answer_single(answer, options)
        order_html = ""
        code_html = ""
    elif card_type == "multi-select":
        options_html = wrap_options_multi(options)
        answer_html = wrap_answer_multi(answer, options)
        order_html = ""
        code_html = ""
    elif card_type == "ordering":
        options_html = ""
        answer_html = wrap_answer_ordering(order_items)
        order_html = wrap_order_items(order_items)
        code_html = ""
    elif card_type == "code-hotarea":
        options_html = ""
        answer_html = wrap_answer_code_hotarea(code_lines, answer, language)
        order_html = ""
        code_html = wrap_code_hotarea(code_lines, language)
    else:
        raise ValueError(f"Unknown card type: {card_type}")

    return {
        "deckName": deck_name,
        "modelName": MODEL_NAME,
        "fields": {
            "Type": card_type,
            "Question": question_html,
            "Options": options_html,
            "Answer": answer_html,
            "Explanation": wrap_explanation(card["explanation"]),
            "KeyPoints": wrap_key_points(card["keyPoints"]),
            "Reference": wrap_reference(card["reference"]),
            "OrderItems": order_html,
            "CodeBlock": code_html,
        },
        "tags": card.get("tags", []),
    }


# ---------------------------------------------------------------------------
# Push logic
# ---------------------------------------------------------------------------


def push_notes(notes: list[dict]) -> tuple[int, int]:
    created = 0
    duplicates = 0
    for i in range(0, len(notes), BATCH_SIZE):
        batch = notes[i : i + BATCH_SIZE]
        results = anki_request_addnotes(batch)
        for r in results:
            if r is None:
                duplicates += 1
            else:
                created += 1
    return created, duplicates


def anki_request_addnotes(notes: list[dict]) -> list:
    """Call addNotes, handling per-note errors gracefully."""
    payload = json.dumps({
        "action": "addNotes",
        "version": 6,
        "params": {"notes": notes},
    })
    req = urllib.request.Request(
        ANKI_URL,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    error = result.get("error")
    if error and not isinstance(error, list):
        raise RuntimeError(f"AnkiConnect error: {error}")

    return result.get("result", [])


def delete_deck_cards(deck_name: str) -> int:
    note_ids = anki_request("findNotes", query=f'deck:"{deck_name}"')
    if note_ids:
        anki_request("deleteNotes", notes=note_ids)
    return len(note_ids)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def process_file(filepath: str) -> tuple[int, int]:
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}", file=sys.stderr)
        return 0, 0

    data = json.loads(path.read_text(encoding="utf-8"))
    deck_name = data["deckName"]
    cards = data["cards"]

    type_counts: dict[str, int] = {}
    for c in cards:
        t = c.get("type", "single-choice")
        type_counts[t] = type_counts.get(t, 0) + 1

    type_summary = ", ".join(f"{k}: {v}" for k, v in sorted(type_counts.items()))
    print(f"\n--- {deck_name} ({len(cards)} cards: {type_summary}) ---")

    ensure_deck(deck_name)

    notes = [card_to_note(c, deck_name) for c in cards]
    created, duplicates = push_notes(notes)

    print(f"  Created: {created}")
    print(f"  Duplicates: {duplicates}")

    return created, duplicates


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 push-to-anki.py <file.json> [file2.json ...]")
        print("       python3 push-to-anki.py --delete-deck <deck-name>")
        sys.exit(1)

    if sys.argv[1] == "--delete-deck":
        if len(sys.argv) < 3:
            print("Usage: --delete-deck <deck-name>")
            sys.exit(1)
        if not check_connection():
            sys.exit(1)
        count = delete_deck_cards(sys.argv[2])
        print(f"Deleted {count} notes from '{sys.argv[2]}'")
        return

    if not check_connection():
        sys.exit(1)

    ensure_model()

    total_created = 0
    total_duplicates = 0

    for filepath in sys.argv[1:]:
        created, duplicates = process_file(filepath)
        total_created += created
        total_duplicates += duplicates

    print(f"\n=== Total: {total_created} created, {total_duplicates} duplicates ===")


if __name__ == "__main__":
    main()
