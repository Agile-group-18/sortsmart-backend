from app.data.items import ITEMS

def search_items(q: str):
    q = q.lower().strip() 

    if not q: 
        return []

    results = []
    """Loop through items, check matches, and return result."""
    for item in ITEMS:
        name_match = q in item["name"].lower()
        keyword_match = any(q in keyword.lower() for keyword in item["keywords"])
        category_match = q in item["category"].lower()

        if name_match or keyword_match or category_match:
            results.append(item)

    return results