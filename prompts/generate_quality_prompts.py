#!/usr/bin/env python3
"""
Script pour générer des prompts d'entraînement de HAUTE QUALITÉ.

Objectifs:
- Formulations naturelles et variées (comme un vrai utilisateur)
- Fautes de frappe, abréviations, langage familier
- Contexte et intentions variées
- Cas ambigus avec clarification
- Diversité linguistique (formel, informel, technique)

Usage:
    python generate_quality_prompts.py

Output:
    training_prompts_quality.json - À importer via l'IHM MCParr
"""

import json
import random
from typing import List, Dict, Any
from dataclasses import dataclass

OUTPUT_FILE = "/home/jeremie/Documents/Developpement/mcparr/training_prompts_quality.json"

SYSTEM_PROMPT = "Tu es MCParr, un assistant IA pour homelab. Tu aides l'utilisateur à gérer ses services média et infrastructure."

# ============================================================================
# PATTERNS LINGUISTIQUES NATURELS
# ============================================================================

# Variations de début de phrase (intent markers)
INTENT_MARKERS = {
    "search": [
        "", "je cherche", "tu as", "y a", "t'as", "tu aurais", "je voudrais",
        "j'aimerais", "j'ai envie de", "trouve-moi", "montre-moi", "donne-moi",
        "est-ce que tu as", "est-ce qu'il y a", "c'est possible d'avoir",
        "je peux avoir", "on a", "on aurait", "dis-moi si tu as",
    ],
    "action": [
        "", "lance", "mets", "démarre", "joue", "fais", "peux-tu",
        "tu peux", "tu pourrais", "j'aimerais que tu", "go",
    ],
    "info": [
        "", "c'est quoi", "qu'est-ce que", "donne-moi", "montre", "affiche",
        "dis-moi", "info sur", "infos", "détails", "stats",
    ],
    "download": [
        "", "télécharge", "dl", "download", "récupère", "ajoute", "chope",
        "get", "prends", "va chercher", "mets en dl",
    ],
}

# Particules de politesse (optionnelles)
POLITENESS = ["", " stp", " svp", " s'il te plaît", " please", " pls"]

# Marqueurs de fin
END_MARKERS = ["", " ?", " !", " ...", " merci", " thanks"]

# Typos communes
TYPOS = {
    "cherche": ["cherche", "cherhe", "chrche", "cerche"],
    "télécharge": ["télécharge", "telecharge", "telecharg", "dl", "download"],
    "regarde": ["regarde", "regare", "regarder", "voir"],
    "écoute": ["écoute", "ecoute", "ecouter", "écouter"],
    "série": ["série", "serie", "séries", "series"],
    "film": ["film", "films", "movie", "movies"],
    "manga": ["manga", "mangas", "mnga"],
    "podcast": ["podcast", "podcasts", "pod"],
}

# ============================================================================
# DONNÉES PAR SERVICE - FORMULATIONS NATURELLES
# ============================================================================

@dataclass
class PromptTemplate:
    """Template de prompt avec variations."""
    patterns: List[str]  # Formulations variées
    tool: str
    tool_args_template: Dict[str, Any]
    tags: List[str]
    category: str


# Audiobookshelf - Livres audio
AUDIOBOOKSHELF_TEMPLATES = [
    # Recherche directe
    PromptTemplate(
        patterns=[
            "{title} en audio",
            "{title} audiobook",
            "{title} livre audio",
            "l'audiobook de {title}",
            "le livre audio {title}",
            "{title} version audio",
            "{title} version narrée",
            "{title} lu par quelqu'un",
            "écouter {title}",
            "j'écoute {title}",
            "mettre {title} en fond",
            "{title} pour le trajet",
            "{title} à écouter",
            "un truc de {author} à écouter",
            "du {author} en audio",
            "{author} audiobook",
        ],
        tool="audiobookshelf_search",
        tool_args_template={"query": "{query}"},
        tags=["audiobookshelf", "audiobook", "écouter"],
        category="media",
    ),
    # Demandes vagues/générales
    PromptTemplate(
        patterns=[
            "qu'est-ce que t'as à écouter",
            "un truc à écouter",
            "un audiobook sympa",
            "quelque chose à écouter en voiture",
            "un livre audio pour ce soir",
            "tu recommandes quoi en audio",
            "des suggestions audiobooks",
            "un bon livre à écouter",
            "qu'est-ce qui est bien en livre audio",
            "un audiobook court",
            "un truc long à écouter",
        ],
        tool="audiobookshelf_search",
        tool_args_template={"query": ""},
        tags=["audiobookshelf", "recommendation"],
        category="media",
    ),
    # Bibliothèques
    PromptTemplate(
        patterns=[
            "mes audiobooks",
            "ma collection audio",
            "bibliothèque audiobookshelf",
            "tout ce que j'ai en audio",
            "combien de livres audio",
            "mes livres audio",
            "liste mes audiobooks",
            "qu'est-ce que j'ai à écouter",
        ],
        tool="audiobookshelf_get_libraries",
        tool_args_template={},
        tags=["audiobookshelf", "bibliothèque"],
        category="media",
    ),
    # Progression
    PromptTemplate(
        patterns=[
            "j'en étais où",
            "reprendre mon livre",
            "continuer mon audiobook",
            "où j'en suis dans mon bouquin",
            "ma progression",
            "qu'est-ce que j'écoutais",
            "mon livre en cours",
            "reprendre là où j'en étais",
        ],
        tool="audiobookshelf_get_media_progress",
        tool_args_template={},
        tags=["audiobookshelf", "progression"],
        category="media",
    ),
]

