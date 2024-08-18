import os
import sqlite3
import requests
from bs4 import BeautifulSoup

# Dossier pour les images
image_folder = "weapon_images"
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

# Liens vers les pages des armes
weapon_urls = [
    "https://bg3.wiki/wiki/List_of_martial_weapons",
    "https://bg3.wiki/wiki/List_of_simple_weapons"
]

base_url = "https://bg3.wiki"

# Fonction pour initialiser la base de données
def init_db():
    conn = sqlite3.connect('bg3_weapons.db')
    cursor = conn.cursor()

    # Suppression des tables si elles existent déjà
    cursor.execute('DROP TABLE IF EXISTS weapon_properties')
    cursor.execute('DROP TABLE IF EXISTS weapons')

    # Création des tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weapons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        enchantment TEXT,
        damage TEXT,
        damage_type TEXT,
        weight TEXT,
        price TEXT,
        special TEXT,
        description TEXT,
        localisation TEXT,
        image_path TEXT,
        url TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weapon_properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        weapon_id INTEGER,
        property_name TEXT,
        property_value TEXT,
        image_path TEXT,
        FOREIGN KEY (weapon_id) REFERENCES weapons(id)
    )
    ''')

    return conn, cursor

# Fonction pour télécharger une image uniquement si elle n'existe pas déjà
def download_image(img_url, img_path):
    if not os.path.exists(img_path):
        img_response = requests.get(img_url)
        with (open(img_path, 'wb') as img_file):
            img_file.write(img_response.content)
        print(f"Image downloaded: {img_path}")
    else:
        pass

# Fonction pour scraper les armes et leurs propriétés d'une page donnée
def scrape_weapon_and_details(weapon_url, name_tag, cols, cursor):
    name = name_tag.get('title')
    full_weapon_url = f"{base_url}{weapon_url}"

    enchantment = cols[1].get_text(strip=True, separator=" ")
    damage = cols[2].get_text(strip=True, separator=" ")
    damage_type = cols[3].get_text(strip=True, separator=" ")
    weight = cols[4].get_text(strip=True, separator=" ")
    price = cols[5].get_text(strip=True, separator=" ")
    special = cols[6].get_text(strip=True, separator=" ")

    # Scraper la page de l'arme pour obtenir la description et l'image principale
    response = requests.get(full_weapon_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Récupération de l'image principale (300x300 px)
    main_image_tag = soup.find('img', src=lambda x: x and '300px' in x)
    main_image_path = None
    if main_image_tag:
        img_url = base_url + main_image_tag['src']
        img_name = os.path.basename(img_url)
        main_image_path = os.path.join(image_folder, img_name)

        download_image(img_url, main_image_path)

    description_tag = soup.find('div', class_='mw-parser-output').find('p')
    description = description_tag.get_text(strip=True, separator=" ") if description_tag else "No description available"

    # Extraire la localisation
    localisation = ""
    localisation_section = soup.find('h2', string=lambda x: x and 'Where to find' in x)
    if localisation_section:
        next_div = localisation_section.find_next('div', class_='bg3wiki-tooltip-box')
        if next_div:
            locations = [li.get_text() for li in next_div.find_all('li')]
            localisation = "\n\n".join(locations)

    # Insertion des informations de base dans la table weapons, y compris la localisation
    cursor.execute('''
    INSERT INTO weapons (name, enchantment, damage, damage_type, weight, price, special, description, localisation, image_path, url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, enchantment, damage, damage_type, weight, price, special, description, localisation, main_image_path, full_weapon_url))

    weapon_id = cursor.lastrowid

    # Scraper les propriétés détaillées de l'arme
    properties_section = soup.find('div', class_='bg3wiki-property-list')
    if properties_section:
        for dl in properties_section.find_all('dl'):
            current_property_name = None
            current_property_value = ""
            image_paths = []

            for child in dl.children:
                if child.name == 'dt':
                    if current_property_name:
                        cursor.execute('''
                        INSERT INTO weapon_properties (weapon_id, property_name, property_value, image_path)
                        VALUES (?, ?, ?, ?)
                        ''', (weapon_id, current_property_name, current_property_value.strip(), ','.join(image_paths)))

                    current_property_name = child.get_text().strip()
                    current_property_value = ""
                    image_paths = []
                elif child.name == 'dd' and current_property_name:
                    current_property_value += "\n" + child.get_text(separator=" ").strip()

                    img_tag = child.find('img')
                    if img_tag:
                        img_url = base_url + img_tag['src']
                        img_name = os.path.basename(img_url)
                        img_path = os.path.join(image_folder, img_name)

                        download_image(img_url, img_path)
                        image_paths.append(img_path)

            if current_property_name:
                cursor.execute('''
                INSERT INTO weapon_properties (weapon_id, property_name, property_value, image_path)
                VALUES (?, ?, ?, ?)
                ''', (weapon_id, current_property_name, current_property_value.strip(), ','.join(image_paths)))

    # Scraper les actions d'arme sous la section "Weapon actions"
    weapon_actions_section = soup.find('h3', string=" Weapon actions ")
    if weapon_actions_section:
        dl_sections = weapon_actions_section.find_next_siblings('dl')
        for dl in dl_sections:
            current_property_name = None
            current_property_value = ""
            image_paths = []

            for child in dl.children:
                if child.name == 'dt':
                    if current_property_name:
                        cursor.execute('''
                        INSERT INTO weapon_properties (weapon_id, property_name, property_value, image_path)
                        VALUES (?, ?, ?, ?)
                        ''', (weapon_id, current_property_name, current_property_value.strip(), ','.join(image_paths)))

                    current_property_name = child.get_text(strip=True)
                    current_property_value = ""
                    image_paths = []
                elif child.name == 'dd' and current_property_name:
                    current_property_value += "\n" + child.get_text(separator=" ").strip()

                    img_tag = child.find('img')
                    if img_tag:
                        img_url = base_url + img_tag['src']
                        img_name = os.path.basename(img_url)
                        img_path = os.path.join(image_folder, img_name)

                        download_image(img_url, img_path)
                        image_paths.append(img_path)

            if current_property_name:
                cursor.execute('''
                INSERT INTO weapon_properties (weapon_id, property_name, property_value, image_path)
                VALUES (?, ?, ?, ?)
                ''', (weapon_id, current_property_name, current_property_value.strip(), ','.join(image_paths)))

# Fonction pour scraper les armes d'une page donnée
def scrape_weapon_page(url, cursor):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    seen_weapons = set()

    for table in soup.find_all('table', class_='wikitable sortable bg3wiki-weapons-table'):
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) < 7:
                continue

            name_tag = cols[0].find('a')
            if not name_tag or 'title' not in name_tag.attrs:
                continue

            name = name_tag.get('title')
            if name in seen_weapons:
                continue

            seen_weapons.add(name)
            weapon_url = name_tag.get('href')

            # Scraper l'arme et ses propriétés
            scrape_weapon_and_details(weapon_url, name_tag, cols, cursor)

# Scraping des armes depuis les pages listées
conn, cursor = init_db()
for url in weapon_urls:
    scrape_weapon_page(url, cursor)

# Validation des transactions et fermeture de la connexion
conn.commit()
conn.close()

print("Base de données des armes créée et peuplée avec succès.")
