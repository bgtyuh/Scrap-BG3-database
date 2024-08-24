import os
import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import json

# Créer un dossier pour stocker les images si ce n'est pas déjà fait
image_folder = 'headwear_images'
os.makedirs(image_folder, exist_ok=True)


# Fonction pour télécharger une image si elle n'existe pas déjà
def download_image(img_url, folder, filename):
    img_path = os.path.join(folder, filename)
    if not os.path.exists(img_path):
        response = requests.get(img_url, stream=True)
        if response.status_code == 200:
            with open(img_path, 'wb') as file:
                for chunk in response:
                    file.write(chunk)
        else:
            print(f"Erreur de téléchargement: {img_url}")


# Fonction personnalisée pour rechercher un élément contenant un certain texte
def find_li_by_text(soup, text):
    for li in soup.find_all('li'):
        if text in li.get_text(strip=True):
            return li
    return None


# Connexion à la base de données SQLite
conn = sqlite3.connect('bg3_headwears.db')
c = conn.cursor()

# Suppression des tables si elles existent déjà pour garantir une base de données propre
c.execute('DROP TABLE IF EXISTS Items')
c.execute('DROP TABLE IF EXISTS Specials')
c.execute('DROP TABLE IF EXISTS Locations')

# Création des tables
c.execute('''
CREATE TABLE IF NOT EXISTS Items (
    item_id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    quote TEXT,
    type TEXT,
    rarity TEXT,
    weight_kg REAL,
    weight_lb REAL,
    price_gp REAL,
    uid TEXT,
    image_path TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS Specials (
    special_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT,
    type TEXT,
    name TEXT,
    effect TEXT,
    FOREIGN KEY (item_id) REFERENCES Items (item_id)
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS Locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT,
    description TEXT,
    FOREIGN KEY (item_id) REFERENCES Items (item_id)
)
''')

# URL de la page Clothing
headwears_url = "https://bg3.wiki/wiki/Headwear"