# Plex - Films et Séries
PLEX_TEMPLATES = [
    # Recherche film
    PromptTemplate(
        patterns=[
            "{title}",
            "le film {title}",
            "{title} le film",
            "regarder {title}",
            "voir {title}",
            "mater {title}",
            "{title} ce soir",
            "on regarde {title}",
            "{title} dispo ?",
            "{title} sur plex",
            "{title} en 4k",
            "{title} en vf",
            "{title} en vo",
            "le {title}",
            "un {title}",
        ],
        tool="plex_search_media",
        tool_args_template={"query": "{query}", "media_type": "movie"},
        tags=["plex", "film", "regarder"],
        category="media",
    ),
    # Recherche série
    PromptTemplate(
        patterns=[
            "la série {title}",
            "{title} série",
            "{title} saison",
            "{title} épisode",
            "{title} s01",
            "{title} dernière saison",
            "regarder {title}",
            "on mate {title}",
            "{title} série tv",
            "la série {title} complète",
            "{title} tous les épisodes",
        ],
        tool="plex_search_media",
        tool_args_template={"query": "{query}", "media_type": "show"},
        tags=["plex", "série", "regarder"],
        category="media",
    ),
    # Demandes vagues vidéo
    PromptTemplate(
        patterns=[
            "un film",
            "un truc à regarder",
            "quelque chose à voir",
            "un bon film",
            "une bonne série",
            "qu'est-ce qu'on regarde",
            "un film d'action",
            "un film drôle",
            "une comédie",
            "un thriller",
            "un film récent",
            "un film de science fiction",
            "un film de super héros",
            "un truc léger",
            "un film pour ce soir",
        ],
        tool="plex_search_media",
        tool_args_template={"query": "{genre}", "media_type": "movie"},
        tags=["plex", "recommendation"],
        category="media",
    ),
    # Nouveautés
    PromptTemplate(
        patterns=[
            "quoi de neuf",
            "nouveautés",
            "derniers ajouts",
            "qu'est-ce qui est nouveau",
            "ajouté récemment",
            "nouveaux films",
            "nouvelles séries",
            "what's new",
            "derniers downloads",
            "récemment téléchargé",
        ],
        tool="plex_get_recently_added",
        tool_args_template={"limit": 10},
        tags=["plex", "nouveautés"],
        category="media",
    ),
    # En cours
    PromptTemplate(
        patterns=[
            "reprendre",
            "continuer à regarder",
            "j'en étais où",
            "mon film en cours",
            "ma série en cours",
            "continue",
            "on deck",
            "ce que je regardais",
        ],
        tool="plex_get_on_deck",
        tool_args_template={"limit": 5},
        tags=["plex", "en_cours"],
        category="media",
    ),
    # Sessions
    PromptTemplate(
        patterns=[
            "qui regarde",
            "qui streame",
            "sessions actives",
            "qui utilise plex",
            "combien de streams",
            "y a du monde",
            "c'est utilisé là",
        ],
        tool="plex_get_active_sessions",
        tool_args_template={},
        tags=["plex", "sessions"],
        category="media",
    ),
]

# Tautulli - Stats Plex
TAUTULLI_TEMPLATES = [
    PromptTemplate(
        patterns=[
            "activité plex",
            "qui regarde quoi",
            "streams en cours",
            "activité en ce moment",
            "monitoring plex",
        ],
        tool="tautulli_get_activity",
        tool_args_template={},
        tags=["tautulli", "activité"],
        category="media",
    ),
    PromptTemplate(
        patterns=[
            "historique plex",
            "qu'est-ce qui a été regardé",
            "history",
            "derniers visionnages",
            "qui a regardé quoi",
            "films vus",
            "séries vues",
        ],
        tool="tautulli_get_history",
        tool_args_template={},
        tags=["tautulli", "historique"],
        category="media",
    ),
    PromptTemplate(
        patterns=[
            "stats plex",
            "statistiques",
            "top films",
            "films les plus vus",
            "séries populaires",
            "temps de visionnage",
        ],
        tool="tautulli_get_statistics",
        tool_args_template={},
        tags=["tautulli", "stats"],
        category="media",
    ),
]

