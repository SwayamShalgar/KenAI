from ken.integrations.web.search import search_web
res = search_web("latest Python version")
print("Search Results: ", len(res) > 0)
