import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from duckduckgo_search import DDGS

def search_web(query: str, max_results: int = 4) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for r in results:
                print(r.get("body"))
    except Exception as e:
        print("ERROR:", e)

search_web("what is the weather in tokyo")