# Komga - Mangas et BD
KOMGA_TEMPLATES = [
    # Recherche
    PromptTemplate(
        patterns=[
            "{title}",
            "le manga {title}",
            "{title} manga",
            "lire {title}",
            "bd {title}",
            "bande dessinée {title}",
            "comic {title}",
            "{title} tome",
            "{title} dernier tome",
            "{title} tous les tomes",
            "la bd {title}",
            "{title} scan",
            "{title} scans",
        ],
        tool="komga_search",
        tool_args_template={"query": "{query}"},
        tags=["komga", "manga", "bd", "lire"],
        category="media",
    ),
    # Demandes vagues lecture
    PromptTemplate(
        patterns=[
            "un manga",
            "un truc à lire",
            "une bd",
            "un comic",
            "qu'est-ce que j'ai à lire",
            "un manga sympa",
            "une bd drôle",
            "un shonen",
            "un seinen",
            "du marvel",
            "du dc comics",
        ],
        tool="komga_search",
        tool_args_template={"query": "{genre}"},
        tags=["komga", "recommendation"],
        category="media",
    ),
    # Bibliothèque
    PromptTemplate(
        patterns=[
            "mes mangas",
            "ma collection manga",
            "bibliothèque komga",
            "mes bd",
            "combien de mangas",
            "liste mes mangas",
        ],
        tool="komga_get_libraries",
        tool_args_template={},
        tags=["komga", "bibliothèque"],
        category="media",
    ),
]

# RomM - Jeux rétro
ROMM_TEMPLATES = [
    # Recherche jeu
    PromptTemplate(
        patterns=[
            "{title}",
            "le jeu {title}",
            "{title} rom",
            "jouer à {title}",
            "{title} sur {platform}",
            "rom {title}",
            "le {title}",
            "{title} jeu",
        ],
        tool="romm_search_roms",
        tool_args_template={"query": "{query}"},
        tags=["romm", "jeu", "rétro"],
        category="media",
    ),
    # Plateformes
    PromptTemplate(
        patterns=[
            "quelles consoles",
            "plateformes dispo",
            "émulateurs",
            "mes consoles",
            "liste des plateformes",
            "consoles rétro",
        ],
        tool="romm_get_platforms",
        tool_args_template={},
        tags=["romm", "plateforme"],
        category="media",
    ),
    # Par plateforme
    PromptTemplate(
        patterns=[
            "jeux {platform}",
            "roms {platform}",
            "catalogue {platform}",
            "mes jeux {platform}",
            "collection {platform}",
        ],
        tool="romm_get_roms",
        tool_args_template={"platform_id": "{platform_id}"},
        tags=["romm", "plateforme"],
        category="media",
    ),
]

# Radarr - Téléchargement films
RADARR_TEMPLATES = [
    # Téléchargement
    PromptTemplate(
        patterns=[
            "télécharge {title}",
            "dl {title}",
            "download {title}",
            "ajoute {title}",
            "récupère {title}",
            "get {title}",
            "{title} à télécharger",
            "prends {title}",
            "choppe {title}",
            "tu peux dl {title}",
            "mets {title} en téléchargement",
            "ajoute {title} à la collection",
        ],
        tool="radarr_search_movie",
        tool_args_template={"query": "{query}"},
        tags=["radarr", "téléchargement", "film"],
        category="media",
    ),
    # Queue
    PromptTemplate(
        patterns=[
            "téléchargements en cours",
            "queue radarr",
            "qu'est-ce qui télécharge",
            "films en dl",
            "état des downloads",
            "progression téléchargements",
        ],
        tool="radarr_get_queue",
        tool_args_template={},
        tags=["radarr", "queue"],
        category="media",
    ),
    # Calendrier
    PromptTemplate(
        patterns=[
            "films à venir",
            "prochaines sorties",
            "calendrier films",
            "sorties ciné",
            "qu'est-ce qui sort",
        ],
        tool="radarr_get_calendar",
        tool_args_template={"days": 30},
        tags=["radarr", "calendrier"],
        category="media",
    ),
]

# Sonarr - Téléchargement séries
SONARR_TEMPLATES = [
    # Téléchargement
    PromptTemplate(
        patterns=[
            "télécharge la série {title}",
            "dl {title} série",
            "ajoute la série {title}",
            "récupère {title}",
            "{title} à télécharger",
            "prends la série {title}",
            "ajoute {title} à sonarr",
            "télécharge tous les épisodes de {title}",
        ],
        tool="sonarr_search_series",
        tool_args_template={"query": "{query}"},
        tags=["sonarr", "téléchargement", "série"],
        category="media",
    ),
    # Queue
    PromptTemplate(
        patterns=[
            "épisodes en téléchargement",
            "queue sonarr",
            "séries en dl",
            "qu'est-ce qui télécharge en série",
            "état des downloads séries",
        ],
        tool="sonarr_get_queue",
        tool_args_template={},
        tags=["sonarr", "queue"],
        category="media",
    ),
    # Calendrier
    PromptTemplate(
        patterns=[
            "épisodes à venir",
            "prochains épisodes",
            "calendrier séries",
            "qu'est-ce qui sort cette semaine",
            "épisodes de la semaine",
            "sorties séries",
        ],
        tool="sonarr_get_calendar",
        tool_args_template={"days": 7},
        tags=["sonarr", "calendrier"],
        category="media",
    ),
]

# Prowlarr / Jackett - Indexeurs
INDEXER_TEMPLATES = [
    PromptTemplate(
        patterns=[
            "indexeurs prowlarr",
            "liste indexeurs",
            "sources prowlarr",
            "mes indexeurs",
        ],
        tool="prowlarr_get_indexers",
        tool_args_template={},
        tags=["prowlarr", "indexeur"],
        category="homelab",
    ),
    PromptTemplate(
        patterns=[
            "teste les indexeurs",
            "check indexeurs",
            "vérifie prowlarr",
            "test prowlarr",
        ],
        tool="prowlarr_test_all_indexers",
        tool_args_template={},
        tags=["prowlarr", "test"],
        category="homelab",
    ),
]

