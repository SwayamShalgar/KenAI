import re

queries = [
    "what is the weather in tokyo",
    "weather for london",
    "weather like in new york",
    "weather paris",
    "what is the weather like in tokyo?",
    "weather in san francisco"
]

for q in queries:
    m = re.match(r"^(?:what is the )?weather(?: like)?(?: in| for)?\s+(.+)$", q)
    if m:
        print(f"MATCH: '{q}' -> '{m.group(1).strip().rstrip('?')}'")
    else:
        print(f"NO MATCH: '{q}'")

