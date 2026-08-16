"""One alphabet for what counts as blank, in one place (CHG-037, CHG-039).

**This module exists because CHG-037's answer was right and its reach was one column.** The
alphabet was written into `store/dispatch.py` for a dismissal reason and a neighbourhood, tied to
the schema and to the browser by a test — and three other free-text columns a person types went
on being trimmed by whatever their own module reached for:

- **`decision_records.payload.$.crew`** (TASK-007) used `str.strip()`, and in the schema a
  one-argument `trim()` plus five `replace`s. Both let U+200B and U+FEFF through, so a placement
  could be recorded under a person's name with an **invisible** crew label — in the one table
  BR-004 forbids correcting.
- **`scenarios.name`** (TASK-009) used `" \\t\\n\\r\\v\\f"`, the six ASCII ones, in the service
  and the identical six in the schema. The two agreed perfectly and were wrong the same way, so
  a storm could be loaded with no visible label on the switcher REQ-F-010 is about.
- **`scenarios.source_note`** (TASK-009) used the same six: a note that claims to say where a
  storm came from and says nothing.

**This is a leaf module and it has to be one.** `store/dispatch.py` imports `store/decisions.py`,
so `decisions` cannot import `dispatch` back without the cycle FF-001 exists to refuse. Every
module that needs the alphabet imports it from here instead, and `dispatch.BLANK_CODEPOINTS`
stays the name the CHG-037 tie test reads, because it is bound to this tuple.

**What it is not.** It is not enforcement — ADR-002 puts that in the schema, and migrations 015
and 016 hold the same alphabet as `char(...)`. What this buys is the service layer answering the
specified `400` for a value the store would refuse anyway, instead of turning it into a `500`.
"""

# The six ASCII ones, the four information separators, Unicode's `White_Space` additions, and
# the two invisibles that are **not** `White_Space` and are exactly what a caller reaches for —
# U+200B ZERO WIDTH SPACE and U+FEFF ZERO WIDTH NO-BREAK SPACE. Neither Python's `str.strip()`
# nor JavaScript's `String.prototype.trim()` removes U+200B; JavaScript removes U+FEFF and
# Python does not; SQLite's one-argument `trim()` removes neither and strips spaces alone. Three
# languages, three sets — so the members are named here rather than borrowed from any of them.
BLANK_CODEPOINTS = (
    0x09, 0x0A, 0x0B, 0x0C, 0x0D,                    # tab, newline, vertical tab, form feed, CR
    0x1C, 0x1D, 0x1E, 0x1F,                          # the four information separators
    0x20,                                            # space
    0x85,                                            # next line
    0xA0,                                            # no-break space
    0x1680,                                          # ogham space mark
    0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005,  # en quad … figure space
    0x2006, 0x2007, 0x2008, 0x2009, 0x200A,          # … hair space
    0x200B,                                          # zero width space — invisible, not blank
    0x2028, 0x2029,                                  # line and paragraph separators
    0x202F,                                          # narrow no-break space
    0x205F,                                          # medium mathematical space
    0x3000,                                          # ideographic space
    0xFEFF,                                          # zero width no-break space
)

WHITESPACE = "".join(chr(point) for point in BLANK_CODEPOINTS)


def trim(value: str) -> str:
    """The ends only. What a person typed in the middle is theirs."""
    return value.strip(WHITESPACE)


def is_blank(value: str | None) -> bool:
    """True when the value is made of nothing a reader could see.

    `None` counts, because an absent label and a label of one zero-width space are the same
    thing to whoever reads the screen — which is the whole of CHG-039's finding.
    """
    return not trim(value or "")


def sql_char_call(*, without_space: bool = False) -> str:
    """The alphabet as SQLite's `char(...)`, for reading a migration back in a test.

    Not used to build a migration — a migration is raw SQL and stays readable as raw SQL
    (ADR-008's reason for hand-written migrations). This is here so a test can construct the
    exact string it expects to find in `sqlite_master` rather than repeating 31 numbers.

    `without_space` renders the form a `glob` character class needs: `char(32)` closes nothing
    in a `glob` set, but a literal space inside `'*[...]*'` matches a space that a well-formed
    single-spaced value is allowed to contain, so the interior scan omits it deliberately.
    """
    points = [point for point in BLANK_CODEPOINTS if not (without_space and point == 0x20)]
    return "char(" + ", ".join(str(point) for point in points) + ")"