# Deluge - Torrents
DELUGE_TEMPLATES = [
    PromptTemplate(
        patterns=[
            "torrents",
            "mes torrents",
            "téléchargements torrent",
            "état torrents",
            "vitesse de dl",
            "qu'est-ce qui télécharge",
            "downloads en cours",
            "deluge status",
        ],
        tool="deluge_get_torrents",
        tool_args_template={},
        tags=["deluge", "torrent"],
        category="homelab",
    ),
]

# Overseerr - Demandes
OVERSEERR_TEMPLATES = [
    PromptTemplate(
        patterns=[
            "demande {title}",
            "request {title}",
            "je voudrais {title}",
            "{title} n'est pas dispo",
            "tu peux ajouter {title}",
            "fais une demande pour {title}",
        ],
        tool="overseerr_search_media",
        tool_args_template={"query": "{query}"},
        tags=["overseerr", "demande"],
        category="media",
    ),
    PromptTemplate(
        patterns=[
            "mes demandes",
            "demandes en attente",
            "état de mes requests",
            "requests overseerr",
        ],
        tool="overseerr_get_requests",
        tool_args_template={},
        tags=["overseerr", "demandes"],
        category="media",
    ),
]

# Wiki.js - Documentation
WIKIJS_TEMPLATES = [
    PromptTemplate(
        patterns=[
            "comment {topic}",
            "tuto {topic}",
            "guide {topic}",
            "doc {topic}",
            "howto {topic}",
            "documentation {topic}",
            "wiki {topic}",
            "aide {topic}",
            "{topic} comment faire",
        ],
        tool="wikijs_search",
        tool_args_template={"query": "{query}"},
        tags=["wikijs", "documentation"],
        category="homelab",
    ),
]

# System - Monitoring
SYSTEM_TEMPLATES = [
    PromptTemplate(
        patterns=[
            "état du serveur",
            "ça va le serveur",
            "tout fonctionne",
            "health check",
            "status",
            "le serveur est ok",
        ],
        tool="system_get_health",
        tool_args_template={},
        tags=["system", "santé"],
        category="homelab",
    ),
    PromptTemplate(
        patterns=[
            "cpu",
            "ram",
            "mémoire",
            "charge serveur",
            "ressources",
            "température",
            "espace disque",
        ],
        tool="system_get_metrics",
        tool_args_template={},
        tags=["system", "métriques"],
        category="homelab",
    ),
    PromptTemplate(
        patterns=[
            "services",
            "quels services",
            "état des services",
            "services actifs",
            "docker status",
        ],
        tool="system_get_services",
        tool_args_template={},
        tags=["system", "services"],
        category="homelab",
    ),
]

# ============================================================================
# DONNÉES DE REMPLACEMENT
# ============================================================================

TITLES_AUDIOBOOK = [
    "Harry Potter", "Le Seigneur des Anneaux", "Dune", "1984", "Le Petit Prince",
    "L'Étranger", "Les Misérables", "Fondation", "Fahrenheit 451", "Le Hobbit",
    "Sapiens", "Le Parfum", "L'Alchimiste", "Le Comte de Monte-Cristo",
    "Da Vinci Code", "Hunger Games", "Game of Thrones", "Twilight",
    "Le Nom du Vent", "Eragon", "La Passe-Miroir", "Ender's Game",
    "Ready Player One", "The Martian", "Project Hail Mary",
    "Brandon Sanderson", "Stephen King", "Lovecraft", "Agatha Christie",
]

TITLES_MOVIE = [
    "Inception", "The Matrix", "Interstellar", "Oppenheimer", "Barbie",
    "Avatar", "Dune", "Gladiator", "Titanic", "Pulp Fiction",
    "The Dark Knight", "Fight Club", "Forrest Gump", "The Godfather",
    "Star Wars", "Jurassic Park", "The Avengers", "Spider-Man",
    "Joker", "Parasite", "Alien", "Terminator", "The Lion King",
    "Toy Story", "Shrek", "Finding Nemo", "John Wick", "Top Gun",
    "Everything Everywhere All at Once", "The Batman", "Black Panther",
    "Deadpool", "Guardians of the Galaxy", "Thor", "Iron Man",
]

TITLES_SHOW = [
    "Breaking Bad", "Game of Thrones", "The Bear", "Stranger Things",
    "The Office", "Friends", "House of the Dragon", "The Mandalorian",
    "The Last of Us", "Wednesday", "Squid Game", "Peaky Blinders",
    "The Crown", "Narcos", "Better Call Saul", "True Detective",
    "The Boys", "Succession", "Ted Lasso", "Yellowstone",
    "The Witcher", "Arcane", "Severance", "Shogun", "Fallout",
    "3 Body Problem", "The Penguin", "Andor", "Slow Horses",
]

