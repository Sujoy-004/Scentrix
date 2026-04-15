
filename = r'c:\Users\KIIT0001\Downloads\Telegram Desktop\Scentrix\backend\app\routers\fragrances.py'
with open(filename, encoding='utf-8') as f:
    content = f.read()

part1 = content.split('@router.get("/{fragrance_id}", response_model=FragranceDetail)')[0]
rest = '@router.get("/{fragrance_id}", response_model=FragranceDetail)' + content.split('@router.get("/{fragrance_id}", response_model=FragranceDetail)')[1]

get_detail_str = rest.split('@router.get("/search", response_model=List[FragranceSearchResult])')[0]
rest2 = '@router.get("/search", response_model=List[FragranceSearchResult])' + rest.split('@router.get("/search", response_model=List[FragranceSearchResult])')[1]

search_str = rest2.split('@router.get("/recommend/metrics/weekly", response_model=RecommendationWeeklyMetrics)')[0]
tail = '@router.get("/recommend/metrics/weekly", response_model=RecommendationWeeklyMetrics)' + rest2.split('@router.get("/recommend/metrics/weekly", response_model=RecommendationWeeklyMetrics)')[1]

new_content = part1 + search_str + get_detail_str + tail

with open(filename, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Swapped endpoints successfully.')