# Requête pour obtenir le contenu de la page
response = requests.get(headwears_url)
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')

    base_url = "https://bg3.wiki"

    # Extraction des liens vers chaque page de vêtement avec une image de taille 50x50
    headwears_links = []
    for a in soup.select('table.wikitable a'):
        img = a.find('img')
        if a['href'].startswith('/wiki/') and img and img.get('width') == '50' and img.get('height') == '50':
            headwears_links.append(base_url + a['href'])

    # Itérer sur chaque lien de vêtement pour scraper les données
    for headwears_url in headwears_links:
        response = requests.get(headwears_url)
        if response.status_code == 200:
            headwears_soup = BeautifulSoup(response.content, 'html.parser')

            # Extraction des données
            name = headwears_soup.find('h1', id='firstHeading').get_text(strip=True, separator=" ")

            # Vérification si l'élément quote existe avant d'appeler get_text()
            description_element_tag = headwears_soup.find('meta', property='og:description')
            description = description_element_tag["content"] if description_element_tag else ""

            # Vérification si l'élément quote existe avant d'appeler get_text()
            quote_element = headwears_soup.find('div', class_='bg3wiki-blockquote-text')
            quote = quote_element.get_text(strip=True, separator=" ") if quote_element else ""

            # Extraire le contenu du script contenant wgCategories
            script_content = headwears_soup.find('script').string
            match = re.search(r'wgCategories":\s*(\[[^\]]*\])', script_content)
            if match:
                # Charger la liste JSON de wgCategories en tant que liste Python
                wg_categories = json.loads(match.group(1))
                # Extraire la première valeur ou toute la liste selon les besoins
                wg_categories.remove('Bugs') if wg_categories and 'Bugs' in wg_categories else None
                headwear_type = wg_categories[0] if wg_categories else None
            else:
                print(f"wgCategories not found for {name}.")
                headwear_type = None

            # Télécharger l'image principale (floatright)
            main_image = headwears_soup.find('img', alt=name + ' image')
            if main_image and main_image['src']:
                img_url = base_url + main_image['src']
                img_filename = os.path.basename(main_image['src'])
                download_image(img_url, image_folder, img_filename)
                image_path = os.path.join(image_folder, img_filename)
            else:
                image_path = None

            # Rareté
            rarity_element = find_li_by_text(headwears_soup, 'Rarity:')
            rarity = rarity_element.get_text(strip=True, separator=" ").split(':')[
                -1].strip() if rarity_element else 'Unknown'

            # Poids
            weight_element = find_li_by_text(headwears_soup, 'Weight:')
            if weight_element:
                weight = weight_element.get_text(strip=True, separator=" ").split(':')[-1].strip().split('/')
                weight_kg = float(weight[0].strip().split(' ')[0].replace('kg', '').strip())
                weight_lb = float(weight[1].strip().split(' ')[0].replace('lb', '').strip())
            else:
                weight_kg = weight_lb = 0.0

            # Traitement du prix
            price_element = find_li_by_text(headwears_soup, 'Price:')
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

            # UID et UUID
            uid_element = headwears_soup.find_all('tt')
            uid = uid_element[0].get_text(strip=True, separator=" ") if uid_element else 'Unknown UID'
            uuid = uid_element[1].get_text(strip=True, separator=" ") if len(uid_element) > 1 else 'Unknown UUID'

            # Vérifier si l'item existe déjà dans la base de données
            c.execute('SELECT COUNT(*) FROM Items WHERE item_id = ?', (uuid,))
            if c.fetchone()[0] > 0:
                print(f"L'item {name} avec l'UID {uuid} existe déjà. Ignoré.")
                continue

            # Insertion des données dans la table Items
            c.execute('''
            INSERT INTO Items (item_id, name, description, quote, type, rarity, weight_kg, weight_lb, price_gp, uid, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
            uuid, name, description, quote, headwear_type, rarity, weight_kg, weight_lb, price_gp,
            uid, image_path))

            # Extraction des effets spéciaux des <dl>, <ul> et autres éléments après "Special"
            specials_section = headwears_soup.find('h3', string="Special")
            if specials_section:
                # Suivre les éléments pertinents après le <h3> "Special"
                next_elem = specials_section.find_next_sibling()
                while next_elem and next_elem.name not in ['h2', 'h3']:  # Arrêter au prochain titre de section
                    # Gérer les <div> avec les listes d'effets spéciaux
                    if next_elem.name == 'div' and 'bg3wiki-tablelist' in next_elem.get('class', []):
                        for dl in next_elem.find_all('dl'):
                            special_name = dl.find('dt').get_text(strip=True, separator=" ") if dl.find(
                                'dt') else 'Unknown Special'
                            special_effect = dl.find('dd').get_text(strip=True, separator=" ") if dl.find(
                                'dd') else 'Unknown Effect'

                            c.execute('''
                            INSERT INTO Specials (item_id, type, name, effect)
                            VALUES (?, ?, ?, ?)
                            ''', (uuid, "Special", special_name, special_effect))

                    # Gérer les <ul> avec des effets comme "Armour Class +1"
                    elif next_elem.name == 'ul':
                        for li in next_elem.find_all('li'):
                            special_effect = li.get_text(strip=True, separator=" ")

                            if special_effect:
                                c.execute('''
                                INSERT INTO Specials (item_id, type, name, effect)
                                VALUES (?, ?, ?, ?)
                                ''', (uuid, "Bonus", "Special Effect", special_effect))

                    # Gérer les éléments <dl> autonomes comme "Mirror Image"
                    elif next_elem.name == 'dl':
                        special_name = next_elem.find('dt').get_text(strip=True, separator=" ") if next_elem.find(
                            'dt') else 'Unknown Special'
                        special_effect = next_elem.find('dd').get_text(strip=True, separator=" ") if next_elem.find(
                            'dd') else 'Unknown Effect'

                        c.execute('''
                        INSERT INTO Specials (item_id, type, name, effect)
                        VALUES (?, ?, ?, ?)
                        ''', (uuid, "Special", special_name, special_effect))

                    next_elem = next_elem.find_next_sibling()

            # Extraction des emplacements "Where to find"
            location_section = headwears_soup.find('h2', string=lambda x: x and "Where to find" in x)
            if location_section:
                # Trouver le <div> suivant contenant les informations
                location_div = location_section.find_next_sibling()
                if location_div and location_div.name == 'div' and 'bg3wiki-tooltip-box' in location_div.get('class',
                                                                                                             []):
                    ul_element = location_div.find('ul')
                    if ul_element:
                        for li in ul_element.find_all('li'):
                            location_text = li.get_text(strip=True, separator=" ")

                            c.execute('''
                            INSERT INTO Locations (item_id, description)
                            VALUES (?, ?)
                            ''', (uuid, location_text))

            # Commit après chaque vêtement pour éviter de perdre des données en cas de problème
            conn.commit()

# Fermeture de la connexion à la base de données
conn.close()

print("Les données ont été extraites et stockées dans la base de données avec succès.")