TITLES_MANGA = [
    "One Piece", "Naruto", "Dragon Ball", "Attack on Titan", "Death Note",
    "Demon Slayer", "My Hero Academia", "Jujutsu Kaisen", "Chainsaw Man",
    "One Punch Man", "Hunter x Hunter", "Bleach", "Fullmetal Alchemist",
    "Berserk", "Tokyo Ghoul", "Spy x Family", "Mob Psycho 100",
    "Vinland Saga", "Kingdom", "Solo Leveling", "Blue Lock",
    "Kaiju No 8", "Dandadan", "Sakamoto Days",
]

TITLES_COMIC = [
    "Batman", "Spider-Man", "X-Men", "Avengers", "Superman", "Wonder Woman",
    "The Walking Dead", "Saga", "Sandman", "Watchmen", "V for Vendetta",
    "Astérix", "Tintin", "Lucky Luke", "Blake et Mortimer", "Largo Winch",
    "Blacksad", "Thorgal", "XIII", "Lanfeust",
]

TITLES_GAME = [
    "Mario Kart", "Super Mario Bros", "Zelda", "Pokemon", "Metroid",
    "Sonic", "Street Fighter", "Mortal Kombat", "Final Fantasy",
    "Resident Evil", "Metal Gear Solid", "Castlevania", "Mega Man",
    "Donkey Kong", "Kirby", "F-Zero", "Star Fox", "Earthbound",
    "Chrono Trigger", "Secret of Mana", "Contra", "Tetris",
    "GoldenEye", "Perfect Dark", "Banjo-Kazooie", "Smash Bros",
]

PLATFORMS = [
    ("nintendo 64", "n64"), ("playstation", "psx"), ("ps2", "ps2"),
    ("super nintendo", "snes"), ("nes", "nes"), ("game boy", "gb"),
    ("game boy advance", "gba"), ("mega drive", "megadrive"),
    ("dreamcast", "dreamcast"), ("gamecube", "gamecube"),
    ("wii", "wii"), ("ds", "nds"), ("psp", "psp"),
]

GENRES_MOVIE = [
    "action", "comédie", "drame", "thriller", "horreur", "science fiction",
    "fantastique", "animation", "documentaire", "romance", "aventure",
    "super héros", "guerre", "western", "musical",
]

WIKI_TOPICS = [
    "docker", "reverse proxy", "ssl", "nginx", "traefik", "vpn",
    "backup", "raid", "ssh", "firewall", "portainer", "watchtower",
    "authentification", "ldap", "base de données", "monitoring",
    "grafana", "prometheus", "alertes", "notifications",
]

AUTHORS = [
    "Stephen King", "Brandon Sanderson", "Lovecraft", "Agatha Christie",
    "Isaac Asimov", "Philip K. Dick", "Terry Pratchett", "Neil Gaiman",
    "Patrick Rothfuss", "Joe Abercrombie", "Robin Hobb", "Ursula K. Le Guin",
]

# ============================================================================
# CAS DE DISTINCTION (ambiguïtés)
# ============================================================================

DISTINCTION_CASES = [
    # Audio vs Vidéo - même titre
    {
        "scenario": "écouter vs regarder",
        "patterns_audio": [
            "j'veux écouter {title}",
            "mets {title} en audio",
            "{title} en audiobook",
            "{title} à écouter",
            "le livre {title}",
            "{title} version audio",
            "écoute {title}",
        ],
        "patterns_video": [
            "j'veux regarder {title}",
            "mets {title}",
            "{title} le film",
            "{title} à voir",
            "voir {title}",
            "mater {title}",
            "le film {title}",
        ],
        "tool_audio": "audiobookshelf_search",
        "tool_video": "plex_search_media",
        "titles": ["Harry Potter", "Dune", "Le Seigneur des Anneaux", "Game of Thrones", "The Martian", "1984"],
    },
    # Manga vs Anime
    {
        "scenario": "lire vs regarder anime",
        "patterns_read": [
            "lire {title}",
            "{title} manga",
            "le manga {title}",
            "{title} scan",
            "{title} tome",
            "{title} à lire",
        ],
        "patterns_watch": [
            "regarder {title}",
            "{title} anime",
            "l'anime {title}",
            "{title} épisode",
            "{title} saison",
            "{title} à voir",
        ],
        "tool_read": "komga_search",
        "tool_watch": "plex_search_media",
        "titles": ["One Piece", "Naruto", "Dragon Ball", "Attack on Titan", "Death Note", "Demon Slayer"],
    },
    # Film vs Série téléchargement
    {
        "scenario": "télécharger film vs série",
        "patterns_movie": [
            "télécharge le film {title}",
            "dl le film {title}",
            "ajoute le film {title}",
            "récupère le film {title}",
        ],
        "patterns_series": [
            "télécharge la série {title}",
            "dl la série {title}",
            "ajoute la série {title}",
            "récupère la série {title}",
        ],
        "tool_movie": "radarr_search_movie",
        "tool_series": "sonarr_search_series",
        "titles": ["The Batman", "Breaking Bad", "Oppenheimer", "Stranger Things"],
    },
]

# ============================================================================
# GÉNÉRATION
# ============================================================================

