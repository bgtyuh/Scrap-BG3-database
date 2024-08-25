import os
import sqlite3

import requests
from bs4 import BeautifulSoup


def connect_to_db(db_name='data/databases/bg3_weapons.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    return conn, cursor


def drop_existing_tables(cursor):
    tables = ['Weapons', 'Damage', 'Special_Abilities', 'Weapon_Actions', 'Weapon_Locations', 'Notes']
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')


def create_tables(cursor):
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


def commit_and_close(conn):
    conn.commit()
    conn.close()


def create_image_folder(folder_name='weapon_images'):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)


def find_name_by_text(soup, name, text):
    for balise in soup.find_all(name):
        if text in balise.get_text(strip=True):
            return balise
    return None


def extract_attributes(properties):
    enchantment_element = find_name_by_text(properties, 'dd', 'Enchantment:')
    if enchantment_element:
        attributes = []
        next_element = enchantment_element.find_next_sibling('dd')
        while next_element and not any(
                keyword in next_element.get_text(strip=True) for keyword in ['Melee:', 'Range:']):
            attribute_text = next_element.get_text(strip=True, separator=" ")
            attributes.append(attribute_text)
            next_element = next_element.find_next_sibling('dd')
        return ', '.join(attributes)
    return None


def get_weapon_list_url():
    return "https://bg3.wiki/wiki/List_of_weapons"


def fetch_soup(url):
    response = requests.get(url)
    return BeautifulSoup(response.content, 'html.parser')


def extract_weapon_info(soup_weapon):
    weapon_name = soup_weapon.find('h1', class_='firstHeading').get_text(strip=True, separator=" ")
    description_tag = soup_weapon.find('meta', property='og:description')
    description = description_tag["content"] if description_tag else None
    quote_tag = soup_weapon.find('div', class_='bg3wiki-blockquote-text')
    quote = quote_tag.get_text() if quote_tag else None
    properties = soup_weapon.find('div', class_='bg3wiki-property-list')
    attributes = extract_attributes(properties)
    type_tag = find_name_by_text(properties, 'dt', 'Details')
    type_ = type_tag.find_next('img')['alt'] if type_tag else 'Unknown'
    range_m, range_f = extract_range(properties)
    rarity, enchantment = extract_rarity_and_enchantment(properties)
    weight_kg, weight_lb = extract_weight(properties)
    price_gp = extract_price(properties)
    uid, weapon_id = extract_uid_and_weapon_id(properties, weapon_name)
    return {
        'name': weapon_name,
        'description': description,
        'quote': quote,
        'attributes': attributes,
        'type': type_,
        'range_m': range_m,
        'range_f': range_f,
        'rarity': rarity,
        'enchantment': enchantment,
        'weight_kg': weight_kg,
        'weight_lb': weight_lb,
        'price': price_gp,
        'uid': uid,
        'weapon_id': weapon_id
    }


def extract_range(properties):
    melee_tag = find_name_by_text(properties, 'dd', 'Melee:')
    if melee_tag:
        range_m = melee_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[0].replace('m', '').strip()
        range_f = melee_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[1].replace('ft', '').strip()
    else:
        range_tag = find_name_by_text(properties, 'dd', 'Range:')
        range_m = range_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[0].replace('m', '').strip()
        range_f = range_tag.get_text(strip=True, separator=" ").split(':')[1].split('/')[1].replace('ft', '').strip()
    return range_m, range_f


def extract_rarity_and_enchantment(properties):
    rarity_dd = find_name_by_text(properties, 'dd', 'Rarity:')
    rarity = rarity_dd.get_text(strip=True, separator=" ").split(':')[-1].strip() if rarity_dd else 'Unknown'
    enchantment_dd = find_name_by_text(properties, 'dd', 'Enchantment:')
    enchantment = int(enchantment_dd.get_text(strip=True, separator=" ").split('+')[
                          -1].strip()) if enchantment_dd and 'None' not in enchantment_dd.get_text(strip=True,
                                                                                                   separator=" ") else 0
    return rarity, enchantment


