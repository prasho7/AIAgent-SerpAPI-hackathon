import re

from models import AgentMode


def detect_likely_mode(question: str) -> AgentMode:
    """Choose a likely mode using deterministic keyword and intent matching."""
    text = (question or "").lower()

    # Explicit local discovery place and activity patterns
    local_patterns = [
        r"\bcafe\b",
        r"\bcafé\b",
        r"\bcafes\b",
        r"\bcafés\b",
        r"\brestaurant\b",
        r"\brestaurants\b",
        r"\bcoworking\b",
        r"\bco-working\b",
        r"\blibrary\b",
        r"\blibraries\b",
        r"\bhotel\b",
        r"\bhotels\b",
        r"\bpark\b",
        r"\bparks\b",
        r"\bhospital\b",
        r"\bhospitals\b",
        r"\bplaces to eat\b",
        r"\bplaces to study\b",
        r"\bplaces to work\b",
        r"\bplaces to stay\b",
        r"\bplaces to visit\b",
        r"\bplaces to go\b",
        r"\bnearby\b",
        r"\bnear\b",
        r"\baround\b",
        r"\bclosest\b",
        r"\beateries\b",
        r"\beatery\b",
        r"\bdiner\b",
        r"\bdiners\b",
        r"\bbakery\b",
        r"\bbakeries\b",
        r"\bpub\b",
        r"\bpubs\b",
        r"\bbar\b",
        r"\bbars\b",
    ]
    if any(re.search(pattern, text) for pattern in local_patterns):
        return AgentMode.LOCAL

    # Explicit shopping keywords
    shopping_patterns = [
        r"\bbuy\b",
        r"\bpurchase\b",
        r"\bprice\b",
        r"\bprices\b",
        r"\bbudget\b",
        r"under\s*(?:₹|\$|rs\.?|inr|usd)\s*\d+",
        r"\bproduct\b",
        r"\bproducts\b",
        r"\blaptop\b",
        r"\blaptops\b",
        r"\bphone\b",
        r"\bphones\b",
        r"\bsmartphone\b",
        r"\bsmartphones\b",
        r"\bheadphones\b",
        r"\bearphones\b",
        r"\bearbuds\b",
        r"\bmonitor\b",
        r"\bmonitors\b",
        r"\bkeyboard\b",
        r"\bkeyboards\b",
        r"\bsmartwatch\b",
        r"\bcompare products\b",
        r"\bshopping\b",
        r"\bdiscount\b",
        r"\bdiscounts\b",
        r"\bdeal\b",
        r"\bdeals\b",
        r"\bwhere to buy\b",
        r"\bseller\b",
        r"\bmerchant\b",
        r"\boffer\b",
        r"\boffers\b",
    ]
    if any(re.search(pattern, text) for pattern in shopping_patterns):
        return AgentMode.SHOPPING

    return AgentMode.RESEARCH

