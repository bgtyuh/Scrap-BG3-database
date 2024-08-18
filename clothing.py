import os
import sqlite3
import requests
from bs4 import BeautifulSoup

# Connexion à la base de données SQLite (ou création si elle n'existe pas)
conn = sqlite3.connect('bg3_clothing.db')
cursor = conn.cursor()

# Suppression des tables si elles existent déjà
cursor.execute('DROP TABLE IF EXISTS clothing_properties')
cursor.execute('DROP TABLE IF EXISTS clothing')

# Création des tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS clothing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    weight TEXT,
    price TEXT,
    effects TEXT,
    description TEXT,
    image_path TEXT,
    url TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS clothing_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clothing_id INTEGER,
    property_name TEXT,
    property_value TEXT,
    image_path TEXT,
    FOREIGN KEY (clothing_id) REFERENCES clothing(id)
)
''')

# Créer un dossier pour stocker les images si ce n'est pas déjà fait
image_folder = "clothing_images"
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

# URL de la page des vêtements
base_url = "https://bg3.wiki"
url = f"{base_url}/wiki/Clothing"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Fonction pour télécharger une image uniquement si elle n'existe pas déjà
def download_image(img_url, img_path):
    if not os.path.exists(img_path):
        img_response = requests.get(img_url)
        with open(img_path, 'wb') as img_file:
            img_file.write(img_response.content)
        print(f"Image downloaded: {img_path}")
    else:
        pass

# Fonction pour scraper les vêtements et leurs propriétés d'une page donnée
def scrape_clothing_and_details(item_url, name_tag, cols, cursor):
    name = name_tag.get('title')
    full_item_url = f"{base_url}{item_url}"

    weight = cols[1].get_text(strip=True, separator=" ")
    price = cols[2].get_text(strip=True, separator=" ")
    effects = cols[3].get_text(strip=True, separator=" ")

    # Scraper la page du vêtement pour obtenir la description et l'image principale
    response = requests.get(full_item_url)
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
    description = description_tag.get_text(strip=True) if description_tag else "No description available"

    # Insertion des informations de base dans la table clothing, y compris la description et l'image principale
    cursor.execute('''
    INSERT INTO clothing (name, weight, price, effects, description, image_path, url)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, weight, price, effects, description, main_image_path, full_item_url))
    clothing_id = cursor.lastrowid

    # Ajout de la propriété "Type" avec la valeur "Clothing" et image_path
    cursor.execute('''
    INSERT INTO clothing_properties (clothing_id, property_name, property_value, image_path)
    VALUES (?, ?, ?, ?)
    ''', (clothing_id, "Type", "Clothing", main_image_path))

    # Scraper les propriétés détaillées du vêtement sous "Properties"
    properties_section = soup.find('div', class_='bg3wiki-property-list')
    if properties_section:
        for li in properties_section.find_all('li'):
            # Séparer le nom de la propriété et sa valeur
            property_text = li.get_text(strip=True, separator=" ")
            if ":" in property_text:
                property_name, property_value = property_text.split(":", 1)
            else:
                property_name = property_text
                property_value = None

            property_image_paths = []
            img_tags = li.find_all('img')
            for img_tag in img_tags:
                img_url = base_url + img_tag['src']
                img_name = os.path.basename(img_url)
                img_path = os.path.join(image_folder, img_name)
                download_image(img_url, img_path)
                property_image_paths.append(img_path)

            cursor.execute('''
            INSERT INTO clothing_properties (clothing_id, property_name, property_value, image_path)
            VALUES (?, ?, ?, ?)
            ''', (clothing_id, property_name.strip(), property_value.strip() if property_value else None, ','.join(property_image_paths)))

    # Scraper les actions spéciales sous "Special"
    special_section = soup.find('h3', id="Special")
    if special_section:
        special_list = special_section.find_next('ul')
        for li in special_list.find_all('li'):
            action_name = li.get_text(strip=True, separator=" ")
            action_image_paths = []

            img_tags = li.find_all('img')
            for img_tag in img_tags:
                img_url = base_url + img_tag['src']
                img_name = os.path.basename(img_url)
                img_path = os.path.join(image_folder, img_name)
                download_image(img_url, img_path)
                action_image_paths.append(img_path)

            cursor.execute('''
            INSERT INTO clothing_properties (clothing_id, property_name, property_value, image_path)
            VALUES (?, ?, ?, ?)
            ''', (clothing_id, action_name, None, ','.join(action_image_paths)))

    # Scraper les propriétés UID et UUID et inclure image_path si une image est associée
    for details in soup.find_all('details', class_='bg3wiki-uid'):
        property_name = details.find('summary').get_text(strip=True)
        property_value = details.find('tt').get_text(strip=True)
        cursor.execute('''
        INSERT INTO clothing_properties (clothing_id, property_name, property_value, image_path)
        VALUES (?, ?, ?, ?)
        ''', (clothing_id, property_name, property_value, None))

# Fonction pour scraper les vêtements d'une page donnée
def scrape_clothing_page(url, cursor):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    seen_items = set()

    for table in soup.find_all('table', class_='wikitable sortable'):
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) < 4:
                continue

            name_tag = cols[0].find('a')
            if not name_tag or 'title' not in name_tag.attrs:
                continue

            name = name_tag.get('title')
            if name in seen_items:
                continue

            seen_items.add(name)
            item_url = name_tag.get('href')

            # Scraper le vêtement et ses propriétés
            scrape_clothing_and_details(item_url, name_tag, cols, cursor)

# Scraping des vêtements depuis la page listée
scrape_clothing_page(url, cursor)

# Validation des transactions et fermeture de la connexion
conn.commit()
conn.close()

print("Base de données des vêtements créée et peuplée avec succès.")