def add_natural_variations(text: str) -> List[str]:
    """Ajoute des variations naturelles à un texte."""
    variations = [text]

    # Version lowercase
    variations.append(text.lower())

    # Version sans accents (simulation erreur)
    no_accents = text.replace("é", "e").replace("è", "e").replace("ê", "e")
    no_accents = no_accents.replace("à", "a").replace("ù", "u").replace("î", "i")
    if no_accents != text:
        variations.append(no_accents)

    # Ajouter politesse aléatoire
    for p in random.sample(POLITENESS, min(2, len(POLITENESS))):
        if p:
            variations.append(text + p)

    return variations


def generate_tool_response(tool_name: str, query: str = "") -> Dict[str, Any]:
    """Génère une réponse simulée pour un outil."""
    responses = {
        "audiobookshelf_search": {"items": [{"title": query or "Audiobook", "author": "Auteur", "duration": "10h"}]},
        "audiobookshelf_get_libraries": {"libraries": [{"name": "Audiobooks", "itemCount": 150}]},
        "audiobookshelf_get_media_progress": {"items": [{"title": "En cours", "progress": 45}]},
        "plex_search_media": {"results": [{"title": query or "Média", "year": 2024, "type": "movie"}]},
        "plex_get_recently_added": {"items": [{"title": "Récent", "type": "movie"}]},
        "plex_get_on_deck": {"items": [{"title": "En cours", "progress": "45%"}]},
        "plex_get_libraries": {"libraries": [{"name": "Films", "count": 500}]},
        "plex_get_active_sessions": {"sessions": []},
        "tautulli_get_activity": {"stream_count": 0, "sessions": []},
        "tautulli_get_history": {"history": [{"title": "Film", "user": "User"}]},
        "tautulli_get_statistics": {"totalPlays": 1500},
        "komga_search": {"results": [{"name": query or "Manga", "booksCount": 50}]},
        "komga_get_libraries": {"libraries": [{"name": "Manga", "booksCount": 300}]},
        "romm_search_roms": {"roms": [{"name": query or "Jeu", "platform": "N64"}]},
        "romm_get_platforms": {"platforms": [{"name": "Nintendo 64", "slug": "n64", "rom_count": 50}]},
        "romm_get_roms": {"roms": [{"name": "Jeu", "platform": "N64"}]},
        "radarr_search_movie": {"movies": [{"title": query or "Film", "year": 2024}]},
        "radarr_get_queue": {"records": []},
        "radarr_get_calendar": {"movies": [{"title": "Film à venir"}]},
        "sonarr_search_series": {"series": [{"title": query or "Série", "year": 2024}]},
        "sonarr_get_queue": {"records": []},
        "sonarr_get_calendar": {"episodes": [{"title": "S01E05"}]},
        "prowlarr_get_indexers": {"indexers": [{"name": "1337x", "enabled": True}]},
        "prowlarr_test_all_indexers": {"results": [{"indexer": "1337x", "success": True}]},
        "deluge_get_torrents": {"torrents": []},
        "overseerr_search_media": {"results": [{"title": query or "Média"}]},
        "overseerr_get_requests": {"requests": []},
        "wikijs_search": {"results": [{"title": "Guide " + (query or "Topic")}]},
        "system_get_health": {"status": "healthy"},
        "system_get_metrics": {"cpu_usage": "25%", "memory_usage": "45%"},
        "system_get_services": {"services": [{"name": "Plex", "status": "running"}]},
    }
    return responses.get(tool_name, {"result": "ok"})


def generate_assistant_response(tool_name: str, query: str = "") -> str:
    """Génère une réponse assistant naturelle."""
    responses = {
        "audiobookshelf_search": f"J'ai trouvé \"{query}\" dans ta bibliothèque audio.",
        "audiobookshelf_get_libraries": "Voici tes bibliothèques audio.",
        "audiobookshelf_get_media_progress": "Voici ta progression.",
        "plex_search_media": f"\"{query}\" est disponible.",
        "plex_get_recently_added": "Voici les derniers ajouts.",
        "plex_get_on_deck": "Voici ce que tu regardais.",
        "plex_get_libraries": "Voici tes bibliothèques.",
        "plex_get_active_sessions": "Personne ne regarde actuellement.",
        "tautulli_get_activity": "Pas d'activité en cours.",
        "tautulli_get_history": "Voici l'historique.",
        "tautulli_get_statistics": "Voici les statistiques.",
        "komga_search": f"\"{query}\" trouvé dans Komga.",
        "komga_get_libraries": "Voici tes bibliothèques BD.",
        "romm_search_roms": f"ROM \"{query}\" trouvée.",
        "romm_get_platforms": "Voici les plateformes disponibles.",
        "romm_get_roms": "Voici les ROMs.",
        "radarr_search_movie": f"\"{query}\" trouvé. Je peux l'ajouter à ta collection.",
        "radarr_get_queue": "Pas de téléchargement en cours.",
        "radarr_get_calendar": "Voici les prochaines sorties.",
        "sonarr_search_series": f"\"{query}\" trouvé. Je peux l'ajouter.",
        "sonarr_get_queue": "Pas de téléchargement en cours.",
        "sonarr_get_calendar": "Voici les prochains épisodes.",
        "prowlarr_get_indexers": "Voici tes indexeurs.",
        "prowlarr_test_all_indexers": "Tous les indexeurs fonctionnent.",
        "deluge_get_torrents": "Pas de torrent actif.",
        "overseerr_search_media": f"\"{query}\" trouvé. Je peux créer une demande.",
        "overseerr_get_requests": "Voici tes demandes.",
        "wikijs_search": f"Documentation trouvée pour \"{query}\".",
        "system_get_health": "Le serveur fonctionne correctement.",
        "system_get_metrics": "Voici les métriques système.",
        "system_get_services": "Voici l'état des services.",
    }
    return responses.get(tool_name, "Opération effectuée.")


