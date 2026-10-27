"""Built-in nutrition coach: turns a message like "I weigh 80 kg and want to lose 5 kg in a month" into a
calorie / protein target with a safe pace and a simple meal split. Pure rules, no external service, so it
works without any API key. General guidance only, not medical advice."""
import re

KCAL_PER_KG = 7700
DAY_WORDS = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}
UNIT_DAYS = {'day': 1, 'week': 7, 'month': 30}

INTENT_RE = re.compile(
    r"\b(diet plan|diet chart|meal plan|eating plan|nutrition plan|lose weight|weight loss|fat loss|lose fat|"
    r"reduce weight|reduce (?:my )?weight|lose \d|reduce \d|drop \d|cut \d|gain weight|weight gain|put on weight|"
    r"bulk(?:ing)?|get lean|get fit|slim down|burn fat|how many calories (?:should|do) i|calories do i need|"
    r"calorie (?:target|deficit|surplus|need)|how much protein (?:should|do) i|what should i eat|gain \d|"
    r"want to (?:lose|gain|weigh)|get to \d+(?:\.\d+)?\s*(?:kgs?|kilos?|lbs?|pounds?))\b",
    re.I)

NUM = r'(\d+(?:\.\d+)?)'
WEIGHT_RE = re.compile(NUM + r'\s*(kgs?|kilograms?|kilos?|lbs?|pounds?)\b', re.I)
TIME_RE = re.compile(r'\b(\d+(?:\.\d+)?|an?|one|two|three|four|five|six)\s+(day|week|month)s?\b', re.I)
HEIGHT_RE = re.compile(r'\b(\d{3})\s*cm\b', re.I)
AGE_RE = re.compile(r'\b(\d{2})\s*(?:years?|yrs?|y/?o)\b|\bage[d]?\s*(?:is\s*)?(\d{2})\b', re.I)
GOAL_VERB_RE = re.compile(r'(lose|loss|reduce|drop|cut|shed|burn|gain|put on|add|build)\b[^.]*$', re.I)
GAIN_VERB_RE = re.compile(r'(gain|put on|add|build)\b[^.]*$', re.I)
TARGET_RE = re.compile(r'(to be|reach|get to|target|goal weight|down to|up to|become)\b[^.]*$', re.I)


def wants_plan(message):
    return bool(INTENT_RE.search(message))


def _kg(value, unit):
    value = float(value)
    return value * 0.45359 if unit.lower().startswith(('lb', 'pound')) else value


def parse(message):
    """Extract what the user told us. Missing values are None."""
    info = {'weight': None, 'change': None, 'direction': None, 'days': None,
            'height': None, 'age': None, 'sex': None}
    target_weight = None
    for m in WEIGHT_RE.finditer(message):
        kg = _kg(m.group(1), m.group(2))
        context = message[max(0, m.start() - 35):m.start()]
        if TARGET_RE.search(context) and not GOAL_VERB_RE.search(context):
            target_weight = kg
        elif GOAL_VERB_RE.search(context):
            info['change'] = kg
            info['direction'] = 'gain' if GAIN_VERB_RE.search(context) else 'loss'
        elif info['weight'] is None:
            info['weight'] = kg
    if info['change'] is None and target_weight and info['weight'] and target_weight != info['weight']:
        info['change'] = abs(info['weight'] - target_weight)
        info['direction'] = 'loss' if target_weight < info['weight'] else 'gain'

    t = TIME_RE.search(message)
    if t:
        raw = t.group(1).lower()
        qty = float(raw) if raw.replace('.', '', 1).isdigit() else DAY_WORDS[raw]
        info['days'] = max(1, round(qty * UNIT_DAYS[t.group(2).lower()]))

    h = HEIGHT_RE.search(message)
    if h and 120 <= int(h.group(1)) <= 230:
        info['height'] = int(h.group(1))
    a = AGE_RE.search(message)
    if a:
        age = int(a.group(1) or a.group(2))
        info['age'] = age if 14 <= age <= 90 else None
    low = message.lower()
    if re.search(r'\b(female|woman|girl|lady)\b', low):
        info['sex'] = 'female'
    elif re.search(r'\b(male|man|boy|guy)\b', low):
        info['sex'] = 'male'
    return info


def _round10(n):
    return int(round(n / 10.0) * 10)


def _maintenance(info):
    weight = info['weight']
    if info['height'] and info['age'] and info['sex']:
        bmr = 10 * weight + 6.25 * info['height'] - 5 * info['age'] + (5 if info['sex'] == 'male' else -161)
        return _round10(bmr * 1.45), 'worked out from your height, age, sex and weight with light activity'
    return _round10(weight * 31), 'estimated at about 31 kcal per kg for a moderately active person'


ASK_FOR_DETAILS = (
    "I can build you a starting plan. Tell me:\n"
    "- your weight (e.g. 80 kg)\n"
    "- how much you want to lose or gain and in how long (e.g. lose 5 kg in 2 months)\n"
    "- optional, for a more accurate estimate: height, age and male/female\n\n"
    'Example: "I weigh 80 kg, 175 cm, 25 years old, male, and want to lose 5 kg in 2 months".')

