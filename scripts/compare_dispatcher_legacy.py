"""Compare Phase 8 dispatcher vs legacy HybridRecommender for all 5 states."""
import json, sys, os, subprocess, time, urllib.request, urllib.error
from collections import Counter

API_BASE = "http://localhost:8000"

# Real fragrance IDs from the catalog
FRAG_IDS = [
    "frag_mugler_alien_2005", "frag_mugler_angel_1992",
    "frag_dolce-gabbana_light-blue_2001", "frag_chanel_coco-mademoiselle_2001",
    "frag_lancome_la-vie-est-belle_2012", "frag_tom-ford_black-orchid_2006",
    "frag_yves-saint-laurent_black-opium_2014", "frag_dior_hypnotic-poison_1998",
    "frag_dior_j-adore_1999", "frag_dior_sauvage_2015",
    "frag_tom-ford_tobacco-vanille_2007", "frag_hermes_terre-d-hermes_2006",
    "frag_versace_crystal-noir_2004", "frag_versace_eros_2012",
    "frag_calvin-klein_euphoria_2005",
    "frag_maison-francis-kurkdjian_baccarat-rouge-540_2015",
    "frag_versace_bright-crystal_2006", "frag_chloe_chloe-eau-de-parfum_2008",
    "frag_creed_aventus_2010", "frag_yves-saint-laurent_la-nuit-de-l-homme_2009",
    "frag_prada_candy_2011", "frag_giorgio-armani_si_2013",
]

TEST_INPUTS = {
    0: {"ratings": [], "quiz_confidence": None,
        "label": "State 0: Anonymous — empty ratings, no quiz"},
    1: {"ratings": [], "quiz_confidence": {"citrus": 0.8, "woody": 0.6, "vanilla": 0.4, "floral": 0.3},
        "label": "State 1: Quiz User — empty ratings + quiz_confidence"},
    2: {"ratings": [{"fragrance_id": FRAG_IDS[0], "rating": 4.5}, {"fragrance_id": FRAG_IDS[2], "rating": 3.0}],
        "quiz_confidence": None,
        "label": "State 2: Cold — 2 ratings"},
    3: {"ratings": [{"fragrance_id": FRAG_IDS[i], "rating": 3.0 + (i % 2)} for i in range(6)],
        "quiz_confidence": None,
        "label": "State 3: Warm — 6 ratings"},
    4: {"ratings": [{"fragrance_id": FRAG_IDS[i % len(FRAG_IDS)], "rating": 2.0 + (i % 4)} for i in range(22)],
        "quiz_confidence": None,
        "label": "State 4: Mature — 22 ratings"},
}

def post_guest(ratings, quiz_confidence=None):
    body = {"ratings": ratings}
    if quiz_confidence is not None:
        body["quiz_confidence"] = quiz_confidence
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API_BASE}/recommendations/guest", data=data,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def analyze_response(response, label):
    if "error" in response:
        print(f"  ERROR: {response['error']}")
        return None
    items = response.get("data", [])
    if not items:
        print(f"  EMPTY — no items returned")
        return None
    sources = Counter(item.get("source", "unknown") for item in items)
    match_scores = [item.get("match_score", 0) for item in items]
    unique_ids = set(item["id"] for item in items)
    return {
        "count": len(items),
        "sources": dict(sources),
        "match_score_min": min(match_scores),
        "match_score_max": max(match_scores),
        "match_score_mean": sum(match_scores) / len(match_scores),
        "unique_ids": len(unique_ids),
        "top5_ids": [item["id"] for item in items[:5]],
    }

def set_dispatcher_flag(enabled):
    """Set PHASE8_DISPATCHER_ENABLED in docker-compose and restart backend."""
    flag = "true" if enabled else "false"
    print(f"\n{'='*60}")
    print(f"Setting PHASE8_DISPATCHER_ENABLED={flag}, restarting backend...")
    print(f"{'='*60}")
    os.environ["PHASE8_DISPATCHER_ENABLED"] = flag
    # Stop backend
    subprocess.run(["docker", "compose", "stop", "backend"],
                   capture_output=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    # Remove backend container so env var takes effect
    subprocess.run(["docker", "compose", "rm", "-f", "backend"],
                   capture_output=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    # Start backend with env var
    env = os.environ.copy()
    env["PHASE8_DISPATCHER_ENABLED"] = flag
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "--no-deps", "backend"],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env
    )
    print(result.stdout[-200:] if len(result.stdout) > 200 else result.stdout)
    # Wait for backend to be healthy
    for attempt in range(30):
        try:
            with urllib.request.urlopen(f"{API_BASE}/health", timeout=5) as r:
                if r.status == 200:
                    print(f"Backend healthy after {attempt+1}s")
                    time.sleep(2)
                    return
        except:
            pass
        time.sleep(2)
    print("WARNING: Backend may not be healthy")

