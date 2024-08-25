import sqlite3
import json

# Load the JSON from the provided file
with open('backgrounds.json', 'r') as file:
    data = json.load(file)

# Connect to SQLite
conn = sqlite3.connect('bg3_backgrounds.db')
c = conn.cursor()

# Drop tables if they already exist
c.execute('DROP TABLE IF EXISTS Backgrounds')
c.execute('DROP TABLE IF EXISTS Background_Skills')
c.execute('DROP TABLE IF EXISTS Background_Characters')
c.execute('DROP TABLE IF EXISTS Background_Notes')

# Create the tables with uppercase names
c.execute('''
CREATE TABLE Backgrounds (
    name TEXT PRIMARY KEY,
    description TEXT
)
''')

c.execute('''
CREATE TABLE Background_Skills (
    background_name TEXT,
    skill_name TEXT,
    FOREIGN KEY(background_name) REFERENCES Backgrounds(name)
)
''')

c.execute('''
CREATE TABLE Background_Characters (
    background_name TEXT,
    character_name TEXT,
    FOREIGN KEY(background_name) REFERENCES Backgrounds(name)
)
''')

c.execute('''
CREATE TABLE Background_Notes (
    background_name TEXT,
    note TEXT,
    FOREIGN KEY(background_name) REFERENCES Backgrounds(name)
)
''')

# Insert data into tables
for background in data['backgrounds']:
    # Insert background data
    c.execute('''
    INSERT INTO Backgrounds (name, description)
    VALUES (?, ?)
    ''', (background['name'], background['description']))

    background_name = background['name']

    # Insert background skills data
    for skill in background.get('skill_proficiencies', []):
        c.execute('''
        INSERT INTO Background_Skills (background_name, skill_name)
        VALUES (?, ?)
        ''', (background_name, skill))

    # Insert background characters data
    for character in background.get('characters', []):
        c.execute('''
        INSERT INTO Background_Characters (background_name, character_name)
        VALUES (?, ?)
        ''', (background_name, character))

    # Insert background notes data
    if 'notes' in background:
        c.execute('''
        INSERT INTO Background_Notes (background_name, note)
        VALUES (?, ?)
        ''', (background_name, background['notes']))

# Commit the changes
conn.commit()

# Close the connection
conn.close()