def extract_weight(properties):
    weight_element = find_name_by_text(properties, 'dd', 'Weight:')
    if weight_element:
        weight = weight_element.get_text(strip=True, separator=" ").split(':')[-1].strip().split('/')
        weight_kg = float(weight[0].strip().split(' ')[0].replace('kg', '').strip())
        weight_lb = float(weight[1].strip().split(' ')[0].replace('lb', '').strip())
    else:
        weight_kg = weight_lb = 0.0
    return weight_kg, weight_lb


def extract_price(properties):
    price_element = find_name_by_text(properties, 'dd', 'Price:')
    if price_element:
        price_text = price_element.get_text(strip=True, separator=" ").split(':')[-1].strip().replace('gp', '').strip()
        if '/' in price_text:
            normal_price, _ = price_text.split('/')
            price_gp = float(normal_price.strip())
        else:
            price_gp = float(price_text) if price_text else 0.0
    else:
        price_gp = 0.0
    return price_gp


def extract_uid_and_weapon_id(properties, weapon_name):
    uuid_dd = find_name_by_text(properties, 'dd', 'UUID')
    if uuid_dd:
        tt_elements = uuid_dd.find_all('tt')
        uid = tt_elements[0].get_text(strip=True, separator=" ") if len(tt_elements) > 0 else 'Unknown UID'
        weapon_id = tt_elements[1].get_text(strip=True, separator=" ") if len(
            tt_elements) > 1 else uid or 'Unknown UUID'
    else:
        uid = 'Unknown UID'
        weapon_id = weapon_name
    return uid, weapon_id


def download_image(image_url, weapon_name, image_folder):
    image_name = f"{weapon_name}.png"
    image_path = os.path.join(image_folder, image_name)
    img_data = requests.get(image_url).content
    with open(image_path, 'wb') as handler:
        handler.write(img_data)
    return image_path


