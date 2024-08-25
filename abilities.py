import sqlite3
import json

# Load the JSON from the provided file
with open('abilities.json', 'r') as file:
    data = json.load(file)

# Connect to SQLite
conn = sqlite3.connect('bg3_abilities.db')
c = conn.cursor()

# Drop tables if they already exist
c.execute('DROP TABLE IF EXISTS Abilities')
c.execute('DROP TABLE IF EXISTS Ability_Uses')
c.execute('DROP TABLE IF EXISTS Ability_Checks')
c.execute('DROP TABLE IF EXISTS Ability_Check_Skills')
c.execute('DROP TABLE IF EXISTS Ability_Saves')

# Create the tables with uppercase names
c.execute('''
CREATE TABLE Abilities (
    name TEXT PRIMARY KEY,
    description TEXT,
    image_path TEXT
)
''')

c.execute('''
CREATE TABLE Ability_Uses (
    ability_name TEXT,
    use_name TEXT,
    description TEXT,
    FOREIGN KEY(ability_name) REFERENCES Abilities(name)
)
''')

c.execute('''
CREATE TABLE Ability_Checks (
    ability_name TEXT,
    check_type TEXT,
    description TEXT,
    FOREIGN KEY(ability_name) REFERENCES Abilities(name)
)
''')

c.execute('''
CREATE TABLE Ability_Check_Skills (
    ability_name TEXT,
    skill_name TEXT,
    description TEXT,
    FOREIGN KEY(ability_name) REFERENCES Abilities(name)
)
''')

c.execute('''
CREATE TABLE Ability_Saves (
    ability_name TEXT,
    description TEXT,
    FOREIGN KEY(ability_name) REFERENCES Abilities(name)
)
''')

# Insert data into tables
for ability in data['abilities']:
    # Insert ability data
    c.execute('''
    INSERT INTO Abilities (name, description, image_path)
    VALUES (?, ?, ?)
    ''', (ability['name'], ability['description'], ability['image_path']))

    ability_name = ability['name']

    # Insert ability uses data
    for use_name, use_description in ability.get('uses', {}).items():
        c.execute('''
        INSERT INTO Ability_Uses (ability_name, use_name, description)
        VALUES (?, ?, ?)
        ''', (ability_name, use_name, use_description))

    # Insert ability checks data
    c.execute('''
    INSERT INTO Ability_Checks (ability_name, check_type, description)
    VALUES (?, ?, ?)
    ''', (ability_name, 'general', ability['checks']['general']))

    # Insert ability check skills data
    for skill_name, skill_description in ability['checks'].get('skills', {}).items():
        c.execute('''
        INSERT INTO Ability_Check_Skills (ability_name, skill_name, description)
        VALUES (?, ?, ?)
        ''', (ability_name, skill_name, skill_description))

    # Insert ability saves data
    c.execute('''
    INSERT INTO Ability_Saves (ability_name, description)
    VALUES (?, ?)
    ''', (ability_name, ability['saves']))

# Commit the changes
conn.commit()

# Close the connection
conn.close()

