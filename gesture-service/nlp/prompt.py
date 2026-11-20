"""
Prompt construction for the NLP layer (KAN-19).

Turns an ordered gloss sequence (the output of KAN-18) into the system and
user prompts for the language model. The rules are written to keep the model
from inventing information that the signer did not sign.
"""

from __future__ import annotations

from typing import Any, Sequence

ARMENIAN_FULL_STOP = "։"
MISSING_MARKER = "[MISSING]"
UNCERTAIN_MARKER = "(uncertain)"

SYSTEM_PROMPT = f"""You convert a sequence of recognized Armenian Sign Language glosses into ONE grammatically correct Armenian sentence.

Rules:
1. Express only what the glosses say. Never add names, numbers, places, times, negation, or any fact that is not in the glosses.
2. You may add only what Armenian grammar requires: function words, verb forms, case endings and punctuation. Keep the gloss order unless Armenian grammar needs another order.
3. {MISSING_MARKER} means a sign was not recognized at that position. Do not guess the missing word. Write a sentence that stays true without it and set "complete" to false.
4. A gloss marked {UNCERTAIN_MARKER} was recognized with low confidence. Use it only if it fits the other glosses; if it makes the sentence doubtful, leave it out, list it in "omitted" and set "complete" to false.
5. "Context" holds earlier sentences of the same conversation. Use it only to resolve ambiguity (for example who is speaking, or the tense). Never copy it and never continue it.
6. Write the sentence in Armenian script and end it with the Armenian full stop "{ARMENIAN_FULL_STOP}" (or a question mark if the glosses clearly ask a question).
7. Answer with a single JSON object and nothing else, in exactly this shape:
{{"sentence": "<Armenian sentence>", "complete": true or false, "omitted": ["<gloss left out>", ...]}}"""


def build_user_prompt(tokens: Sequence[Any], gaps: Sequence[int], context: Sequence[str]) -> str:
    """
    tokens: objects with `.gloss` and `.status` ("accepted" / "uncertain")
    gaps:   positions of missing predictions (see GlossSequence.gaps)
    context: earlier sentences of the session, oldest first
    """
    gap_positions = set(gaps)
    lines: list[str] = ["Glosses in signing order:"]
    number = 1
    for index, token in enumerate(tokens):
        if index in gap_positions:
            lines.append(f"{number}. {MISSING_MARKER}")
            number += 1
        suffix = f" {UNCERTAIN_MARKER}" if token.status == "uncertain" else ""
        lines.append(f"{number}. {token.gloss}{suffix}")
        number += 1
    if len(tokens) in gap_positions:
        lines.append(f"{number}. {MISSING_MARKER}")

    if context:
        lines.append("")
        lines.append("Context (earlier sentences, oldest first; do not copy):")
        lines.extend(f"- {sentence}" for sentence in context)

    return "\n".join(lines)
