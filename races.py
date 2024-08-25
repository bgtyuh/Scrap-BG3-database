import json
import sqlite3

# Charger le JSON depuis le fichier
with open('data/json/races.json', 'r') as file:
    data = json.load(file)

# Connexion à SQLite
conn = sqlite3.connect('data/databases/bg3_races.db')
c = conn.cursor()

# Création des tables
c.execute('''
CREATE TABLE races (
    name TEXT PRIMARY KEY,
    description TEXT,
    base_speed TEXT,
    size TEXT,
    image_url TEXT
)
''')

c.execute('''
CREATE TABLE racial_features (
    race_name TEXT,
    name TEXT,
    description TEXT,
    FOREIGN KEY(race_name) REFERENCES races(name)
)
''')

c.execute('''
CREATE TABLE subraces (
    race_name TEXT,
    name TEXT,
    description TEXT,
    FOREIGN KEY(race_name) REFERENCES races(name)
)
''')

c.execute('''
CREATE TABLE subrace_features (
    subrace_name TEXT,
    name TEXT,
    description TEXT,
    FOREIGN KEY(subrace_name) REFERENCES subraces(name)
)
''')

c.execute('''
CREATE TABLE spells (
    subrace_name TEXT,
    name TEXT,
    level INTEGER,
    casting_stat TEXT,
    recharge_type TEXT,
    FOREIGN KEY(subrace_name) REFERENCES subraces(name)
)
''')

# Insérer les données
for race in data['races']:
    # Insérer la race
    c.execute('''
    INSERT INTO races (name, description, base_speed, size, image_url)
    VALUES (?, ?, ?, ?, ?)
    ''', (race['name'], race['description'], race['base_speed'], race['size'], race['image_url']))

    race_name = race['name']

    # Insérer les caractéristiques raciales
    for feature in race['racial_features']:
        c.execute('''
        INSERT INTO racial_features (race_name, name, description)
        VALUES (?, ?, ?)
        ''', (race_name, feature['name'], feature['description']))

    # Insérer les sous-races
    for subrace in race.get('subraces', []):
        c.execute('''
        INSERT INTO subraces (race_name, name, description)
        VALUES (?, ?, ?)
        ''', (race_name, subrace['name'], subrace['description']))

        subrace_name = subrace['name']

        # Insérer les caractéristiques des sous-races
        for feature in subrace['features']:
            c.execute('''
            INSERT INTO subrace_features (subrace_name, name, description)
            VALUES (?, ?, ?)
            ''', (subrace_name, feature['name'], feature['description']))

        # Insérer les sorts
        for spell in subrace.get('spells', []):
            c.execute('''
            INSERT INTO spells (subrace_name, name, level, casting_stat, recharge_type)
            VALUES (?, ?, ?, ?, ?)
            ''', (subrace_name, spell['name'], spell['level'], spell['casting_stat'], spell['recharge_type']))

# Sauvegarder (commit) les changements
conn.commit()

# Fermer la connexion
conn.close()