def create_prompt_entry(
    name: str,
    user_input: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    category: str,
    tags: List[str],
) -> Dict[str, Any]:
    """Crée une entrée de prompt pour l'import."""
    query = tool_args.get("query", "")
    return {
        "name": name[:200],
        "description": f"Prompt haute qualité pour {tool_name}",
        "category": category,
        "difficulty": "basic",
        "source": "generated_quality",
        "format": "chat",
        "system_prompt": SYSTEM_PROMPT,
        "user_input": user_input,
        "tool_call": {"name": tool_name, "arguments": tool_args},
        "tool_response": generate_tool_response(tool_name, query),
        "assistant_response": generate_assistant_response(tool_name, query),
        "expected_output": "",
        "tags": tags,
        "enabled": True,
    }


def generate_from_template(template: PromptTemplate, titles: List[str], limit: int = None) -> List[Dict]:
    """Génère des prompts à partir d'un template."""
    prompts = []

    for pattern in template.patterns:
        if "{title}" in pattern or "{query}" in pattern:
            # Pattern avec titre
            selected_titles = titles[:limit] if limit else titles
            for title in selected_titles:
                user_input = pattern.replace("{title}", title).replace("{query}", title)
                for variant in add_natural_variations(user_input):
                    tool_args = {}
                    for key, val in template.tool_args_template.items():
                        if isinstance(val, str):
                            tool_args[key] = val.replace("{query}", title)
                        else:
                            tool_args[key] = val

                    prompts.append(create_prompt_entry(
                        f"{template.tool} - {variant[:150]}",
                        variant,
                        template.tool,
                        tool_args,
                        template.category,
                        template.tags,
                    ))
        elif "{author}" in pattern:
            # Pattern avec auteur
            for author in AUTHORS[:10]:
                user_input = pattern.replace("{author}", author)
                tool_args = {"query": author}
                prompts.append(create_prompt_entry(
                    f"{template.tool} - {user_input[:150]}",
                    user_input,
                    template.tool,
                    tool_args,
                    template.category,
                    template.tags,
                ))
        elif "{genre}" in pattern:
            # Pattern avec genre
            for genre in GENRES_MOVIE:
                user_input = pattern.replace("{genre}", genre)
                tool_args = dict(template.tool_args_template)
                tool_args["query"] = genre
                prompts.append(create_prompt_entry(
                    f"{template.tool} - {user_input[:150]}",
                    user_input,
                    template.tool,
                    tool_args,
                    template.category,
                    template.tags,
                ))
        elif "{topic}" in pattern:
            # Pattern avec topic wiki
            for topic in WIKI_TOPICS:
                user_input = pattern.replace("{topic}", topic)
                tool_args = {"query": topic}
                prompts.append(create_prompt_entry(
                    f"{template.tool} - {user_input[:150]}",
                    user_input,
                    template.tool,
                    tool_args,
                    template.category,
                    template.tags,
                ))
        elif "{platform}" in pattern:
            # Pattern avec plateforme
            for platform_name, platform_id in PLATFORMS:
                user_input = pattern.replace("{platform}", platform_name)
                tool_args = dict(template.tool_args_template)
                if "{platform_id}" in str(tool_args):
                    tool_args = {k: v.replace("{platform_id}", platform_id) if isinstance(v, str) else v
                                for k, v in tool_args.items()}
                prompts.append(create_prompt_entry(
                    f"{template.tool} - {user_input[:150]}",
                    user_input,
                    template.tool,
                    tool_args,
                    template.category,
                    template.tags,
                ))
        else:
            # Pattern simple sans variable
            for variant in add_natural_variations(pattern):
                prompts.append(create_prompt_entry(
                    f"{template.tool} - {variant[:150]}",
                    variant,
                    template.tool,
                    dict(template.tool_args_template),
                    template.category,
                    template.tags,
                ))

    return prompts


