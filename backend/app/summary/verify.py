"""The guardrail (CHG-040). Code, not a prompt instruction.

A model asked politely not to invent things still invents things — the three failures the
client's own testing recorded are quoted in the tests. So after the model returns, and
before anything is shown, this module extracts every checkable claim from the draft and
judges each against the supplied figures:

- **every numeric figure**, digits or number-words, must be a supplied value;
- **every proper noun**, outside sentence-openers and a small closed grammar list, must
  appear in a supplied value;
- **place-shaped claims** (seaboard, counties, regions…) must appear in a supplied value;
- **a forbidden vocabulary** is refused anywhere it appears, whatever it is attached to.

**Pure, and deliberately so** — no imports from any other module, no store, no request.
The function is a string and a dict in, a verdict out, which is what keeps it testable
against exactly the sentences that have already gone wrong once.

The verdict lists every extracted claim, allowed or not, because the review drawer renders
the whole table: a fixed four-row table is how the fifth invention gets past a reviewer.
"""

import re

# Words the summary may never contain, wherever they appear and whatever they are attached
# to. Each one either describes the storm (this platform does not), implies a live system
# (none exists), or dresses the arithmetic as something grander than it is.
FORBIDDEN_VOCABULARY = (
    "telemetry",
    "sensor",
    "sensors",
    "predictive",
    "prediction",
    "predictions",
    "model",
    "models",
    "landfall",
    "sustained winds",
    "mph",
    "protocol",
    "protocols",
    "activated",
    "monitoring system",
    "ai",
    "algorithm",
    "algorithms",
)

# Nouns that shape a claim about geography or scale. A draft may only speak about places
# and populations the platform supplied — "across three counties" was a real failure, and
# it names a geography nobody gave the model.
PLACE_WORDS = (
    "seaboard",
    "county",
    "counties",
    "coast",
    "coastal",
    "coastline",
    "state",
    "states",
    "city",
    "cities",
    "region",
    "regions",
    "district",
    "districts",
)

# Number words a draft might spell out. Narrow on purpose: "one" alone is a pronoun more
# often than a count, so a number word is only extracted when it quantifies a noun.
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "dozen": 12, "twenty": 20, "hundred": 100, "thousand": 1000,
}

# Capitalised words that are grammar rather than names. Small and closed: anything else
# capitalised mid-sentence has to earn its place by appearing in a supplied value.
_GRAMMAR = frozenset(
    w.lower()
    for w in (
        "The", "A", "An", "It", "Its", "This", "That", "These", "Those", "We", "Our",
        "There", "No", "Not", "And", "Or", "But", "Of", "In", "On", "At", "As", "To",
        "With", "Currently", "Current", "Estimated", "Approximately",
    )
)

# The per-asset path's one recorded difference (CHG-059): a gust reason legitimately
# states the gust in mph, so `mph` cannot be forbidden there — the figure check is the
# guard that pins every stated number to a supplied value. Everything else stays banned.
ASSET_FORBIDDEN_VOCABULARY = tuple(
    term for term in FORBIDDEN_VOCABULARY if term != "mph"
)

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_TIME = re.compile(r"^\d{1,2}[:.]\d{2}$")
_CAP_RUN = re.compile(r"(?:[A-Z][A-Za-z'’\-]+)(?:\s+[A-Z][A-Za-z'’\-]+)*")


def _supplied_text(figures: dict) -> str:
    """Every supplied value, flattened to one lowercase haystack."""
    return " ".join(str(value) for value in figures.values()).lower()


def _supplied_numbers(figures: dict) -> set[str]:
    """Every number that appears in any supplied value, normalised (commas stripped)."""
    found = set()
    for value in figures.values():
        for match in _NUMBER.finditer(str(value)):
            found.add(match.group().replace(",", ""))
            # "41,200 customers" may be drafted as "41200" or "41,200"; both normalise
            # here. A percentage of a figure does not: only the figure itself is supplied.
    return found


def _sentence_starts(text: str) -> set[int]:
    starts = {0}
    for match in re.finditer(r"[.!?]\s+", text):
        starts.add(match.end())
    return starts


def verify_asset(text: str, figures: dict) -> dict:
    """CHG-059: the per-asset path — the same judge, with `mph` speakable."""
    return verify(text, figures, forbidden=ASSET_FORBIDDEN_VOCABULARY)


def verify(text: str, figures: dict, *, forbidden=FORBIDDEN_VOCABULARY) -> dict:
    """Judge one draft. Returns {'ok': bool, 'entries': [...]} — every extracted claim,
    each with its verdict, so the review drawer can render the whole table."""
    entries: list[dict] = []
    lowered = text.lower()
    haystack = _supplied_text(figures)
    allowed_numbers = _supplied_numbers(figures)

    # (a) numeric figures ------------------------------------------------------------
    for match in _NUMBER.finditer(text):
        token = match.group()
        normalised = token.replace(",", "")
        if _TIME.match(token):
            # A clock time is judged as text against the supplied timestamp below,
            # not as an integer — 14:20 is not the number fourteen-twenty.
            allowed = token in str(figures.get("forecast_issued_at", ""))
            entries.append(
                {"kind": "figure", "token": token, "allowed": allowed,
                 "platform_value": figures.get("forecast_issued_at")}
            )
            continue
        allowed = normalised in allowed_numbers
        entries.append(
            {"kind": "figure", "token": token, "allowed": allowed,
             "platform_value": _platform_value_for(normalised, figures)}
        )

    # (a') spelled-out counts, when they quantify a noun ------------------------------
    for match in re.finditer(
        r"\b(" + "|".join(NUMBER_WORDS) + r")\s+([a-z]+)", lowered
    ):
        word, noun = match.group(1), match.group(2)
        if noun in ("of", "or", "and", "the", "hand", "another"):
            continue
        value = str(NUMBER_WORDS[word])
        allowed = value in allowed_numbers
        entries.append(
            {"kind": "figure", "token": f"{word} {noun}", "allowed": allowed,
             "platform_value": _platform_value_for(value, figures)}
        )

    # (b) proper nouns ----------------------------------------------------------------
    starts = _sentence_starts(text)
    for match in _CAP_RUN.finditer(text):
        run = match.group()
        words = run.split()
        if match.start() in starts:
            # A sentence-opener proves nothing about names. Drop the first word and
            # judge the rest of the run, which is where a real name would continue.
            words = words[1:]
            if not words:
                continue
        candidate = " ".join(words)
        if all(word.lower() in _GRAMMAR for word in words):
            continue
        allowed = candidate.lower() in haystack
        entries.append(
            {"kind": "noun", "token": candidate, "allowed": allowed,
             "platform_value": None}
        )

    # (b') place-shaped claims ----------------------------------------------------------
    for word in PLACE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered) and word not in haystack:
            entries.append(
                {"kind": "noun", "token": word, "allowed": False, "platform_value": None}
            )

    # (c) forbidden vocabulary ----------------------------------------------------------
    for term in forbidden:
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            entries.append(
                {"kind": "vocabulary", "token": term, "allowed": False,
                 "platform_value": None}
            )

    # The verdict IS the conjunction — there is no code path to ok=True past a
    # disallowed entry, which is the mutation the last test in the suite kills.
    return {"ok": all(entry["allowed"] for entry in entries), "entries": entries}


def _platform_value_for(normalised: str, figures: dict):
    """The supplied figure a number matches, for the drawer's In-the-platform column."""
    for name, value in figures.items():
        if normalised in {m.group().replace(",", "") for m in _NUMBER.finditer(str(value))}:
            return {"figure": name, "value": value}
    return None
