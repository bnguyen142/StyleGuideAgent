from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ──────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []  # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("track jacket", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


# ── suggest_outfit ───────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    advice = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(advice, str)
    assert advice.strip() != ""


def test_suggest_outfit_empty_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    advice = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(advice, str)
    assert advice.strip() != ""


# ── create_fit_card ──────────────────────────────────────────────────────────

def test_create_fit_card_with_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    outfit = "Pair this tee with your favorite jeans and sneakers."
    card = create_fit_card(outfit, item)
    assert isinstance(card, str)
    assert card.strip() != ""


def test_create_fit_card_empty_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    card = create_fit_card("", item)
    assert card == "Can't create a description without outfit suggestion"


def test_create_fit_card_whitespace_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    card = create_fit_card("   ", item)
    assert card == "Can't create a description without outfit suggestion"
