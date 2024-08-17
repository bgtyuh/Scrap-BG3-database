import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Connexion à la base de données SQLite (ou création si elle n'existe pas)
conn = sqlite3.connect('bg3_spells.db')
cursor = conn.cursor()

# Suppression des tables si elles existent déjà
cursor.execute('DROP TABLE IF EXISTS spell_properties')
cursor.execute('DROP TABLE IF EXISTS spells')

# Création des tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS spells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    section TEXT,
    description TEXT,
    url TEXT,
    image_path TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS spell_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spell_id INTEGER,
    property_name TEXT,
    property_value TEXT,
    image_path TEXT,
    FOREIGN KEY (spell_id) REFERENCES spells(id)
)
''')

# Créer un dossier pour stocker les images si ce n'est pas déjà fait
image_folder = "spell_images"
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

# URL de la page des sorts
base_url = "https://bg3.wiki"
url = f"{base_url}/wiki/List_of_all_spells"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Initialisation des variables
sorts = []
current_section = None

def scrape_spell(element):
    global current_section
    result = None

    # Vérifie si on entre dans une nouvelle section de sorts (h4)
    if element.name == 'h4':
        section_title = element.find('span', class_='mw-headline').get_text().strip()
        if "Level" in section_title or "Cantrips" in section_title:
            current_section = section_title
        else:
            current_section = None

    # Si on est dans une section de sorts valide
    if current_section and element.name == 'li':
        span_icon_wrapper = element.find('span', class_='bg3wiki-icontext-icon-wrapper')
        if span_icon_wrapper:
            link = element.find('a')
            if link:
                name = link.get('title')
                sort_url = f"{base_url}{link.get('href')}"

                # Scraper la page du sort pour obtenir des informations supplémentaires
                sort_response = requests.get(sort_url)
                sort_soup = BeautifulSoup(sort_response.text, 'html.parser')

                # Extraction des informations détaillées
                description_section = sort_soup.find('div', class_='mw-parser-output')

                # Récupération de la description générale
                description = description_section.p.text.strip() if description_section and description_section.p else "No description available"

                # Récupération de l'image du sort, en évitant les petites images
                sort_image_tag = None
                for img_tag in description_section.find_all('img'):
                    width = int(img_tag.get('width', 0))
                    if width == 300:
                        sort_image_tag = img_tag
                        break

                sort_image_path = None
                if sort_image_tag:
                    sort_img_url = base_url + sort_image_tag['src']
                    sort_img_name = os.path.basename(sort_img_url)
                    sort_image_path = os.path.join(image_folder, sort_img_name)

                    # Télécharger et sauvegarder l'image du sort
                    img_response = requests.get(sort_img_url)
                    with open(sort_image_path, 'wb') as img_file:
                        img_file.write(img_response.content)

                # Retourne les informations du sort pour insertion
                result = {
                    'name': name,
                    'section': current_section,
                    'description': description,
                    'url': sort_url,
                    'image_path': sort_image_path,
                    'sort_soup': sort_soup
                }
    return result

# Boucle sur tous les éléments du document pour trouver les sorts
elements = soup.find_all(['h4', 'li'])

# Utilisation de ThreadPoolExecutor pour paralléliser le scraping
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(scrape_spell, element) for element in elements]

    for future in as_completed(futures):
        spell_data = future.result()
        if spell_data:
            # Insertion des informations de base dans la table spells
            cursor.execute('''
            INSERT INTO spells (name, section, description, url, image_path)
            VALUES (?, ?, ?, ?, ?)
            ''', (spell_data['name'], spell_data['section'], spell_data['description'], spell_data['url'], spell_data['image_path']))
            spell_id = cursor.lastrowid

            # Extraction des propriétés spécifiques
            properties_section = spell_data['sort_soup'].find('div', class_='bg3wiki-property-list')
            if properties_section:
                for dl in properties_section.find_all('dl'):
                    current_property_name = None
                    current_property_value = ""
                    property_image_path = None

                    for child in dl.children:
                        if child.name == 'dt':
                            if current_property_name:
                                cursor.execute('''
                                INSERT INTO spell_properties (spell_id, property_name, property_value, image_path)
                                VALUES (?, ?, ?, ?)
                                ''', (spell_id, current_property_name, current_property_value.strip(), property_image_path))

                            current_property_name = child.get_text().strip()
                            current_property_value = ""
                            property_image_path = None
                        elif child.name == 'dd' and current_property_name:
                            current_property_value += " " + child.get_text(separator=" ").strip()

                            img_tag = child.find('img')
                            if img_tag:
                                img_url = base_url + img_tag['src']
                                img_name = os.path.basename(img_url)
                                img_path = os.path.join(image_folder, img_name)

                                img_response = requests.get(img_url)
                                with open(img_path, 'wb') as img_file:
                                    img_file.write(img_response.content)

                                property_image_path = img_path

                    if current_property_name:
                        cursor.execute('''
                        INSERT INTO spell_properties (spell_id, property_name, property_value, image_path)
                        VALUES (?, ?, ?, ?)
                        ''', (spell_id, current_property_name, current_property_value.strip(), property_image_path))

# Validation des transactions et fermeture de la connexion
conn.commit()
conn.close()

print("Base de données créée et peuplée avec succès.")
