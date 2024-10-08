
# Scrap-BG3-Database

## Description

Ce projet vise à extraire des données du jeu **Baldur's Gate 3 (BG3)** en utilisant des scrapers Python. Les données sont organisées sous forme de fichiers JSON et bases de données SQLite, et incluent des informations sur divers éléments du jeu tels que les capacités, les armes, les armures, les races, etc.

## Arborescence du projet

```plaintext
Scrap-BG3-database/
│
├── data/
│   ├── json/
│   │   ├── abilities.json
│   │   ├── backgrounds.json
│   │   ├── classes.json
│   │   ├── feats.json
│   │   ├── races.json
│   │   └── ... (autres fichiers JSON)
│   ├── databases/
│   │   ├── bg3_abilities.db
│   │   ├── bg3_amulets.db
│   │   ├── bg3_armours.db
│   │   ├── ... (autres fichiers SQLite)
│   └── images/
│       ├── amulets_images/
│       ├── armour_images/
│       ├── weapons_images/
│       └── ... (autres dossiers d'images)
│
├── abilities.py
├── amulets.py
├── armours.py
├── weapons.py
├── ... (autres scripts de scraping)
│
├── .idea/  (fichiers de configuration PyCharm)
├── README.md  (ce fichier)
```

## Structure des données

- **Fichiers JSON** (`data/json/`) : Ces fichiers contiennent des données structurées sur les différents éléments du jeu, certains construits manuellement.
- **Bases de données SQLite** (`data/databases/`) : Ces fichiers stockent les données sous une forme de base de données, facilitant les requêtes et analyses.
- **Images** (`data/images/`) : Les dossiers contiennent les images des différents éléments du jeu.

Les scripts pour lesquels aucun fichier JSON n'a le même nom sont conçus pour scraper directement les informations sur le [wiki de BG3](https://bg3.wiki/).

## Contribution

Les contributions sont les bienvenues ! Si vous souhaitez améliorer les scrapers ou ajouter de nouvelles fonctionnalités, n'hésitez pas à soumettre une pull request.
