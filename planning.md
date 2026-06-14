# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**

Searches the mock listings dataset for secondhand items that match a text description, with optional size and max price filters, and returns the best matches sorted by relevance.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str):  will be used to try match user request for keyword 
- `size` (str):  tell you size of the clothes and used to match users size
- `max_price` (float): tell us the maximum amount the user is willing to pay so that it will compare with item for sale to see if it price is under or matches this prices

**What it returns:**
it returns a list sort by relevence with return id, description, category, style_tags, price, title, size, condition, colors, brand, platform

**What happens if it fails or returns nothing:**
The tool itself returns an empty list (`[]`) — it does not raise an exception. When this happens, the agent tells the user no matching listings were found and suggests they try loosening their search: removing the size filter, raising the max price, or using broader/different keywords in the description.

---

### Tool 2: suggest_outfit

**What it does:**
This tool will help the user get their style together. If the user has items already in their wardrobe, the program will suggest how the new item matches with what they currently have. If the wardrobe is empty, the program will give generic styling advice for the new item instead.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): the top result returned by `search_listings` — a listing dict with fields like `id`, `title`, `category`, `style_tags`, `price`, etc.
- `wardrobe` (dict): the user's existing closet — a dict with an `items` key containing a list of wardrobe item dicts, each with fields like `id`, `category`, `style_tags`, `colors`, `notes`

**What it returns:**
it off style advice that combines the new items with items already own for a complete outfit. 

**What happens if it fails or returns nothing:**
if empty it will return general styling advice about the new items rather than matching to own pieces

---

### Tool 3: create_fit_card

**What it does:**
Takes the outfit suggestion from `suggest_outfit` and the new item from `search_listings`, and turns them into one short, shareable caption — like something someone would post with a thrifted outfit pic.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): the styling suggestion text that came back from `suggest_outfit`, describing how to wear the new item with stuff from the wardrobe
- `new_item` (dict): the same listing dict from `search_listings`, with fields like `title`, `price`, `platform`, `condition` that get used in the caption

**What it returns:**
A short string like 2-4 sentences, written like something in instagram. It is casual like someone having a conversation with details item name, price, platform. Give the vibe of the outfit from 'outfit'. Should sound a little different every time, even for the same item, since the LLM runs at a higher temperature.

**What happens if it fails or returns nothing:**
if 'outfit' is empty the tool should not call LLM. It should return "Can't create a description without outfit suggestion"

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**

1. First we break down the user's query into description, size, and max_price using regex/string matching — looking for patterns like "size M" or "under $30" for size and price. Whatever's left over becomes the description, and it's okay if that's a little messy since search_listings already does keyword matching anyway. Store all three in `session["parsed"]`.
2. Call `search_listings(description, size, max_price)` and store what comes back in `session["search_results"]`.
3. Check if `session["search_results"]` is empty.
   - **If yes**: don't proceed any further. Set `session["error"]` to a message asking the user to reword their search — maybe drop the size filter, raise the max price, or try different keywords. Return the session right away — `suggest_outfit` and `create_fit_card` don't get called.
   - **If no**: take the highest ranked item, `search_results[0]`, as `selected_item`, and move on.
4. Call `suggest_outfit(selected_item, wardrobe)` and store what it gives back in `session["outfit_suggestion"]`.
5. Call `create_fit_card(outfit_suggestion, selected_item)` and store the result in `session["fit_card"]`.
6. Return the session. If `error` is `None` and `fit_card` has something in it, we're done.

---

## State Management

**How does information from one tool get passed to the next?**

Everything is tied to the session, which is a dictionary. The tools don't pass data to each other — it's the planning loop that pulls the right information out of the session and hands it to the next tool, which writes its result back in.

query and wardrobe get set at the beginning and don't change. We parse the user's query into description, size, and max_price, which get filled in by the parsing step. We use this info to create the arguments for search_listings, which returns search_results. The top item, search_results[0], gets stored as selected_item — this dict gets passed to both suggest_outfit and create_fit_card. outfit_suggestion is returned from suggest_outfit, then goes into create_fit_card as an argument. fit_card holds the final caption. error stays None the whole way through, unless search_results comes back empty — then error gets set and we return early.

