import os
import sqlite3
import requests
from bs4 import BeautifulSoup

# Connexion à la base de données SQLite (ou création si elle n'existe pas)
conn = sqlite3.connect('bg3_weapons.db')
cursor = conn.cursor()

# Suppression des tables si elles existent déjà pour garantir une base de données propre
cursor.execute('DROP TABLE IF EXISTS Weapons')
cursor.execute('DROP TABLE IF EXISTS Damage')
cursor.execute('DROP TABLE IF EXISTS Special_Abilities')
cursor.execute('DROP TABLE IF EXISTS Weapon_Actions')
cursor.execute('DROP TABLE IF EXISTS Weapon_Locations')
cursor.execute('DROP TABLE IF EXISTS Notes')

# Création des tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS Weapons (
    weapon_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    rarity TEXT,
    description TEXT,
    weight REAL,
    price INTEGER,
    enchantment INTEGER,
    type TEXT,
    range REAL,
    attributes TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Damage (
    damage_id TEXT PRIMARY KEY,
    weapon_id TEXT,
    damage_dice TEXT,
    damage_bonus INTEGER,
    damage_type TEXT,
    FOREIGN KEY(weapon_id) REFERENCES Weapons(weapon_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Special_Abilities (
    ability_id INTEGER PRIMARY KEY AUTOINCREMENT,
    weapon_id TEXT,
    name TEXT,
    description TEXT,
    FOREIGN KEY(weapon_id) REFERENCES Weapons(weapon_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Weapon_Actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    weapon_id TEXT,
    name TEXT,
    description TEXT,
    FOREIGN KEY(weapon_id) REFERENCES Weapons(weapon_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Weapon_Locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    weapon_id TEXT,
    location_description TEXT,
    coordinates TEXT,
    FOREIGN KEY(weapon_id) REFERENCES Weapons(weapon_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    weapon_id TEXT,
    note_content TEXT,
    FOREIGN KEY(weapon_id) REFERENCES Weapons(weapon_id)
)
''')

# Validation des changements
conn.commit()

# Fonction personnalisée pour rechercher un élément contenant un certain texte dans un dd
def find_dd_by_text(soup, text):
    for dd in soup.find_all('dd'):
        if text in dd.get_text(strip=True):
            return dd
    return None

weapons_url = "https://bg3.wiki/wiki/Rhapsody"

# Requête pour obtenir le contenu de la page
response = requests.get(weapons_url)
# Lecture du fichier HTML

soup = BeautifulSoup(response.content, 'html.parser')

# Extraction des données
weapon_name = soup.find('h1', class_='firstHeading').get_text(strip=True, separator=" ")

description_tag = soup.find('div', class_='bg3wiki-blockquote-text')
description = description_tag.get_text(strip=True, separator=" ") if description_tag else None

properties = soup.find('div', class_='bg3wiki-property-list')

# Utilisation de la fonction personnalisée pour rechercher les propriétés dans des <dd>
rarity_dd = find_dd_by_text(properties, 'Rarity:')
rarity = rarity_dd.get_text(strip=True, separator=" ").split(':')[-1].strip() if rarity_dd else 'Unknown'

enchantment_dd = find_dd_by_text(properties, 'Enchantment:')
enchantment = int(enchantment_dd.get_text(strip=True, separator=" ").split('+')[-1].strip()) if enchantment_dd else 0

# Poids
weight_element = find_dd_by_text(properties, 'Weight:')
if weight_element:
    weight = weight_element.get_text(strip=True, separator=" ").split(':')[-1].strip().split('/')
    weight_kg = float(weight[0].strip().split(' ')[0].replace('kg', '').strip())
    weight_lb = float(weight[1].strip().split(' ')[0].replace('lb', '').strip())
else:
    weight_kg = weight_lb = 0.0

# Traitement du prix
price_element = find_dd_by_text(properties, 'Price:')
if price_element:
    price_text = price_element.get_text(strip=True, separator=" ").split(':')[-1].strip().replace('gp',
                                                                                                  '').strip()

    # Vérifier si le prix contient deux valeurs (par exemple, "800 / 1050 H Honour")
    if '/' in price_text:
        normal_price, honour_price = price_text.split('/')
        # Extraire uniquement la partie avant la barre (prix normal)
        price_gp = float(normal_price.strip())
    else:
        # Si une seule valeur est présente
        price_gp = float(price_text)
else:
    price_gp = 0.0  # Valeur par défaut si aucun prix n'est trouvé

uuid_dd = find_dd_by_text(properties, 'UUID')
uuid = uuid_dd.find('tt').get_text(strip=True, separator=" ") if uuid_dd else 'Unknown UUID'

# Détails des attributs
attributes = []
for prop in ['One-Handed', 'Finesse', 'Light', 'Thrown', 'Dippable']:
    if find_dd_by_text(properties, prop):
        attributes.append(prop.lower().replace(' ', '_'))

# Extraction des informations de dégâts
damage_dd = find_dd_by_text(properties, 'Damage')
if damage_dd:
    damage_text = damage_dd.get_text(strip=True, separator=" ").split(':')[-1].strip()
    damage_parts = damage_text.split(' ')
    damage_dice = damage_parts[0]  # Ex: '1d4'
    damage_type = damage_parts[1] if len(damage_parts) > 1 else None  # Ex: 'Piercing'
    damage_bonus = enchantment  # On utilise l'enchantement comme bonus de dégâts si applicable
else:
    damage_dice = None
    damage_type = None
    damage_bonus = 0

# Insertion des données dans la table Weapons
cursor.execute('''
INSERT INTO Weapons (weapon_id, name, rarity, description, weight, price, enchantment, type, range, attributes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (uuid, weapon_name, rarity, description, weight_kg, price_gp, enchantment, 'Dagger', 1.5, ','.join(attributes)))

cursor.execute('''
INSERT INTO Damage (damage_id, weapon_id, damage_dice, damage_bonus, damage_type)
VALUES (?, ?, ?, ?, ?)
''', (uuid + '-damage', uuid, damage_dice, damage_bonus, damage_type))

# Capacités spéciales
special_abilities_section = soup.find("h2", string=lambda x: x and 'Special' in x)
special_abilities = special_abilities_section.find_next('div', class_='bg3wiki-tablelist') if special_abilities_section else None
if special_abilities:
    for li in special_abilities.find_all('li'):
        ability_name = li.find('dt').get_text(strip=True, separator=" ")
        ability_description = li.find('dd').get_text(strip=True, separator=" ")
        cursor.execute('''
        INSERT INTO Special_Abilities (weapon_id, name, description)
        VALUES (?, ?, ?)
        ''', (uuid, ability_name, ability_description))

# Lieux de l'arme
location_section = soup.find("h2", string=lambda x: x and 'Where to find' in x)
location = location_section.find_next('li') if location_section else None
if location:
    location_description = location.get_text(strip=True, separator=" ")
    coordinates = location.find('span', class_='bg3wiki-coordinates').get_text(strip=True, separator=" ") if location else None
    cursor.execute('''
    INSERT INTO Weapon_Locations (weapon_id, location_description, coordinates)
    VALUES (?, ?, ?)
    ''', (uuid, location_description, coordinates))

# Notes
notes_section = soup.find("h2", string=lambda x: x and 'Notes' in x)
note = notes_section.find_next('li') if notes_section else None
if note:
    note_content = note.get_text(strip=True, separator=" ")
    cursor.execute('''
    INSERT INTO Notes (weapon_id, note_content)
    VALUES (?, ?)
    ''', (uuid, note_content))

# Commit des changements
conn.commit()

# Fermeture de la connexion à la base de données
conn.close()

print("Les données ont été extraites et stockées dans la base de données avec succès.")
