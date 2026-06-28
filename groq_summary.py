"""
groq_summary.py
───────────────────
Sends court-order text to Groq and returns structured summaries.

Two public functions:
  summarise_order(text, cnr)
  summarise_caseload(cases)
"""

import json
import re

from groq import Groq
from config import GROQ_API_KEY, DEBUG


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT INIT
# ─────────────────────────────────────────────────────────────────────────────

MODEL = "llama-3.3-70b-versatile"

FALLBACK = {
    "ai_outcome": "Not determinable from order text.",
    "ai_next_action": "Not determinable.",
    "ai_key_parties": "Not determinable.",
}

MAX_ORDER_CHARS = 6000

client = None

from config import GROQ_API_KEY
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ─────────────────────────────────────────────────────────────────────────────
# ORDER PROMPT
# ─────────────────────────────────────────────────────────────────────────────

_ORDER_SYSTEM = """
You are a legal analyst specialising in Indian court proceedings.

Given the text of a court order, extract exactly three fields.

Reply ONLY with a JSON object.

{
  "outcome": "One sentence describing what the court decided.",
  "next_action": "One sentence describing what the advocate should do next.",
  "key_parties": "Comma-separated names of judges, advocates, petitioners and respondents."
}

Rules:
- Be factual.
- Never invent details.
- If information is unavailable, write:
  "Not determinable from order text."
"""


# ─────────────────────────────────────────────────────────────────────────────
# ORDER SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def summarise_order(order_text: str, cnr: str = "") -> dict:

    if client is None:
        return FALLBACK.copy()

    if not order_text:
        return FALLBACK.copy()

    if len(order_text.strip()) < 40:
        if DEBUG:
            print(f"[{cnr}] Order text too short.")
        return FALLBACK.copy()

    text = order_text[:MAX_ORDER_CHARS]

    if len(order_text) > MAX_ORDER_CHARS:
        text += "\n\n[TRUNCATED]"

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": _ORDER_SYSTEM,
                },
                {
                    "role": "user",
                    "content": f"Court Order:\n\n{text}",
                },
            ],
            temperature=0.15,
            max_tokens=400,
        )

        raw = response.choices[0].message.content.strip()

        # Remove markdown fences
        raw = re.sub(
            r"^```(?:json)?|```$",
            "",
            raw,
            flags=re.MULTILINE,
        ).strip()

        # Sometimes model returns extra text
        match = re.search(r"\{.*\}", raw, re.DOTALL)

        if match:
            raw = match.group()

        parsed = json.loads(raw)

        return {
            "ai_outcome":
                parsed.get(
                    "outcome",
                    FALLBACK["ai_outcome"],
                ),

            "ai_next_action":
                parsed.get(
                    "next_action",
                    FALLBACK["ai_next_action"],
                ),

            "ai_key_parties":
                parsed.get(
                    "key_parties",
                    FALLBACK["ai_key_parties"],
                ),
        }

    except json.JSONDecodeError as e:

        if DEBUG:
            print(
                f"[{cnr}] JSON parsing failed: {e}"
            )

        return FALLBACK.copy()

    except Exception as e:

        if DEBUG:
            print(
                f"[{cnr}] Groq API error: {e}"
            )

        return FALLBACK.copy()


# ─────────────────────────────────────────────────────────────────────────────
# CASELOAD SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def summarise_caseload(cases: list) -> str:

    if client is None:
        return (
            "AI caseload analysis unavailable."
        )

    if not cases:
        return (
            "No case data available for analysis."
        )

    try:

        rows = "\n".join(
            (
                f"- "
                f"{c.get('cnr_number','?')} | "
                f"{c.get('case_type','?')} | "
                f"Stage: {c.get('case_stage','?')} | "
                f"Next: {c.get('next_hearing_date','?')} | "
                f"Adjournments: "
                f"{c.get('consecutive_adjournments',0)}"
            )
            for c in cases[:60]
        )

        prompt = f"""
You are a legal practice analyst.

Below is a summary of {len(cases)} active cases.

{rows}

Write a professional 3-4 sentence paragraph:

1. Describe the case distribution.
2. Highlight urgent hearings.
3. Highlight repeated adjournments.
4. Suggest one priority action.

Do not use bullet points.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.4,
            max_tokens=300,
        )

        return (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as e:

        if DEBUG:
            print(
                f"[groq] Caseload analysis failed: {e}"
            )

        return (
            "Could not generate "
            "caseload analysis."
        )