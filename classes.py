import json
import re
import sqlite3
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Set, TYPE_CHECKING

try:  # Optional dependency – the script can operate without network scraping support.
    import requests  # type: ignore
    from bs4 import BeautifulSoup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - gracefully degrade when requests/bs4 are missing
    requests = None
    BeautifulSoup = None

if TYPE_CHECKING:  # pragma: no cover - help static type checkers without incurring a runtime dependency
    from bs4 import Tag  # type: ignore
else:
    Tag = Any  # type: ignore

def extract_level_from_text(text: str) -> Optional[int]:
    """Return the first integer found in the provided text."""

    match = re.search(r"(\d+)", text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def parse_spell_table(table: Tag) -> Mapping[int, Set[str]]:
    """Parse a spell progression table and return spells grouped by level.

    The parser is intentionally defensive so that it can cope with minor
    structural differences between class pages. A row is considered valid when
    the first column contains a level indicator and at least one of the
    remaining columns mentions spells (hyperlinks are preferred but plain text
    entries separated by commas are also supported).
    """

    rows = table.find_all("tr")
    if not rows:
        return {}

    header_cells = rows[0].find_all(["th", "td"])
    header_labels = [cell.get_text(" ", strip=True).lower() for cell in header_cells]
    if not header_labels:
        return {}

    if "level" not in header_labels[0]:
        return {}

    if not any("spell" in label for label in header_labels[1:]):
        return {}

    spells_by_level: MutableMapping[int, Set[str]] = defaultdict(set)
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        level_text = cells[0].get_text(" ", strip=True)
        level = extract_level_from_text(level_text)
        if level is None:
            continue

        found_spells: List[str] = []
        for cell in cells[1:]:
            link_spells = [a.get_text(strip=True) for a in cell.find_all("a") if a.get_text(strip=True)]
            if link_spells:
                found_spells.extend(link_spells)
                continue

            cell_text = cell.get_text(" ", strip=True)
            if cell_text:
                parts = [part.strip() for part in re.split(r",|/|\n", cell_text) if part.strip()]
                found_spells.extend(parts)

        for spell in found_spells:
            spells_by_level[level].add(spell)

    return {level: spells for level, spells in spells_by_level.items() if spells}


def fetch_class_spells(class_names: Iterable[str]) -> Dict[str, Dict[int, Set[str]]]:
    """Retrieve the spells learned by each class from the BG3 wiki.

    The function scrapes the https://bg3.wiki/wiki/Classes page and searches for
    spell progression tables that are scoped under headings matching a known
    class name. A best effort is made to gracefully handle structural changes.
    When the remote resource is not reachable (for example because the runtime
    does not have external network access) an empty mapping is returned so that
    the rest of the import pipeline can still run.
    """

    if requests is None or BeautifulSoup is None:
        print("Warning: skipping class spell scraping because requests/bs4 are not installed.")
        return {}

    try:
        response = requests.get(
            "https://bg3.wiki/wiki/Classes",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network best effort
        print(f"Warning: unable to fetch class spell data from the wiki: {exc}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    content_root = soup.find("div", id="mw-content-text")
    if not content_root:
        return {}

    known_classes = {name.strip().lower() for name in class_names}
    spells_by_class: Dict[str, Dict[int, Set[str]]] = {}
    current_class: Optional[str] = None

    for element in content_root.children:
        if getattr(element, "name", None) in {"h2", "h3", "h4"}:
            heading_text = element.get_text(" ", strip=True)
            key = heading_text.strip().lower()
            if key in known_classes:
                current_class = heading_text.strip()
                spells_by_class.setdefault(current_class, {})
            else:
                current_class = None
            continue

        if not current_class or getattr(element, "name", None) != "table":
            continue

        parsed_table = parse_spell_table(element)
        if not parsed_table:
            continue

        class_store = spells_by_class.setdefault(current_class, {})
        for level, spells in parsed_table.items():
            class_store.setdefault(level, set()).update(spells)

    # Remove classes for which no spells were discovered
    return {
        class_name: {level: spells for level, spells in sorted(levels.items())}
        for class_name, levels in spells_by_class.items()
        if any(levels.values())
    }


# Load the JSON from the updated file
with open('data/json/classes.json', 'r') as file:
    data = json.load(file)
    class_names = [class_entry['name'] for class_entry in data.get('classes', [])]


class_spells_mapping = fetch_class_spells(class_names)

# Connect to SQLite
conn = sqlite3.connect('data/databases/bg3_classes.db')
c = conn.cursor()

# Drop tables if they already exist
c.execute('DROP TABLE IF EXISTS Classes')
c.execute('DROP TABLE IF EXISTS Class_Progression')
c.execute('DROP TABLE IF EXISTS Subclasses')
c.execute('DROP TABLE IF EXISTS Subclasses_Features')
c.execute('DROP TABLE IF EXISTS Class_Spells_Learned')

# Create the tables
c.execute('''
CREATE TABLE Classes (
    name TEXT PRIMARY KEY,
    description TEXT,
    hit_points_at_level1 TEXT,
    hit_points_on_level_up TEXT,
    key_abilities TEXT,
    saving_throw_proficiencies TEXT,
    equipment_proficiencies TEXT,
    skill_proficiencies TEXT,
    spellcasting_ability TEXT,
    starting_equipment TEXT,
    image_path TEXT
)
''')

c.execute('''
CREATE TABLE Class_Progression (
    class_name TEXT,
    level INTEGER,
    proficiency_bonus TEXT,
    features TEXT,
    rage_charges INTEGER,
    invocations_known INTEGER,
    FOREIGN KEY(class_name) REFERENCES Classes(name)
)
''')

c.execute('''
CREATE TABLE Subclasses (
    class_name TEXT,
    name TEXT,
    description TEXT,
    image_path TEXT,
    FOREIGN KEY(class_name) REFERENCES Classes(name)
)
''')

c.execute('''
CREATE TABLE Subclasses_Features (
    subclass_name TEXT,
    level INTEGER,
    feature_name TEXT,
    feature_description TEXT,
    FOREIGN KEY(subclass_name) REFERENCES Subclasses(name)
)
''')

c.execute('''
CREATE TABLE Class_Spells_Learned (
    class_name TEXT,
    level INTEGER,
    spell_name TEXT,
    FOREIGN KEY(class_name) REFERENCES Classes(name)
)
''')

# Insert data into tables
for class_data in data['classes']:
    # Insert class data
    c.execute('''
    INSERT INTO Classes (name, description, hit_points_at_level1, hit_points_on_level_up, key_abilities,
                         saving_throw_proficiencies, equipment_proficiencies, skill_proficiencies, spellcasting_ability,
                         starting_equipment, image_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (class_data['name'], class_data['description'], class_data['hit_points_at_level1'],
          class_data['hit_points_on_level_up'], class_data['key_abilities'], class_data['saving_throw_proficiencies'],
          class_data['equipment_proficiencies'], class_data['skill_proficiencies'],
          class_data.get('spellcasting_ability', None),
          class_data['starting_equipment'], class_data.get('image_path', None)))

    class_name = class_data['name']

    # Insert class progression data
    progression_columns = [row[1] for row in c.execute('PRAGMA table_info(Class_Progression)')]
    desired_progression_columns = [
        'class_name',
        'level',
        'proficiency_bonus',
        'features',
        'rage_charges',
        'rage_damage',
        'cantrips_known',
        'spells_known',
        'spell_slots_1st',
        'spell_slots_2nd',
        'spell_slots_3rd',
        'spell_slots_4th',
        'spell_slots_5th',
        'spell_slots_6th',
        'sorcery_points',
        'sneak_attack_damage',
        'bardic_inspiration_charges',
        'channel_divinity_charges',
        'lay_on_hands_charges',
        'ki_points',
        'unarmoured_movement_bonus',
        'martial_arts_damage',
        'spell_slots_per_level',
        'invocations_known',
    ]

    for progression in class_data['class_progression']:
        progression_values = {
            'class_name': class_name,
            'level': progression['level'],
            'proficiency_bonus': progression['proficiency_bonus'],
            'features': progression['features'],
            'rage_charges': progression.get('rage_charges'),
            'rage_damage': progression.get('rage_damage'),
            'cantrips_known': progression.get('cantrips_known'),
            'spells_known': progression.get('spells_known'),
            'spell_slots_1st': progression.get('spell_slots_1st'),
            'spell_slots_2nd': progression.get('spell_slots_2nd'),
            'spell_slots_3rd': progression.get('spell_slots_3rd'),
            'spell_slots_4th': progression.get('spell_slots_4th'),
            'spell_slots_5th': progression.get('spell_slots_5th'),
            'spell_slots_6th': progression.get('spell_slots_6th'),
            'sorcery_points': progression.get('sorcery_points'),
            'sneak_attack_damage': progression.get('sneak_attack_damage'),
            'bardic_inspiration_charges': progression.get('bardic_inspiration_charges'),
            'channel_divinity_charges': progression.get('channel_divinity_charges'),
            'lay_on_hands_charges': progression.get('lay_on_hands_charges'),
            'ki_points': progression.get('ki_points'),
            'unarmoured_movement_bonus': progression.get('unarmoured_movement_bonus'),
            'martial_arts_damage': progression.get('martial_arts_damage'),
            'spell_slots_per_level': progression.get('spell_slots_per_level'),
            'invocations_known': progression.get('invocations_known'),
        }

        columns_to_insert = [
            column for column in desired_progression_columns if column in progression_columns
        ]
        placeholders = ', '.join(['?'] * len(columns_to_insert))
        column_clause = ', '.join(columns_to_insert)
        values = [progression_values[column] for column in columns_to_insert]

        c.execute(
            f'''
            INSERT INTO Class_Progression ({column_clause})
            VALUES ({placeholders})
            ''',
            values,
        )

        learned_spells = class_spells_mapping.get(class_name, {}).get(progression['level'], set())
        for spell_name in sorted(learned_spells):
            c.execute('''
            INSERT INTO Class_Spells_Learned (class_name, level, spell_name)
            VALUES (?, ?, ?)
            ''', (class_name, progression['level'], spell_name))

        learned_spells = class_spells_mapping.get(class_name, {}).get(progression['level'], set())
        for spell_name in sorted(learned_spells):
            c.execute('''
            INSERT INTO Class_Spells_Learned (class_name, level, spell_name)
            VALUES (?, ?, ?)
            ''', (class_name, progression['level'], spell_name))

    # Insert subclass data
    for subclass in class_data.get('subclasses', []):
        c.execute('''
        INSERT INTO Subclasses (class_name, name, description, image_path)
        VALUES (?, ?, ?, ?)
        ''', (class_name, subclass['name'], subclass['description'], subclass['image_path']))

        subclass_name = subclass['name']

        # Insert subclass features
        for feature in subclass['features']:
            c.execute('''
            INSERT INTO Subclasses_Features (subclass_name, level, feature_name, feature_description)
            VALUES (?, ?, ?, ?)
            ''', (subclass_name, feature['level'], feature['feature_name'], feature['feature_description']))

# Commit the changes
conn.commit()

# Close the connection
conn.close()
