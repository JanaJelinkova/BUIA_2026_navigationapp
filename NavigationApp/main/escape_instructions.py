"""
Escape instructions mapping for different locations.
Each location maps to specific evacuation instructions.
"""

import random

ESCAPE_INSTRUCTIONS = {
    'ucebna': [
        'Opusťte učebnu a otočte se do leva, pokračujte rovně ke schodišti',
        'Vyjděte z učebny, dejte se vlevo a pokračujte směrem ke schodišti',
        'Ukončete pobyt v učebně, opusťte místnost a jděte vlevo ke schodišti'
    ],
    'chodba': [
        'Pokračujte rovně ke schodišti',
        'Následujte chodbu až ke schodišti',
        'Jděte po chodbě směrem k východu ke schodišti'
    ],
    'schodiste': [
        'Sejděte do přízemí',
        'Sjeďte po schodech dolů do přízemí',
        'Použijte schodiště k sestupu do přízemí'
    ],
    'turnikety': [
        'Odejděte skrz turnikety před budovu',
        'Projděte turnikety a pokračujte ven před budovu',
        'Opusťte budovu přes turnikety směrem ven'
    ],
    'venek': [
        'Jste v bezpečí, čekejte na pokyny učitele',
        'Zůstaňte venku na volném prostranství a vyčkejte další instrukce',
        'Přesuňte se na bezpečné místo venku a čekejte na pokyny'
    ]
}

# Display names for locations
LOCATION_NAMES = {
    'ucebna': 'Učebna',
    'chodba': 'Chodba',
    'schodiste': 'Schodiště',
    'turnikety': 'Turnikety (Přízemí)',
    'venek': 'Venek'
}

def get_instruction(location_key):
    """Get escape instruction for a given location key.

    Returns a random variation from the list of instructions for that key.
    """
    key = (location_key or '').lower()
    vals = ESCAPE_INSTRUCTIONS.get(key)
    if not vals:
        return 'Neznámá poloha - postupujte podle značek nouzových východů'
    return random.choice(vals)

def get_location_name(location_key):
    """Get display name for a location key."""
    return LOCATION_NAMES.get(location_key.lower(), location_key)

def get_all_locations():
    """Get all available locations with a representative instruction."""
    return {key: {'name': name, 'instruction': ESCAPE_INSTRUCTIONS.get(key, [''])[0]}
            for key, name in LOCATION_NAMES.items()}
