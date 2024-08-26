import json
import sqlite3

# Load the JSON from the updated file
with open('data/json/classes.json', 'r') as file:
    data = json.load(file)

# Connect to SQLite
conn = sqlite3.connect('data/databases/bg3_classes.db')
c = conn.cursor()

# Drop tables if they already exist
c.execute('DROP TABLE IF EXISTS Classes')
c.execute('DROP TABLE IF EXISTS Class_Progression')
c.execute('DROP TABLE IF EXISTS Subclasses')
c.execute('DROP TABLE IF EXISTS Subclasses_Features')

# Create the tables
c.execute('''
CREATE TABLE Classes (
    name TEXT PRIMARY KEY,
    description TEXT,
    hit_points_at_level1 TEXT,
    hit_points_on_level_up TEXT,
    key_abilities TEXT,
    saving_throw_proficiencies TEXT,
    equipment_proficiencies TEXT,
    skill_proficiencies TEXT,
    spellcasting_ability TEXT,
    starting_equipment TEXT,
    image_path TEXT
)
''')

c.execute('''
CREATE TABLE Class_Progression (
    class_name TEXT,
    level INTEGER,
    proficiency_bonus TEXT,
    features TEXT,
    rage_charges INTEGER,
    rage_damage INTEGER,
    cantrips_known INTEGER,
    spells_known INTEGER,
    spell_slots_1st INTEGER,
    spell_slots_2nd INTEGER,
    spell_slots_3rd INTEGER,
    spell_slots_4th INTEGER,
    spell_slots_5th INTEGER,
    spell_slots_6th INTEGER,
    sorcery_points INTEGER,
    sneak_attack_damage TEXT,
    bardic_inspiration_charges INTEGER,
    channel_divinity_charges INTEGER,
    lay_on_hands_charges INTEGER,
    ki_points INTEGER,
    unarmoured_movement_bonus TEXT,
    martial_arts_damage TEXT,
    spell_slots_per_level TEXT,
    invocations_known INTEGER,
    FOREIGN KEY(class_name) REFERENCES Classes(name)
)
''')

c.execute('''
CREATE TABLE Subclasses (
    class_name TEXT,
    name TEXT,
    description TEXT,
    image_path TEXT,
    FOREIGN KEY(class_name) REFERENCES Classes(name)
)
''')

c.execute('''
CREATE TABLE Subclasses_Features (
    subclass_name TEXT,
    level INTEGER,
    feature_name TEXT,
    feature_description TEXT,
    FOREIGN KEY(subclass_name) REFERENCES Subclasses(name)
)
''')

# Insert data into tables
for class_data in data['classes']:
    # Insert class data
    c.execute('''
    INSERT INTO Classes (name, description, hit_points_at_level1, hit_points_on_level_up, key_abilities,
                         saving_throw_proficiencies, equipment_proficiencies, skill_proficiencies, spellcasting_ability,
                         starting_equipment, image_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (class_data['name'], class_data['description'], class_data['hit_points_at_level1'],
          class_data['hit_points_on_level_up'], class_data['key_abilities'], class_data['saving_throw_proficiencies'],
          class_data['equipment_proficiencies'], class_data['skill_proficiencies'],
          class_data.get('spellcasting_ability', None),
          class_data['starting_equipment'], class_data.get('image_path', None)))

    class_name = class_data['name']

    # Insert class progression data
    for progression in class_data['class_progression']:
        c.execute('''
        INSERT INTO Class_Progression (class_name, level, proficiency_bonus, features, rage_charges, rage_damage,
                                       cantrips_known, spells_known, spell_slots_1st, spell_slots_2nd, spell_slots_3rd,
                                       spell_slots_4th, spell_slots_5th, spell_slots_6th, sorcery_points, sneak_attack_damage,
                                       bardic_inspiration_charges, channel_divinity_charges, lay_on_hands_charges, ki_points,
                                       unarmoured_movement_bonus, martial_arts_damage, spell_slots_per_level, invocations_known)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (class_name, progression['level'], progression['proficiency_bonus'], progression['features'],
              progression.get('rage_charges'), progression.get('rage_damage'),
              progression.get('cantrips_known'), progression.get('spells_known'),
              progression.get('spell_slots_1st'), progression.get('spell_slots_2nd'),
              progression.get('spell_slots_3rd'), progression.get('spell_slots_4th'),
              progression.get('spell_slots_5th'), progression.get('spell_slots_6th'),
              progression.get('sorcery_points'), progression.get('sneak_attack_damage'),
              progression.get('bardic_inspiration_charges'), progression.get('channel_divinity_charges'),
              progression.get('lay_on_hands_charges'), progression.get('ki_points'),
              progression.get('unarmoured_movement_bonus'), progression.get('martial_arts_damage'),
              progression.get('spell_slots_per_level'), progression.get('invocations_known')))

    # Insert subclass data
    for subclass in class_data.get('subclasses', []):
        c.execute('''
        INSERT INTO Subclasses (class_name, name, description, image_path)
        VALUES (?, ?, ?, ?)
        ''', (class_name, subclass['name'], subclass['description'], subclass['image_path']))

        subclass_name = subclass['name']

        # Insert subclass features
        for feature in subclass['features']:
            c.execute('''
            INSERT INTO Subclasses_Features (subclass_name, level, feature_name, feature_description)
            VALUES (?, ?, ?, ?)
            ''', (subclass_name, feature['level'], feature['feature_name'], feature['feature_description']))

# Commit the changes
conn.commit()

# Close the connection
conn.close()
