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
    quote TEXT,
    weight_kg REAL,
    weight_lb REAL,
    price INTEGER,
    enchantment INTEGER,
    type TEXT,
    range_m REAL,
    range_f REAL,
    attributes TEXT,
    uid TEXT,
    image_path TEXT
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

# Créer le dossier pour les images si nécessaire
image_folder = 'weapon_images'
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

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

# Récupération de la liste des armes
list_url = "https://bg3.wiki/wiki/List_of_weapons"
response = requests.get(list_url)
soup = BeautifulSoup(response.content, 'html.parser')
set_of_url = set()
set_of_weapon_id = set()

# Itération sur chaque ligne du tableau pour récupérer les armes
rows = soup.select('table.wikitable tbody tr')
for row in rows:
    # Sélectionne la première cellule du tableau (contient le lien de l'arme)
    weapon_cell = row.find('td')
    if weapon_cell:
        weapon_link = weapon_cell.find('a', href=True)
        if weapon_link:
            weapon_url = "https://bg3.wiki" + weapon_link['href']

            if weapon_url in set_of_url:
                continue
            set_of_url.add(weapon_url)

            # Requête pour obtenir le contenu de la page de l'arme
            response_weapon = requests.get(weapon_url)
            soup_weapon = BeautifulSoup(response_weapon.content, 'html.parser')

            # Extraction des données
            weapon_name = soup_weapon.find('h1', class_='firstHeading').get_text(strip=True, separator=" ")
            print(weapon_name)

            description_tag = soup_weapon.find('meta', property='og:description')
            description = description_tag["content"] if description_tag else None

            quote_tag = soup_weapon.find('div', class_='bg3wiki-blockquote-text')
            quote = quote_tag.get_text() if quote_tag else None

            properties = soup_weapon.find('div', class_='bg3wiki-property-list')

            # Initialisation de la variable attributes
            attributes = extract_attributes(properties)

            # Type
            type_tag = find_name_by_text(properties, 'dt', 'Details')
            type_ = type_tag.find_next('img')['alt'] if type_tag else 'Unknown'

            # Range
            melee_tag = find_name_by_text(properties, 'dd', 'Melee:')
            if melee_tag:
                range_m = melee_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[0].replace('m', '').strip()
                range_f = melee_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[1].replace('ft', '').strip()
            else:
                range_tag = find_name_by_text(properties, 'dd', 'Range:')
                range_m = range_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[0].replace('m', '').strip()
                range_f = range_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[1].replace('ft', '').strip()

            # Utilisation de la fonction personnalisée pour rechercher les propriétés dans des <dd>
            rarity_dd = find_name_by_text(properties, 'dd', 'Rarity:')
            rarity = rarity_dd.get_text(strip=True, separator=" ").split(':')[-1].strip() if rarity_dd else 'Unknown'

            enchantment_dd = find_name_by_text(properties, 'dd', 'Enchantment:')
            enchantment = int(enchantment_dd.get_text(strip=True, separator=" ").split('+')[
                                  -1].strip()) if enchantment_dd and 'None' not in enchantment_dd.get_text(strip=True,
                                                                                                           separator=" ") else 0

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
                    price_gp = float(price_text) if price_text else 0.0
            else:
                price_gp = 0.0  # Valeur par défaut si aucun prix n'est trouvé

            # Extraction du UID et du UUID
            uuid_dd = find_name_by_text(properties, 'dd', 'UUID')
            if uuid_dd:
                tt_elements = uuid_dd.find_all('tt')
                uid = tt_elements[0].get_text(strip=True, separator=" ") if len(tt_elements) > 0 else 'Unknown UID'
                weapon_id = tt_elements[1].get_text(strip=True, separator=" ") if len(tt_elements) > 1 else uid or 'Unknown UUID'
            else:
                uid = 'Unknown UID'
                weapon_id = weapon_name
            if weapon_id in set_of_weapon_id:
                weapon_id += uid
            set_of_weapon_id.add(weapon_id)

            # Téléchargement de l'image
            image_tag = weapon_cell.find('img', src=True, width='50', height='50')
            if image_tag:
                image_url = "https://bg3.wiki" + image_tag['src']
                image_name = f"{weapon_name}.png"
                image_path = os.path.join(image_folder, image_name)

                # Téléchargement de l'image
                img_data = requests.get(image_url).content
                with open(image_path, 'wb') as handler:
                    handler.write(img_data)
            else:
                image_path = None

            # Insertion des données dans la table Weapons
            cursor.execute('''
            INSERT INTO Weapons (weapon_id, name, rarity, description, quote, weight_kg, weight_lb, price, enchantment, type, range_m, range_f, attributes, uid, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (weapon_id, weapon_name, rarity, description, quote, weight_kg, weight_lb, price_gp, enchantment, type_, range_m, range_f,
                  attributes, uid, image_path))

            # Extraction des informations de dégâts
            damage_dl_list = find_name_by_text(properties, 'dl', 'amage').find_all_next(class_='bg3wiki-info-blob')
            for damage_dl in damage_dl_list:
                # Extrait le type de dégâts
                damage_type = damage_dl.find('a', title='Damage Types')
                if not damage_type:
                    continue
                damage_type = damage_type.find_next("a").get_text(strip=True)

                # Extrait le dé d'origine (ex: '1d4')
                damage_dice = damage_dl.get_text(strip=True).split(' ')[0]

                # Extrait le bonus de dégâts (ex: '+1')
                damage_bonus_text = damage_dl.get_text(strip=True)
                # Extrait le bonus de dégâts uniquement s'il se trouve juste après le dé (ex: '1d4 + 1 (2~5)')
                bonus_part = damage_bonus_text.split('(')[0].strip()  # Prend tout jusqu'à la première parenthèse
                if '+' in bonus_part:
                    try:
                        damage_bonus = int(bonus_part.split('+')[1].strip())
                    except ValueError:
                        damage_bonus = 0  # Si la conversion échoue, définir à 0
                else:
                    damage_bonus = 0

                # Extrait le range total (ex: '2~5')
                damage_total_range = damage_bonus_text.split('(')[-1].split(')')[0] if '(' in damage_bonus_text else ''

                # Extrait le modificateur de dégâts (ex: 'Strength or Dexterity modifier')
                modifier_tag = damage_dl.find('a', href='/wiki/Damage_Roll#Modifiers')
                modifier = modifier_tag.get_text(strip=True) if modifier_tag else None

                # Extrait la source de dégâts
                damage_source = damage_dl.find_previous('dt').get_text(strip=True, separator=" ")

                # Insertion des informations de dégâts dans la table Damage
                cursor.execute('''
                INSERT INTO Damage (weapon_id, damage_dice, damage_bonus, damage_total_range, modifier, damage_type, damage_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (weapon_id, damage_dice, damage_bonus, damage_total_range, modifier, damage_type, damage_source))

            # Capacités spéciales
            special_abilities_section = soup_weapon.find("h3", string=lambda x: x and 'Special' in x)
            if special_abilities_section:
                # Extrait les capacités spéciales de l'arme
                special_abilities = ''.join(
                    sibling.get_text() for sibling in special_abilities_section.find_next_siblings()
                    if sibling.name not in ['h3', 'h2', 'h1']
                )

                # Insertion des informations spéciales dans la table Special_Abilities
                cursor.execute('''
                INSERT INTO Special_Abilities (weapon_id, name, description)
                VALUES (?, ?, ?)
                ''', (weapon_id, None, special_abilities))

            # Capacités de l'arme
            weapon_abilities_section = soup_weapon.find("h3", string=lambda x: x and 'Weapon actions' in x)
            if weapon_abilities_section:
                weapon_abilities_list = weapon_abilities_section.find_next_siblings('dl')
                for weapon_ability in weapon_abilities_list:
                    # Extrait le nom de la capacité
                    ability_name = weapon_ability.find_next('dt').get_text(strip=True, separator=" ").replace('( )', '').strip()

                    # Extrait la description de la capacité
                    ability_description = weapon_ability.find_next('dd').get_text(strip=True, separator=" ")

                    # Insertion des informations spéciales dans la table Special_Abilities
                    cursor.execute('''
                    INSERT INTO Weapon_Actions (weapon_id, name, description)
                    VALUES (?, ?, ?)
                    ''', (weapon_id, ability_name, ability_description))

            # Lieux de l'arme
            location_section = soup_weapon.find("h2", string=lambda x: x and 'Where to find' in x)
            if location_section:
                for location in location_section.find_next('ul').find_all('li'):
                    # Extrait des localisations
                    location_description = location.get_text(strip=True, separator=" ")

                    # Insertion des informations de localisation dans la table Weapon_Locations
                    cursor.execute('''
                    INSERT INTO Weapon_Locations (weapon_id, location_description)
                    VALUES (?, ?)
                    ''', (weapon_id, location_description))

            # Extraction des notes
            notes_section = soup_weapon.find("h2", string=lambda x: x and 'Notes' in x)
            if notes_section:
                notes_list = notes_section.find_next('div', class_='bg3wiki-tooltip-box').find_all('li')
                for note in notes_list:
                    note_content = note.get_text(strip=True, separator=" ")
                    cursor.execute('''
                    INSERT INTO Notes (weapon_id, note_content)
                    VALUES (?, ?)
                    ''', (weapon_id, note_content))

# Commit des changements après chaque itération
conn.commit()

# Fermeture de la connexion à la base de données
conn.close()

print("Les données ont été extraites et stockées dans la base de données avec succès.")
