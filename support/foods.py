"""Third-party API: Open Food Facts nutrition search, used by "Look up food" on the Meals page.

Time limit: FOOD_API_TIMEOUT_SECONDS (default 4 s). Fallback: a bundled table of common foods
(KILO-2001). Successful searches are cached for an hour and failures for a minute, so a slow service
never makes every lookup wait.
"""
import hashlib
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('support')

API_URL = 'https://search.openfoodfacts.org/search'
OK_TTL = 3600
FAIL_TTL = 60

# name -> (kcal, protein g, carbs g, fat g) per 100 g
FALLBACK_FOODS = {
    'Chicken breast, cooked': (165, 31, 0, 3.6),
    'White rice, cooked': (130, 2.7, 28, 0.3),
    'Brown rice, cooked': (112, 2.3, 23.5, 0.8),
    'Egg, boiled': (155, 13, 1.1, 11),
    'Oats, dry': (389, 16.9, 66, 6.9),
    'Banana': (89, 1.1, 23, 0.3),
    'Apple': (52, 0.3, 14, 0.2),
    'Whole milk': (61, 3.2, 4.8, 3.3),
    'Greek yogurt, plain': (97, 9, 3.9, 5),
    'Cheddar cheese': (403, 25, 1.3, 33),
    'Whole wheat bread': (247, 13, 41, 3.4),
    'Salmon, cooked': (208, 20, 0, 13),
    'Paneer': (296, 18, 3.6, 22),
    'Lentils, cooked': (116, 9, 20, 0.4),
    'Chickpeas, cooked': (164, 8.9, 27, 2.6),
    'Potato, boiled': (87, 1.9, 20, 0.1),
    'Sweet potato, baked': (90, 2, 21, 0.2),
    'Broccoli': (34, 2.8, 7, 0.4),
    'Almonds': (579, 21, 22, 50),
    'Peanut butter': (588, 25, 20, 50),
    'Olive oil': (884, 0, 0, 100),
    'Whey protein powder': (400, 80, 8, 6),
    'Dosa': (168, 3.9, 29, 3.7),
    'Idli': (130, 3.9, 27, 0.4),
    'Chapati': (297, 9.8, 46, 7.5),
}


def _fallback(query):
    q = query.lower()
    words = [w for w in q.split() if len(w) > 1]
    rows = [
        {'name': name, 'calories': kcal, 'protein': protein, 'carbs': carbs, 'fat': fat}
        for name, (kcal, protein, carbs, fat) in FALLBACK_FOODS.items()
        if q in name.lower() or any(w in name.lower() for w in words)
    ]
    return rows[:8]


def _num(value):
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return 0


def search_foods(query):
    """Return {'source': 'openfoodfacts' | 'fallback', 'results': [...per 100 g...]}. Never raises."""
    query = query.strip()[:60]
    key = 'food:' + hashlib.sha1(query.lower().encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            API_URL,
            params={'q': query, 'page_size': 12, 'fields': 'product_name,brands,nutriments'},
            headers={'User-Agent': 'KILO-fitness-tracker/1.0 (student project)'},
            timeout=settings.FOOD_API_TIMEOUT_SECONDS)
        response.raise_for_status()
        results = []
        for product in response.json().get('hits', []):
            nutr = product.get('nutriments') or {}
            name = (product.get('product_name') or '').strip()
            if not name or nutr.get('energy-kcal_100g') in (None, ''):
                continue
            brands = product.get('brands') or ''
            if isinstance(brands, str):                  # the API returns a list; older endpoints a CSV string
                brands = brands.split(',')
            brand = str(brands[0]).strip() if brands else ''
            results.append({
                'name': f'{name} ({brand})' if brand else name,
                'calories': _num(nutr.get('energy-kcal_100g')),
                'protein': _num(nutr.get('proteins_100g')),
                'carbs': _num(nutr.get('carbohydrates_100g')),
                'fat': _num(nutr.get('fat_100g')),
            })
        if not results:
            raise ValueError('no usable results')
        outcome, ttl = {'source': 'openfoodfacts', 'results': results[:6]}, OK_TTL
    except Exception as exc:  # noqa: BLE001 - timeouts, DNS, rate limit, bad JSON ...
        logger.warning('Food lookup failed (%s); using built-in foods (KILO-2001)', exc)
        outcome, ttl = {'source': 'fallback', 'results': _fallback(query)}, FAIL_TTL

    cache.set(key, outcome, ttl)
    return outcome