def generate_distinction_prompts() -> List[Dict]:
    """Génère les prompts de distinction (cas ambigus)."""
    prompts = []

    for case in DISTINCTION_CASES:
        titles = case["titles"]

        # Prompts audio/lecture
        if "patterns_audio" in case:
            for pattern in case["patterns_audio"]:
                for title in titles:
                    user_input = pattern.replace("{title}", title)
                    prompts.append(create_prompt_entry(
                        f"Distinction audio - {user_input[:140]}",
                        user_input,
                        case["tool_audio"],
                        {"query": title},
                        "media",
                        ["distinction", "audio", "écouter"],
                    ))

        if "patterns_read" in case:
            for pattern in case["patterns_read"]:
                for title in titles:
                    user_input = pattern.replace("{title}", title)
                    prompts.append(create_prompt_entry(
                        f"Distinction lire - {user_input[:140]}",
                        user_input,
                        case["tool_read"],
                        {"query": title},
                        "media",
                        ["distinction", "lire", "manga"],
                    ))

        # Prompts vidéo
        if "patterns_video" in case:
            for pattern in case["patterns_video"]:
                for title in titles:
                    user_input = pattern.replace("{title}", title)
                    tool_args = {"query": title}
                    if case["tool_video"] == "plex_search_media":
                        tool_args["media_type"] = "movie"
                    prompts.append(create_prompt_entry(
                        f"Distinction vidéo - {user_input[:140]}",
                        user_input,
                        case["tool_video"],
                        tool_args,
                        "media",
                        ["distinction", "vidéo", "regarder"],
                    ))

        if "patterns_watch" in case:
            for pattern in case["patterns_watch"]:
                for title in titles:
                    user_input = pattern.replace("{title}", title)
                    tool_args = {"query": title}
                    if case["tool_watch"] == "plex_search_media":
                        tool_args["media_type"] = "show"
                    prompts.append(create_prompt_entry(
                        f"Distinction anime - {user_input[:140]}",
                        user_input,
                        case["tool_watch"],
                        tool_args,
                        "media",
                        ["distinction", "anime", "regarder"],
                    ))

        # Prompts film vs série téléchargement
        if "patterns_movie" in case:
            for pattern in case["patterns_movie"]:
                for title in titles:
                    user_input = pattern.replace("{title}", title)
                    prompts.append(create_prompt_entry(
                        f"Distinction film dl - {user_input[:140]}",
                        user_input,
                        case["tool_movie"],
                        {"query": title},
                        "media",
                        ["distinction", "radarr", "film"],
                    ))

        if "patterns_series" in case:
            for pattern in case["patterns_series"]:
                for title in titles:
                    user_input = pattern.replace("{title}", title)
                    prompts.append(create_prompt_entry(
                        f"Distinction série dl - {user_input[:140]}",
                        user_input,
                        case["tool_series"],
                        {"query": title},
                        "media",
                        ["distinction", "sonarr", "série"],
                    ))

    return prompts


def generate_all_prompts() -> List[Dict]:
    """Génère tous les prompts de haute qualité."""
    prompts = []

    print("Génération des prompts Audiobookshelf...")
    for template in AUDIOBOOKSHELF_TEMPLATES:
        prompts.extend(generate_from_template(template, TITLES_AUDIOBOOK))

    print("Génération des prompts Plex...")
    for template in PLEX_TEMPLATES:
        if "film" in template.tags:
            prompts.extend(generate_from_template(template, TITLES_MOVIE))
        elif "série" in template.tags:
            prompts.extend(generate_from_template(template, TITLES_SHOW))
        else:
            prompts.extend(generate_from_template(template, []))

    print("Génération des prompts Tautulli...")
    for template in TAUTULLI_TEMPLATES:
        prompts.extend(generate_from_template(template, []))

    print("Génération des prompts Komga...")
    for template in KOMGA_TEMPLATES:
        all_titles = TITLES_MANGA + TITLES_COMIC
        prompts.extend(generate_from_template(template, all_titles))

    print("Génération des prompts RomM...")
    for template in ROMM_TEMPLATES:
        prompts.extend(generate_from_template(template, TITLES_GAME))

    print("Génération des prompts Radarr...")
    for template in RADARR_TEMPLATES:
        prompts.extend(generate_from_template(template, TITLES_MOVIE))

    print("Génération des prompts Sonarr...")
    for template in SONARR_TEMPLATES:
        prompts.extend(generate_from_template(template, TITLES_SHOW))

    print("Génération des prompts Indexeurs...")
    for template in INDEXER_TEMPLATES:
        prompts.extend(generate_from_template(template, []))

    print("Génération des prompts Deluge...")
    for template in DELUGE_TEMPLATES:
        prompts.extend(generate_from_template(template, []))

    print("Génération des prompts Overseerr...")
    for template in OVERSEERR_TEMPLATES:
        prompts.extend(generate_from_template(template, TITLES_MOVIE[:15]))

    print("Génération des prompts Wiki.js...")
    for template in WIKIJS_TEMPLATES:
        prompts.extend(generate_from_template(template, []))

    print("Génération des prompts System...")
    for template in SYSTEM_TEMPLATES:
        prompts.extend(generate_from_template(template, []))

    print("Génération des prompts de distinction...")
    prompts.extend(generate_distinction_prompts())

    # Dédupliquer par user_input
    seen = set()
    unique_prompts = []
    for p in prompts:
        key = p["user_input"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_prompts.append(p)

    print(f"\nTotal prompts générés: {len(prompts)}")
    print(f"Total prompts uniques: {len(unique_prompts)}")

    return unique_prompts


def main():
    prompts = generate_all_prompts()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    print(f"\nFichier généré: {OUTPUT_FILE}")
    print(f"Taille: {len(prompts)} prompts")

    # Stats par service
    stats = {}
    for p in prompts:
        tool = p["tool_call"]["name"].split("_")[0]
        stats[tool] = stats.get(tool, 0) + 1

    print("\nRépartition par service:")
    for service, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {service}: {count}")


if __name__ == "__main__":
    main()
