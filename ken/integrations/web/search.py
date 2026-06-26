import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from duckduckgo_search import DDGS

def search_web(query: str, max_results: int = 4) -> str:
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            if not results:
                return ""
            
            formatted = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                formatted.append(f"Title: {title}\nSummary: {body}")
                
            return "\n\n---\n\n".join(formatted)
    except Exception as e:
        return f"Search failed: {e}"
