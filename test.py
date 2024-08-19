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
    weight_kg REAL,
    weight_lb REAL,
    price INTEGER,
    enchantment INTEGER,
    type TEXT,
    range REAL,
    attributes TEXT,
    uid TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Damage (
    damage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    weapon_id TEXT,
    damage_dice TEXT,
    damage_bonus INTEGER,
    damage_total_range TEXT,
    modifier TEXT,
    damage_type TEXT,
    damage_source TEXT,
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


# Fonction personnalisée pour rechercher un élément contenant un certain texte dans une balise spécifique
def find_name_by_text(soup, name, text):
    for balise in soup.find_all(name):
        if text in balise.get_text(strip=True):
            return balise
    return None


# Fonction pour extraire les attributs entre Enchantment et Melee/Range
def extract_attributes(properties):
    enchantment_element = find_name_by_text(properties, 'dd', 'Enchantment:')
    if enchantment_element:
        attributes = []
        next_element = enchantment_element.find_next_sibling('dd')
        while next_element and not any(
                keyword in next_element.get_text(strip=True) for keyword in ['Melee:', 'Range:']):
            # Extrait le texte de l'attribut
            attribute_text = next_element.get_text(strip=True, separator=" ")
            attributes.append(attribute_text)
            next_element = next_element.find_next_sibling('dd')
        return ', '.join(attributes)
    return None


weapons_url = "https://bg3.wiki/wiki/Sethan"

# Requête pour obtenir le contenu de la page
response = requests.get(weapons_url)
# Lecture du contenu HTML
soup = BeautifulSoup(response.content, 'html.parser')

# Extraction des données
weapon_name = soup.find('h1', class_='firstHeading').get_text(strip=True, separator=" ")

description_tag = soup.find('div', class_='bg3wiki-blockquote-text')
description = description_tag.get_text(strip=True, separator=" ") if description_tag else None

properties = soup.find('div', class_='bg3wiki-property-list')

# Initialisation de la variable attributes
attributes = extract_attributes(properties)

# Utilisation de la fonction personnalisée pour rechercher les propriétés dans des <dd>
rarity_dd = find_name_by_text(properties, 'dd', 'Rarity:')
rarity = rarity_dd.get_text(strip=True, separator=" ").split(':')[-1].strip() if rarity_dd else 'Unknown'

enchantment_dd = find_name_by_text(properties, 'dd', 'Enchantment:')
enchantment = int(enchantment_dd.get_text(strip=True, separator=" ").split('+')[-1].strip()) if enchantment_dd else 0

# Poids
weight_element = find_name_by_text(properties, 'dd', 'Weight:')
if weight_element:
    weight = weight_element.get_text(strip=True, separator=" ").split(':')[-1].strip().split('/')
    weight_kg = float(weight[0].strip().split(' ')[0].replace('kg', '').strip())
    weight_lb = float(weight[1].strip().split(' ')[0].replace('lb', '').strip())
else:
    weight_kg = weight_lb = 0.0

# Traitement du prix
price_element = find_name_by_text(properties, 'dd', 'Price:')
if price_element:
    price_text = price_element.get_text(strip=True, separator=" ").split(':')[-1].strip().replace('gp', '').strip()

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

# Extraction du UID et du UUID
uuid_dd = find_name_by_text(properties, 'dd', 'UUID')
if uuid_dd:
    tt_elements = uuid_dd.find_all('tt')
    uid = tt_elements[0].get_text(strip=True, separator=" ") if len(tt_elements) > 0 else 'Unknown UID'
    weapon_id = tt_elements[1].get_text(strip=True, separator=" ") if len(tt_elements) > 1 else 'Unknown UUID'
else:
    uid = 'Unknown UID'
    weapon_id = 'Unknown UUID'

# Insertion des données dans la table Weapons
cursor.execute('''
INSERT INTO Weapons (weapon_id, name, rarity, description, weight_kg, weight_lb, price, enchantment, type, range, attributes, uid)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (weapon_id, weapon_name, rarity, description, weight_kg, weight_lb, price_gp, enchantment, 'Dagger', 1.5,
      attributes, uid))

# Extraction des informations de dégâts
damage_dl = find_name_by_text(properties, 'dl', 'Damage')
if damage_dl:
    # Extrait le dé d'origine (ex: '1d4')
    damage_dice = damage_dl.find('div', class_='bg3wiki-info-blob').get_text(strip=True).split(' ')[0]

    # Extrait le bonus de dégâts (ex: '+1')
    damage_bonus_text = damage_dl.find('div', class_='bg3wiki-info-blob').get_text(strip=True)
    damage_bonus = int(damage_bonus_text.split('+')[1].split('(')[0].strip()) if '+' in damage_bonus_text else 0

    # Extrait le range total (ex: '2~5')
    damage_total_range = damage_bonus_text.split('(')[-1].split(')')[0] if '(' in damage_bonus_text else ''

    # Extrait le modificateur de dégâts (ex: 'Strength or Dexterity modifier')
    modifier = damage_dl.find('a', href='/wiki/Damage_Roll#Modifiers').get_text(strip=True)

    # Extrait le type de dégâts
    damage_type = damage_dl.find('a', title='Damage Types').find_next("a").get_text(strip=True)

    # Insertion des informations de dégâts dans la table Damage
    cursor.execute('''
    INSERT INTO Damage (weapon_id, damage_dice, damage_bonus, damage_total_range, modifier, damage_type, damage_source)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (weapon_id, damage_dice, damage_bonus, damage_total_range, modifier, damage_type, 'normal'))

# Vérifier s'il y a des "Extra damage"
extra_damage_section = find_name_by_text(properties, 'dl', 'Extra damage')
if extra_damage_section:
    extra_damage_dl_list = extra_damage_section.find_next('dd').find_all_next('dd', limit=2)
    for extra_damage_dl in extra_damage_dl_list:
        # Extrait le dé d'origine (ex: '1d4')
        extra_damage_dice = extra_damage_dl.find('div', class_='bg3wiki-info-blob').get_text(strip=True).split(' ')[0]

        # Extrait le bonus de dégâts (ex: '+1')
        extra_damage_bonus_text = extra_damage_dl.find('div', class_='bg3wiki-info-blob').get_text(strip=True)
        extra_damage_bonus = int(
            extra_damage_bonus_text.split('+')[1].split('(')[0].strip()) if '+' in extra_damage_bonus_text else 0

        # Extrait le range total (ex: '2~5')
        extra_damage_total_range = extra_damage_bonus_text.split('(')[-1].split(')')[
            0] if '(' in extra_damage_bonus_text else ''

        # Extrait le type de dégâts
        extra_damage_type = extra_damage_dl.find('a', title='Damage Types').find_next("a").get_text(strip=True)

        # Insertion des informations de dégâts supplémentaires dans la table Damage
        cursor.execute('''
        INSERT INTO Damage (weapon_id, damage_dice, damage_bonus, damage_total_range, modifier, damage_type, damage_source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
        weapon_id, extra_damage_dice, extra_damage_bonus, extra_damage_total_range, None, extra_damage_type, 'extra'))

# Capacités spéciales
special_abilities_section = soup.find("h3", string=lambda x: x and 'Special' in x)
if special_abilities_section:
    spe

# Lieux de l'arme
location_section = soup.find("h2", string=lambda x: x and 'Where to find' in x)
location = location_section.find_next('li') if location_section else None
if location:
    location_description = location.get_text(strip=True, separator=" ")
    cursor.execute('''
    INSERT INTO Weapon_Locations (weapon_id, location_description)
    VALUES (?, ?)
    ''', (weapon_id, location_description))

# Extraction des notes
notes_section = soup.find("h2", string=lambda x: x and 'Notes' in x)
if notes_section:
    notes_list = notes_section.find_next('div', class_='bg3wiki-tooltip-box').find_all('li')
    for note in notes_list:
        note_content = note.get_text(strip=True, separator=" ")
        cursor.execute('''
        INSERT INTO Notes (weapon_id, note_content)
        VALUES (?, ?)
        ''', (weapon_id, note_content))

# Commit des changements
conn.commit()

# Fermeture de la connexion à la base de données
conn.close()

print("Les données ont été extraites et stockées dans la base de données avec succès.")