def main():
    results = {}
    for enabled in [True, False]:
        path = "dispatcher" if enabled else "legacy"
        set_dispatcher_flag(enabled)
        results[path] = {}
        for state, inp in TEST_INPUTS.items():
            print(f"\n--- {inp['label']} [{path}] ---")
            response = post_guest(inp["ratings"], inp["quiz_confidence"])
            analysis = analyze_response(response, inp["label"])
            results[path][state] = analysis
            if analysis:
                print(f"  Items: {analysis['count']}")
                print(f"  Sources: {analysis['sources']}")
                print(f"  Match scores: {analysis['match_score_min']:.1f}–{analysis['match_score_max']:.1f} (avg {analysis['match_score_mean']:.1f})")
                print(f"  Unique IDs: {analysis['unique_ids']}")
                print(f"  Top 5: {analysis['top5_ids']}")
            print()

    # Restore dispatcher
    set_dispatcher_flag(True)

    # Print comparison table
    print("\n" + "="*70)
    print("COMPARISON: DISPATCHER vs LEGACY")
    print("="*70)
    print(f"{'State':<10} {'Metric':<20} {'Dispatcher':<25} {'Legacy':<25}")
    print("-"*80)
    for state in sorted(TEST_INPUTS.keys()):
        d = results.get("dispatcher", {}).get(state)
        l = results.get("legacy", {}).get(state)
        if not d or not l:
            print(f"{state:<10} {'ERROR':<20} {'N/A':<25} {'N/A':<25}")
            continue
        print(f"{state:<10} {'item_count':<20} {d['count']:<25} {l['count']:<25}")
        print(f"{state:<10} {'unique_ids':<20} {d['unique_ids']:<25} {l['unique_ids']:<25}")
        print(f"{state:<10} {'match_score_mean':<20} {d['match_score_mean']:<25.2f} {l['match_score_mean']:<25.2f}")
        # Jaccard overlap
        d_top10 = set(d['top5_ids'])
        l_top10 = set(l['top5_ids'])
        overlap = d_top10 & l_top10
        jaccard = len(overlap) / len(d_top10 | l_top10) if (d_top10 | l_top10) else 0
        print(f"{state:<10} {'top5_jaccard':<20} {jaccard:<25.2f} {'':<25}")
        # Source comparison
        d_src = ', '.join([f'{k}={v}' for k, v in sorted(d['sources'].items())])
        l_src = ', '.join([f'{k}={v}' for k, v in sorted(l['sources'].items())])
        print(f"{state:<10} {'sources':<20} {d_src:<25} {l_src:<25}")
        print("-"*80)

    # Summary verdict
    print("\nSUMMARY VERDICT:")
    for state in sorted(TEST_INPUTS.keys()):
        d = results.get("dispatcher", {}).get(state)
        l = results.get("legacy", {}).get(state)
        if not d or not l:
            print(f"  State {state}: INCOMPLETE")
            continue
        same_count = d['count'] == l['count']
        d_top10 = set(d['top5_ids'])
        l_top10 = set(l['top5_ids'])
        overlap = len(d_top10 & l_top10)
        jaccard = overlap / len(d_top10 | l_top10) if (d_top10 | l_top10) else 0
        verdict = "IDENTICAL" if (same_count and jaccard >= 0.8) else \
                  "SIMILAR" if (same_count and jaccard >= 0.4) else \
                  "DIFFERENT"
        print(f"  State {state}: {verdict} (counts_match={same_count}, top5_overlap={overlap}/10, jaccard={jaccard:.2f})")

    return results

if __name__ == "__main__":
    main()