def insert_weapon_data(cursor, weapon_data):
    cursor.execute('''
    INSERT INTO Weapons (weapon_id, name, rarity, description, quote, weight_kg, weight_lb, price, enchantment, type, range_m, range_f, attributes, uid, image_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (weapon_data['weapon_id'], weapon_data['name'], weapon_data['rarity'], weapon_data['description'],
          weapon_data['quote'], weapon_data['weight_kg'], weapon_data['weight_lb'], weapon_data['price'],
          weapon_data['enchantment'], weapon_data['type'], weapon_data['range_m'], weapon_data['range_f'],
          weapon_data['attributes'], weapon_data['uid'], weapon_data['image_path']))


def extract_and_insert_damage(cursor, properties, weapon_id):
    damage_dl_list = find_name_by_text(properties, 'dl', 'amage').find_all_next(class_='bg3wiki-info-blob')
    for damage_dl in damage_dl_list:
        damage_type = damage_dl.find('a', title='Damage Types')
        if not damage_type:
            continue
        damage_type = damage_type.find_next("a").get_text(strip=True)
        damage_dice = damage_dl.get_text(strip=True).split(' ')[0]
        damage_bonus_text = damage_dl.get_text(strip=True)
        bonus_part = damage_bonus_text.split('(')[0].strip()
        if '+' in bonus_part:
            try:
                damage_bonus = int(bonus_part.split('+')[1].strip())
            except ValueError:
                damage_bonus = 0
        else:
            damage_bonus = 0
        damage_total_range = damage_bonus_text.split('(')[-1].split(')')[0] if '(' in damage_bonus_text else ''
        modifier_tag = damage_dl.find('a', href='/wiki/Damage_Roll#Modifiers')
        modifier = modifier_tag.get_text(strip=True) if modifier_tag else None
        damage_source = damage_dl.find_previous('dt').get_text(strip=True, separator=" ")
        cursor.execute('''
        INSERT INTO Damage (weapon_id, damage_dice, damage_bonus, damage_total_range, modifier, damage_type, damage_source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (weapon_id, damage_dice, damage_bonus, damage_total_range, modifier, damage_type, damage_source))


def extract_and_insert_special_abilities(cursor, soup_weapon, weapon_id):
    special_abilities_section = soup_weapon.find("h3", string=lambda x: x and 'Special' in x)
    if special_abilities_section:
        special_abilities = ''.join(
            sibling.get_text() for sibling in special_abilities_section.find_next_siblings()
            if sibling.name not in ['h3', 'h2', 'h1']
        )
        cursor.execute('''
        INSERT INTO Special_Abilities (weapon_id, name, description)
        VALUES (?, ?, ?)
        ''', (weapon_id, None, special_abilities))


def extract_and_insert_weapon_actions(cursor, soup_weapon, weapon_id):
    weapon_abilities_section = soup_weapon.find("h3", string=lambda x: x and 'Weapon actions' in x)
    if weapon_abilities_section:
        weapon_abilities_list = weapon_abilities_section.find_next_siblings('dl')
        for weapon_ability in weapon_abilities_list:
            ability_name = weapon_ability.find_next('dt').get_text(strip=True, separator=" ").replace('( )', '').strip()
            ability_description = weapon_ability.find_next('dd').get_text(strip=True, separator=" ")
            cursor.execute('''
            INSERT INTO Weapon_Actions (weapon_id, name, description)
            VALUES (?, ?, ?)
            ''', (weapon_id, ability_name, ability_description))


def extract_and_insert_weapon_locations(cursor, soup_weapon, weapon_id):
    location_section = soup_weapon.find("h2", string=lambda x: x and 'Where to find' in x)
    if location_section:
        for location in location_section.find_next('ul').find_all('li'):
            location_description = location.get_text(strip=True, separator=" ")
            cursor.execute('''
            INSERT INTO Weapon_Locations (weapon_id, location_description)
            VALUES (?, ?)
            ''', (weapon_id, location_description))


def extract_and_insert_notes(cursor, soup_weapon, weapon_id):
    notes_section = soup_weapon.find("h2", string=lambda x: x and 'Notes' in x)
    if notes_section:
        notes_list = notes_section.find_next('div', class_='bg3wiki-tooltip-box').find_all('li')
        for note in notes_list:
            note_content = note.get_text(strip=True, separator=" ")
            cursor.execute('''
            INSERT INTO Notes (weapon_id, note_content)
            VALUES (?, ?)
            ''', (weapon_id, note_content))


def main():
    conn, cursor = connect_to_db()
    drop_existing_tables(cursor)
    create_tables(cursor)
    create_image_folder()

    list_url = get_weapon_list_url()
    soup = fetch_soup(list_url)
    set_of_url = set()
    set_of_weapon_id = set()
    image_folder = 'data/images/weapon_images'

    rows = soup.select('table.wikitable tbody tr')
    for row in rows:
        weapon_cell = row.find('td')
        if weapon_cell:
            weapon_link = weapon_cell.find('a', href=True)
            if weapon_link:
                weapon_url = "https://bg3.wiki" + weapon_link['href']

                if weapon_url in set_of_url:
                    continue
                set_of_url.add(weapon_url)

                soup_weapon = fetch_soup(weapon_url)
                weapon_data = extract_weapon_info(soup_weapon)

                if weapon_data['weapon_id'] in set_of_weapon_id:
                    weapon_data['weapon_id'] += weapon_data['uid']
                set_of_weapon_id.add(weapon_data['weapon_id'])

                image_tag = weapon_cell.find('img', src=True, width='50', height='50')
                if image_tag:
                    image_url = "https://bg3.wiki" + image_tag['src']
                    weapon_data['image_path'] = download_image(image_url, weapon_data['name'], image_folder)

                insert_weapon_data(cursor, weapon_data)
                extract_and_insert_damage(cursor, soup_weapon.find('div', class_='bg3wiki-property-list'),
                                          weapon_data['weapon_id'])
                extract_and_insert_special_abilities(cursor, soup_weapon, weapon_data['weapon_id'])
                extract_and_insert_weapon_actions(cursor, soup_weapon, weapon_data['weapon_id'])
                extract_and_insert_weapon_locations(cursor, soup_weapon, weapon_data['weapon_id'])
                extract_and_insert_notes(cursor, soup_weapon, weapon_data['weapon_id'])
                print(weapon_data["name"])

    commit_and_close(conn)
    print("Les données ont été extraites et stockées dans la base de données avec succès.")


if __name__ == "__main__":
    main()
