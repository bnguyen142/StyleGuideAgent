# FitFindr

FitFindr is a multi-tool agent that takes a natural-language request for secondhand
clothing, finds a matching listing, suggests how to style it with the user's existing
wardrobe, and turns that into a shareable outfit caption.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]`

- **`description`** (str): free-text keywords describing what the user wants (e.g.
  `"90s track jacket"`).
- **`size`** (str | None): size string to filter on, case-insensitive substring match
  (e.g. `"M"` matches a listing sized `"S/M"`). `None` skips the size filter.
- **`max_price`** (float | None): inclusive price ceiling. `None` skips the price filter.
- **Returns**: a list of listing dicts (`id`, `title`, `description`, `category`,
  `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`), filtered
  by size/price, scored by keyword overlap between `description` and each listing's
  title/description/category/style_tags/brand, with zero-score listings dropped and
  the rest sorted highest score first.
- **Purpose**: turn a loosely-worded request into a ranked shortlist of real listings.

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

- **`new_item`** (dict): a listing dict, normally `search_results[0]` from
  `search_listings`.
- **`wardrobe`** (dict): the user's wardrobe, with an `items` key holding a list of
  wardrobe item dicts (`id`, `name`, `category`, `colors`, `style_tags`, `notes`).
- **Returns**: a non-empty string (2–4 sentences) from the LLM. If `wardrobe["items"]`
  is non-empty, it suggests outfits that pair `new_item` with specific named wardrobe
  pieces. If `wardrobe["items"]` is empty, it falls back to general styling advice for
  `new_item` alone.
- **Purpose**: connect a potential purchase to the user's actual closet (or give them
  a starting point if they have none on file).

### `create_fit_card(outfit: str, new_item: dict) -> str`

- **`outfit`** (str): the styling suggestion returned by `suggest_outfit`.
- **`new_item`** (dict): the same listing dict passed to `suggest_outfit`.
- **Returns**: a 2–4 sentence, casual, Instagram-style caption that mentions the item
  name, price, and platform once each and captures the outfit's vibe. Generated at
  `temperature=1.1` so repeated calls on the same input read differently. If `outfit`
  is empty or whitespace-only, returns the literal string
  `"Can't create a description without outfit suggestion"` without calling the LLM.
- **Purpose**: produce the final shareable artifact the user actually walks away with.

## Planning Loop

`run_agent(query, wardrobe)` in `agent.py` runs a fixed sequence of steps, but with a
real conditional branch that changes which tools run:

1. **Parse** `query` with `_parse_query()` — regex pulls out `size\s+(\w+)` and
   `under\s+\$?(\d+)` patterns for `size` and `max_price`; whatever text is left
   (with leftover commas/periods cleaned up) becomes `description`. Stored in
   `session["parsed"]`.
2. **Search**: call `search_listings(description, size, max_price)`, store the result
   in `session["search_results"]`.
3. **Branch on results**:
   - If `session["search_results"]` is **empty**, set `session["error"]` to a message
     telling the user to drop the size filter, raise `max_price`, or try different
     keywords, and **return immediately** — `suggest_outfit` and `create_fit_card`
     are never called.
   - If **not empty**, set `session["selected_item"] = search_results[0]` and continue.
4. **Style**: call `suggest_outfit(selected_item, wardrobe)`, store in
   `session["outfit_suggestion"]`.
5. **Caption**: call `create_fit_card(outfit_suggestion, selected_item)`, store in
   `session["fit_card"]`.
6. Return `session`.

The agent's behavior is *not* "call all three tools every time" — step 3 is the
decision point that determines whether the rest of the loop runs at all.

## State Management

Everything lives in a single `session` dict created fresh by `_new_session()` for
each call to `run_agent()` — nothing persists between calls.

| Key | Set by | Consumed by |
|---|---|---|
| `query`, `wardrobe` | input to `run_agent` | `_parse_query`, `suggest_outfit` |
| `parsed` | `_parse_query(query)` | `search_listings` (unpacked as args) |
| `search_results` | `search_listings(...)` | branch check in step 3 |
| `selected_item` | `search_results[0]` | `suggest_outfit`, `create_fit_card` |
| `outfit_suggestion` | `suggest_outfit(...)` | `create_fit_card` |
| `fit_card` | `create_fit_card(...)` | final output |
| `error` | set only on the no-results branch | `app.py` (short-circuits the UI) |

The tools never call each other or share state directly — `run_agent()` is the only
thing that reads from and writes to `session`, pulling each tool's output and handing
it to the next tool as an argument. `app.py`'s `handle_query()` just reads the final
`session` dict and maps `error` / `selected_item` / `outfit_suggestion` / `fit_card`
onto the three Gradio output panels.

## Error Handling

| Tool | Failure mode | Agent response | Tested with |
|---|---|---|---|
| `search_listings` | No listings match `description`/`size`/`max_price` | Returns `[]` (no exception). `run_agent` sets `session["error"]` to *"No listings matched your search. Try removing the size filter, raising your max price, or using broader/different keywords."* and returns immediately — `suggest_outfit`/`create_fit_card` never run. | `"designer ballgown size XXS under $5"` → `search_results == []`, error message set, `fit_card` stays `None`. |
| `suggest_outfit` | `wardrobe["items"]` is empty | Skips the wardrobe-matching prompt and asks the LLM for general styling advice for `new_item` alone — still returns a non-empty string. | Called with `get_empty_wardrobe()` on the Y2K Baby Tee → *"The Y2K Baby Tee in butterfly print is a playful and whimsical piece that pairs well with high-waisted jeans, flowy skirts, or distressed shorts..."* |
| `create_fit_card` | `outfit` is empty or whitespace-only | Returns the literal string `"Can't create a description without outfit suggestion"` without calling the LLM. | `create_fit_card("", item)` → `"Can't create a description without outfit suggestion"` (also tested with `"   "`). |

## Spec Reflection

**Where the spec helped:** Locking down the exact failure-mode strings in
`planning.md` *before* writing any code made implementation and testing mechanical.
Because `create_fit_card`'s empty-input return value was specified as the literal
string `"Can't create a description without outfit suggestion"`, the pytest test for
that case could be written and asserted on an exact match with zero ambiguity.

**Where implementation diverged:** `planning.md` said the leftover text after parsing
out size/price "is okay if a little messy." In practice I added a small cleanup step
(collapsing whitespace and stripping stray commas/periods left behind by the regex
removal) that wasn't in the original spec — not because the messy version broke
`search_listings` (its keyword-overlap scoring handles noise fine), but because the
raw leftover text looked confusing when inspecting `session["parsed"]` during testing.

**Known limitation:** `search_listings`'s size filter uses case-insensitive substring
matching (e.g., `"M"` matches `"S/M"` and `"M/L"`), which works well for letter sizes
but has edge cases with the dataset's other size formats — e.g., searching `size="S"`
can match `"One Size"` listings (since "Size" contains "s"), and `size="L"` can match
waist/length notations like `"W30 L30"` (since "L30" contains "l"). A more robust
approach would tokenize both the search term and the listing's size string and check
for exact token overlap.

## AI Usage

1. **Tools (`search_listings`, `suggest_outfit`, `create_fit_card`)** — I gave Claude
   each tool's spec block from `planning.md` (inputs, return value, failure mode) one
   at a time, plus the existing docstring/TODO in `tools.py`, and asked it to
   implement just that function using `load_listings()`. I reviewed each
   implementation against the spec, then tested directly: ran `search_listings` on
   `"vintage graphic tee"`, `"designer ballgown" (size XXS, max $5)`, `"jeans" (size
   M)`, and `"jacket" (max $10)` to confirm the filter/score/sort behavior and the
   empty-results case; ran `suggest_outfit` against both `get_example_wardrobe()` and
   `get_empty_wardrobe()` to confirm the fallback path; and ran `create_fit_card`
   twice on identical input to confirm the `temperature=1.1` output actually varies,
   and once with `""` to confirm the exact guard string.

2. **Planning loop (`agent.py`)** — I gave Claude the Planning Loop, State Management,
   and Architecture sections of `planning.md` plus the existing `_new_session()` /
   `run_agent()` TODOs and asked it to implement `run_agent()` and the
   `_parse_query()` helper. I reviewed it by running `python agent.py` and checking
   both built-in cases: the happy path (graphic tee) correctly threads
   `selected_item` → `suggest_outfit` → `create_fit_card`, and the no-results path
   (`"designer ballgown size XXS under $5"`) sets `session["error"]` and leaves
   `fit_card` as `None` without calling the other two tools — matching the branch
   described in the diagram.

3. **UI wiring (`app.py`)** — I gave Claude the `handle_query()` TODO and the session
   dict structure from `agent.py` and asked it to map `session["error"]` /
   `selected_item` / `outfit_suggestion` / `fit_card` onto the three output panels. I
   verified it by launching `python app.py` and calling `handle_query` through the
   running app for both a happy-path query (all three panels populate, listing panel
   shows price/platform/condition/size) and the no-results query (error message in
   the first panel, other two panels empty).
