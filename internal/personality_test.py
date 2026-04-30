import requests
import json
import time

BASE_URL = "http://localhost:8000"

PERSONALITIES = [
    {
        "name": "The Deep Ocean (Aquatic)",
        "pos": ["sea water", "salt", "ozonic"],
        "neg": ["vanilla", "cinnamon"],
        "desc": "Loves the fresh, salty air. Hates anything heavy or sweet."
    },
    {
        "name": "The Ancient Forest (Woody)",
        "pos": ["cedar", "sandalwood", "vetiver"],
        "neg": ["lemon", "bergamot"],
        "desc": "Loves grounding, dry woods. Hates sharp citrus."
    },
    {
        "name": "The Dark Knight (Leather/Smoky)",
        "pos": ["leather", "smoke", "incense", "oud"],
        "neg": ["rose", "jasmine"],
        "desc": "Loves mysterious, burnt textures. Rejects delicate florals."
    },
    {
        "name": "The Confectioner (Gourmand)",
        "pos": ["vanilla", "caramel", "chocolate", "praline"],
        "neg": ["green", "basil", "mint"],
        "desc": "Loves edible, sugary scents. Hates herbal or green notes."
    },
    {
        "name": "The Sun God (Citrus)",
        "pos": ["lemon", "bergamot", "grapefruit", "lime"],
        "neg": ["musk", "leather", "tobacco"],
        "desc": "Loves high-energy brightness. Hates dark, animalic bases."
    },
    {
        "name": "The Royal Garden (Floral)",
        "pos": ["rose", "tuberose", "jasmine"],
        "neg": ["woody", "earthy"],
        "desc": "Loves blooming elegance. Rejects dry woods or soil."
    },
    {
        "name": "The Nomad (Spicy/Resinous)",
        "pos": ["cardamom", "cinnamon", "myrrh", "amber"],
        "neg": ["ozonic", "aquatic"],
        "desc": "Loves warm, traveling spice. Hates cold water vibes."
    },
    {
        "name": "The Minimalist (Clean/Musky)",
        "pos": ["white musk", "aldehydes", "cotton"],
        "neg": ["patchouli", "oud"],
        "desc": "Loves laundry-fresh simplicity. Hates complex, dirty bases."
    },
    {
        "name": "The Vintage Star (Powdery)",
        "pos": ["iris", "powdery", "violet"],
        "neg": ["tropical", "fruity"],
        "desc": "Loves classic, talc-like elegance. Hates modern syrupy fruit."
    },
    {
        "name": "The Earth Dweller (Earthy)",
        "pos": ["patchouli", "earthy", "moss"],
        "neg": ["candy", "sugar"],
        "desc": "Loves damp soil and mossy roots. Hates artificial sweetness."
    }
]

def find_fragment(query):
    try:
        r = requests.get(f"{BASE_URL}/fragrances/search?limit=1&q={query}")
        data = r.json()
        if data:
            return data[0]
    except:
        pass
    return None

def simulate():
    print(f"| Personality | Quiz Questions (Fragrance - Rating) | Recommendations Found (Top 5 Matches) |")
    print(f"| :--- | :--- | :--- |")
    
    for p in PERSONALITIES:
        ratings = []
        quiz_history = []
        
        # 1. Positives
        for node in p["pos"]:
            frag = find_fragment(node)
            if frag:
                ratings.append({"fragrance_id": frag["id"], "rating": 9.5})
                quiz_history.append(f"{frag['name']} ({frag['brand']}) - **9.5**")
        
        # 2. Negatives
        for node in p["neg"]:
            frag = find_fragment(node)
            if frag:
                ratings.append({"fragrance_id": frag["id"], "rating": 2.0})
                quiz_history.append(f"{frag['name']} ({frag['brand']}) - **2.0**")
            
        # Hit Guest API
        try:
            res = requests.post(f"{BASE_URL}/recommendations/guest", json={"ratings": ratings})
            rec_data = res.json()
            if rec_data:
                top_recs = [f"{r['name']} ({r['brand']}) [{r['match_score']}%]" for r in rec_data[:5]]
                
                # Format cells
                questions_cell = "<br> ".join(quiz_history)
                recs_cell = "<br> ".join(top_recs)
                print(f"| **{p['name']}** | {questions_cell} | {recs_cell} |")
        except Exception as e:
             print(f"| {p['name']} | Error | {str(e)} |")

simulate()
