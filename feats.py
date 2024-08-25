import sqlite3
import json

# Load the JSON from the provided file
with open('feats.json', 'r') as file:
    data = json.load(file)

# Connect to SQLite
conn = sqlite3.connect('bg3_feats.db')
c = conn.cursor()

# Drop tables if they already exist
c.execute('DROP TABLE IF EXISTS Feats')
c.execute('DROP TABLE IF EXISTS Feat_Options')
c.execute('DROP TABLE IF EXISTS Feat_Notes')

# Create the tables with uppercase names
c.execute('''
CREATE TABLE Feats (
    name TEXT PRIMARY KEY,
    description TEXT,
    prerequisite TEXT
)
''')

c.execute('''
CREATE TABLE Feat_Options (
    feat_name TEXT,
    option_name TEXT,
    description TEXT,
    FOREIGN KEY(feat_name) REFERENCES Feats(name)
)
''')

c.execute('''
CREATE TABLE Feat_Notes (
    feat_name TEXT,
    note TEXT,
    FOREIGN KEY(feat_name) REFERENCES Feats(name)
)
''')

# Insert data into tables
for feat in data['feats']:
    # Insert feat data, handling missing description
    description = feat.get('description', None)
    c.execute('''
    INSERT INTO Feats (name, description, prerequisite)
    VALUES (?, ?, ?)
    ''', (feat['name'], description, feat.get('prerequisite', None)))

    feat_name = feat['name']

    # Insert feat options data
    for option in feat.get('options', []):
        c.execute('''
        INSERT INTO Feat_Options (feat_name, option_name, description)
        VALUES (?, ?, ?)
        ''', (feat_name, option['name'], option['description']))

    # Insert feat notes data
    for note in feat.get('notes', []):
        c.execute('''
        INSERT INTO Feat_Notes (feat_name, note)
        VALUES (?, ?)
        ''', (feat_name, note))

# Commit the changes
conn.commit()

# Close the connection
conn.close()
