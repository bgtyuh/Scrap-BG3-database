#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, re, sqlite3, sys
from typing import List, Tuple, Set
import requests
from bs4 import BeautifulSoup

# --------- CONFIG CHEMINS (mets ceux que TU utilises en vrai) ----------
JSON_PATH = os.environ.get("BG3_JSON", "data/json/classes.json")           # <-- racine
DB_PATH   = os.environ.get("BG3_DB",   "data/databases/bg3_classes.db")         # <-- racine
# ----------------------------------------------------------------------

CLASS_PAGE_SLUG = {
    "Bard": "Bard", "Cleric": "Cleric", "Druid": "Druid",
    "Paladin": "Paladin", "Ranger": "Ranger",
    "Sorcerer": "Sorcerer", "Warlock": "Warlock", "Wizard": "Wizard",
}

FULL, HALF, NONE = "full", "half", "none"
CLASS_CASTER_TYPE = {
    "Bard": FULL, "Cleric": FULL, "Druid": FULL, "Sorcerer": FULL, "Wizard": FULL, "Warlock": FULL,
    "Paladin": HALF, "Ranger": HALF,
    "Barbarian": NONE, "Fighter": NONE, "Monk": NONE, "Rogue": NONE,
}

FULL_MAP = {0:1, 1:1, 2:3, 3:5, 4:7, 5:9, 6:11}
HALF_MAP = {0:2, 1:2, 2:5, 3:9}

def char_level_for(class_name: str, spell_level: int) -> int:
    ctype = CLASS_CASTER_TYPE.get(class_name, NONE)
    if ctype == FULL: return FULL_MAP.get(spell_level, 99)
    if ctype == HALF: return HALF_MAP.get(spell_level, 99)
    return 99

def list_url_for_class(class_name: str) -> str:
    slug = CLASS_PAGE_SLUG.get(class_name)
    if not slug:
        raise KeyError(f"Aucune page 'List_of_*_spells' pour {class_name}")
    return f"https://bg3.wiki/wiki/List_of_{slug}_spells"

def robust_text(el) -> str:
    return el.get_text(" ", strip=True) if hasattr(el, "get_text") else str(el).strip()

def fetch_class_spell_list(class_name: str) -> List[Tuple[str, int]]:
    url = list_url_for_class(class_name)
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results: List[Tuple[str, int]] = []
    tables = soup.find_all("table")
    if not tables:
        print(f"[WARN] {class_name}: aucune table trouvée sur {url}")
        return results

    for table in tables:
        headers = [robust_text(th).lower() for th in table.find_all("th")]
        if not headers: 
            continue
        # on tolère variations: "name"/"spell", "lvl"/"level"
        try:
            name_idx = next(i for i,h in enumerate(headers) if ("spell" in h) or ("name" in h))
            lvl_idx  = next(i for i,h in enumerate(headers) if ("level" in h) or (re.search(r"\blvl\b", h)))
        except StopIteration:
            continue

        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) <= max(name_idx, lvl_idx):
                continue
            name_cell = tds[name_idx]
            link = name_cell.find("a")
            spell_name = robust_text(link) if link and robust_text(link) else robust_text(name_cell)
            if not spell_name:
                continue

            lvl_text = robust_text(tds[lvl_idx])
            if re.search(r"cantrip", lvl_text, re.I):
                spell_level = 0
            else:
                m = re.search(r"\d+", lvl_text)
                if not m:
                    # quelques pages mettent juste "—" pour cantrip; on essaie encore:
                    if lvl_text.strip() in {"—", "-", ""}:
                        spell_level = 0
                    else:
                        continue
                else:
                    spell_level = int(m.group(0))

            results.append((spell_name, spell_level))

    # dédoublonner
    dedup: Set[Tuple[str,int]] = set(results)
    return sorted(dedup, key=lambda x: (x[1], x[0].lower()))

def main():
    # 1) Charger classes
    if not os.path.exists(JSON_PATH):
        print(f"[ERREUR] JSON introuvable: {JSON_PATH}. Modifie JSON_PATH.")
        sys.exit(1)
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    class_names = [c["name"] for c in data.get("classes", [])]

    # 2) DB
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS Class_Spells_Learned(
        class_name TEXT,
        level INTEGER,
        spell_name TEXT,
        FOREIGN KEY(class_name) REFERENCES Classes(name)
    )""")
    # on nettoie pour un import propre
    c.execute("DELETE FROM Class_Spells_Learned")
    conn.commit()

    # 3) Scrape
    total = 0
    for cls in class_names:
        ctype = CLASS_CASTER_TYPE.get(cls, NONE)
        if ctype == NONE:
            print(f"[SKIP] {cls}: non-caster dans ce script.")
            continue

        try:
            pairs = fetch_class_spell_list(cls)  # (spell_name, spell_level)
        except Exception as e:
            print(f"[WARN] {cls}: échec scraping: {e}")
            continue

        if not pairs:
            print(f"[WARN] {cls}: 0 sort trouvé. Vérifie la page et/ou l’HTML.")
            continue

        rows = []
        for spell_name, spell_level in pairs:
            lvl = char_level_for(cls, spell_level)
            if lvl >= 99:
                continue
            rows.append((cls, lvl, spell_name))

        if not rows:
            print(f"[WARN] {cls}: 0 ligne à insérer après mapping (peut arriver si niveaux de sort hors plage).")
            continue

        c.executemany(
            "INSERT INTO Class_Spells_Learned(class_name, level, spell_name) VALUES (?, ?, ?)",
            rows
        )
        conn.commit()
        total += len(rows)
        # petit résumé
        lvls = {}
        for _, lvl, _ in rows:
            lvls[lvl] = lvls.get(lvl, 0) + 1
        resume = ", ".join(f"L{l}: {n}" for l,n in sorted(lvls.items()))
        print(f"[OK] {cls}: {len(rows)} sorts insérés ({resume})")

    print(f"[DONE] Total inséré: {total}. BDD: {os.path.abspath(DB_PATH)}")
    conn.close()

if __name__ == "__main__":
    main()