Each call to run_agent() makes a fresh session dictionary, so nothing carries over between separate queries.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]` to a message telling the user no listings matched and suggesting they reword their search — drop the size filter, raise `max_price`, or use broader/different keywords. The loop returns right away; `suggest_outfit` and `create_fit_card` never get called. |
| suggest_outfit | Wardrobe is empty | Handled inside the tool itself — it checks `wardrobe["items"]` and, if empty, asks the LLM for general styling advice instead of matching to specific pieces. The loop doesn't need to do anything special; it just stores whatever comes back in `session["outfit_suggestion"]` and moves on as usual. |
| create_fit_card | Outfit input is missing or incomplete | The tool checks if `outfit` is empty/whitespace before calling the LLM, and if so returns `"Can't create a description without outfit suggestion"` instead of crashing. Since `suggest_outfit` always returns a non-empty string, this is really a defensive guard — it shouldn't actually trigger during normal use. |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│   User query + wardrobe (example/empty)      │
└─────────────────────┬─────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│   _new_session() creates session dict        │
└─────────────────────┬─────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│   Step 1: parse query (regex/string match)   │
│   → session["parsed"] =                      │
│       {description, size, max_price}         │
└─────────────────────┬─────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│   search_listings(description, size,         │
│       max_price)                             │
│   → session["search_results"]                │
└─────────────────────┬─────────────────────────┘
                       │
                       ▼
                 search_results
                    empty?
            ┌──────────┴──────────┐
          yes                     no
            │                      │
            ▼                      ▼
┌───────────────────────┐  ┌─────────────────────────────────┐
│ session["error"] =     │  │ session["selected_item"] =       │
│  "No matches found —   │  │   search_results[0]              │
│   try dropping size    │  └─────────────────┬─────────────────┘
│   filter, raising      │                    │
│   max_price, or using  │                    ▼
│   broader keywords"    │  ┌─────────────────────────────────┐
└───────────┬─────────────┘  │ suggest_outfit(selected_item,    │
            │                 │   wardrobe)                      │
            │                 │ (handles empty wardrobe          │
            │                 │  internally — always returns     │
            │                 │  non-empty)                       │
            │                 │ → session["outfit_suggestion"]   │
            │                 └─────────────────┬─────────────────┘
            │                                    │
            │                                    ▼
            │                 ┌─────────────────────────────────┐
            │                 │ create_fit_card(outfit_           │
            │                 │   suggestion, selected_item)      │
            │                 │ (guards against empty outfit,     │
            │                 │  won't trigger normally)          │
            │                 │ → session["fit_card"]            │
            │                 └─────────────────┬─────────────────┘
            │                                    │
            └─────────────────┬───────────────────┘
                               ▼
                ┌─────────────────────────────────┐
                │ Return session                    │
                │ (success: error=None,             │
                │  fit_card populated)              │
                │ (no-match: error message set,     │
                │  fit_card stays None)             │
                └─────────────────────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

I'll use Claude (this Claude Code session) for this, one tool at a time — not all three at once. For each tool, I'll give it that tool's spec block from planning.md (what it does, input parameters, what it returns, failure mode) along with the existing docstring/TODO already in tools.py, and ask it to implement just that function using load_listings() from utils/data_loader.py.

Before running anything, I'll check the generated code against the spec — does search_listings filter by size, max_price, and score by description like I wrote? Does suggest_outfit check wardrobe["items"] and fall back to general advice when it's empty? Does create_fit_card guard against an empty outfit and return the exact fallback string I specified? Then I'll test each one with a few hardcoded inputs, including the failure case, and write pytest tests in tests/test_tools.py covering all three failure modes before moving on.

**Milestone 4 — Planning loop and state management:**

For agent.py, I'll give Claude the Planning Loop, State Management, and Architecture diagram sections together, plus the existing _new_session() and run_agent() TODOs, and ask it to implement run_agent() following those steps.

Before trusting it, I'll check: does it branch on session["search_results"] being empty like the diagram shows? Does it stop and skip suggest_outfit/create_fit_card on that branch? Does it set selected_item = search_results[0] and pass that into both suggest_outfit and create_fit_card? Then I'll run python agent.py and confirm both test cases (happy path and no-results path) behave as described — printing session["selected_item"] and session["outfit_suggestion"] to confirm state is actually flowing through, not hardcoded.

For app.py, I'll give it the handle_query() TODO plus the session dict structure from State Management, and check that it maps session["error"], session["selected_item"], session["outfit_suggestion"], and session["fit_card"] to the three output panels correctly.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "Looking for a 90s track jacket, size M, under $50."

**Step 1:**
The loop parses the query. Regex finds "size M" → `size = "M"`, and "under $50" → `max_price = 50.0`. What's left becomes `description` (≈ "90s track jacket"). `session["parsed"] = {"description": "90s track jacket", "size": "M", "max_price": 50.0}`.

**Step 2:**
The loop calls `search_listings("90s track jacket", size="M", max_price=50.0)`. After filtering by size M and price ≤ $50, the top match by keyword overlap is "90s Track Jacket — Navy/White Stripe" (`lst_004`) — $45, size M, poshmark, excellent condition, tags `["90s", "vintage", "athletic", "streetwear"]`. `session["search_results"]` holds this as the top result.

**Step 3:**
`search_results` is not empty, so no error. `session["selected_item"] = search_results[0]` → the track jacket listing.

**Step 4:**
The loop calls `suggest_outfit(selected_item, wardrobe)` with the example wardrobe. It suggests pairing the jacket with pieces already in the closet — e.g. the white ribbed tank (w_003) underneath, baggy straight-leg jeans (w_001), and chunky white sneakers (w_007). `session["outfit_suggestion"]` = something like: "Layer this track jacket over your white ribbed tank, and pair it with your baggy jeans and chunky white sneakers for an easy 90s athletic-streetwear look."

**Step 5:**
The loop calls `create_fit_card(outfit_suggestion, selected_item)`. `session["fit_card"]` = something like: "snagged this 90s navy/white track jacket on poshmark for $45 in excellent condition — layered it over a white tank with my baggy jeans and chunky sneakers for instant throwback vibes ⚡"

**Final output to user:**
`session["error"]` is `None`. The Gradio UI shows three panels: the listing (90s Track Jacket — Navy/White Stripe, $45, poshmark, excellent, size M), the outfit suggestion, and the fit card caption.