DISCLAIMER = ('This is general guidance, not medical advice. If you have a medical condition, are pregnant, '
              'or are under 18, check with a doctor or dietitian first.')


def build_reply(message):
    """Return the coach's reply for a diet / calorie / protein question (never None)."""
    info = parse(message)
    if info['weight'] is None:
        return ASK_FOR_DETAILS

    weight = info['weight']
    maint, basis = _maintenance(info)
    floor = 1200 if info['sex'] == 'female' else 1500
    change, direction, days = info['change'], info['direction'], info['days']
    lines = []

    if change and direction == 'loss':
        cap = min(1000, 0.01 * weight * KCAL_PER_KG / 7)          # about 1 % of body weight per week
        required = change * KCAL_PER_KG / days if days else 500
        deficit = min(required, cap)
        target = _round10(max(maint - deficit, floor))
        deficit = maint - target
        week_pace = deficit * 7 / KCAL_PER_KG
        weeks_needed = change * KCAL_PER_KG / deficit / 7
        goal_line = f'losing {change:g} kg' + (f' in {_span(days)}' if days else '')
        lines.append(f'Here is a starting plan for {goal_line} at {weight:g} kg.')
        pace = [f'At {target:,} kcal/day you would lose about {week_pace:.1f} kg per week.']
        if days and required > cap + 1:
            pace.insert(0, f'{change:g} kg in {_span(days)} is about {change / days * 7:.1f} kg per week, faster '
                           f'than the roughly {cap * 7 / KCAL_PER_KG:.1f} kg per week usually considered safe, so '
                           f'I have set a safer pace.')
            pace.append(f'Reaching {change:g} kg this way takes about {weeks_needed:.0f} weeks.')
        elif days:
            pace.append(f'That gets you to {change:g} kg in about {weeks_needed:.0f} weeks.')
        protein_g = 1.8 * weight
    elif change and direction == 'gain':
        surplus = min(change * KCAL_PER_KG / days if days else 350, 500)
        target = _round10(maint + surplus)
        surplus = target - maint
        week_pace = surplus * 7 / KCAL_PER_KG
        weeks_needed = change * KCAL_PER_KG / surplus / 7
        goal_line = f'gaining {change:g} kg' + (f' in {_span(days)}' if days else '')
        lines.append(f'Here is a starting plan for {goal_line} at {weight:g} kg.')
        pace = [f'At {target:,} kcal/day you would gain about {week_pace:.2f} kg per week '
                f'(roughly {weeks_needed:.0f} weeks for {change:g} kg). Gaining slowly keeps most of it as muscle.']
        protein_g = 1.8 * weight
    else:
        target = maint
        lines.append(f'At {weight:g} kg here is a starting point.')
        pace = [f'To lose weight eat about 500 kcal below maintenance ({maint - 500:,} kcal), roughly 0.5 kg per '
                f'week. To gain, eat about 300 kcal above ({maint + 300:,} kcal). Tell me a goal such as '
                f'"lose 5 kg in 2 months" for a tailored plan.']
        protein_g = 1.6 * weight

    target = _round10(target)
    protein = round(protein_g)
    fat = round(target * 0.25 / 9)
    carbs = max(0, round((target - protein * 4 - fat * 9) / 4))

    lines += [
        '',
        f'Maintenance: about {maint:,} kcal/day ({basis}).',
        f'Daily target: {target:,} kcal',
        f'Protein {protein} g · Carbs {carbs} g · Fat {fat} g',
        '',
        *pace,
        '',
        'Meal split',
        f'- Breakfast {_round10(target * .25):,} kcal, ~{round(protein * .25)} g protein',
        f'- Lunch {_round10(target * .30):,} kcal, ~{round(protein * .30)} g protein',
        f'- Dinner {_round10(target * .30):,} kcal, ~{round(protein * .30)} g protein',
        f'- Snacks {_round10(target * .15):,} kcal, ~{round(protein * .15)} g protein',
        '',
        'Habits that make it work',
        '- Build meals around a protein source (eggs, chicken, fish, paneer, dal, curd) plus vegetables.',
        '- Strength train 3 to 4 times a week and walk 7,000 to 10,000 steps a day.',
        '- Sleep 7 to 9 hours and drink water through the day.',
        '',
        f'Put it into KILO: open the Goals page and set daily calories to {target:,} and protein to {protein} g, '
        f'then log your meals and workouts so the Today page tracks your progress.',
        '',
        DISCLAIMER,
    ]
    return '\n'.join(lines)


def _span(days):
    if days % 30 == 0:
        n = days // 30
        return f'{n} month' + ('s' if n != 1 else '')
    if days % 7 == 0:
        n = days // 7
        return f'{n} week' + ('s' if n != 1 else '')
    return f'{days} days'
