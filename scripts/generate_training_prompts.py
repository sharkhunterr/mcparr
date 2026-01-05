#!/usr/bin/env python3
"""
Script pour générer un fichier JSON de prompts d'entraînement à importer via l'IHM.
Génère 500+ prompts variés pour couvrir toutes les formulations possibles.
"""

import json
from typing import List, Dict, Any

OUTPUT_FILE = "/home/jeremie/Documents/Developpement/mcparr/training_prompts_import.json"

SYSTEM_PROMPT = "Tu es MCParr, un assistant IA pour homelab. Tu aides l'utilisateur à gérer ses services média et infrastructure."

# ============================================================================
# TEMPLATES DE PROMPTS PAR SERVICE
# ============================================================================

PROMPTS_DATA = {
    # ========================================================================
    # AUDIOBOOKSHELF - Livres audio, podcasts, audiobooks
    # ========================================================================
    "audiobookshelf": {
        "search": [
            "Cherche le livre audio {title}",
            "Tu as l'audiobook de {title} ?",
            "Je cherche {title} en audio",
            "Trouve-moi {title} à écouter",
            "Y a {title} en livre audio ?",
            "{title} est dispo en audiobook ?",
            "Je veux écouter {title}",
            "Où est le livre audio {title} ?",
            "Audiobook {title} disponible ?",
            "Version audio de {title} ?",
            "Tu peux me trouver {title} en audio ?",
            "{title} en version narrée ?",
            "Le livre {title} est lu par qui ?",
            "J'aimerais écouter {title}",
            "Mets-moi {title} en audio",
            "Livre audio {title} svp",
            "Recherche audiobook {title}",
        ],
        "titles": [
            "Harry Potter", "Le Seigneur des Anneaux", "Dune", "1984", "Le Petit Prince",
            "L'Étranger", "Les Misérables", "Game of Thrones", "Fondation", "Fahrenheit 451",
            "Hunger Games", "Twilight", "Da Vinci Code", "Le Comte de Monte-Cristo", "Germinal",
            "Le Hobbit", "Sapiens", "Le Parfum", "L'Alchimiste", "Candide",
        ],
        "libraries": [
            "Montre mes livres audio",
            "Mes audiobooks ?",
            "Liste mes bibliothèques audio",
            "Qu'est-ce que j'ai en audio ?",
            "Bibliothèque Audiobookshelf",
            "Tous mes livres audio",
            "Combien de livres audio j'ai ?",
            "Collection audiobooks",
        ],
        "podcasts": [
            "Mes podcasts ?",
            "Liste les podcasts",
            "Quels podcasts j'ai ?",
            "Montre mes podcasts",
            "Podcasts disponibles ?",
            "Je veux écouter un podcast",
            "Podcasts Audiobookshelf",
        ],
        "progress": [
            "Où j'en suis dans mon livre ?",
            "Ma progression d'écoute ?",
            "Qu'est-ce que j'écoutais ?",
            "Reprendre mon livre audio",
            "Continuer mon audiobook",
            "J'en étais où dans mon livre ?",
            "Progression audiobook",
        ],
        "stats": [
            "Stats Audiobookshelf",
            "Statistiques d'écoute",
            "Combien j'ai écouté ?",
            "Mon temps d'écoute total",
            "Statistiques audiobooks",
        ],
    },

    # ========================================================================
    # PLEX - Films, séries TV, vidéo
    # ========================================================================
    "plex": {
        "search_movie": [
            "Cherche le film {title}",
            "Tu as le film {title} ?",
            "Je veux regarder {title}",
            "{title} est disponible ?",
            "Trouve {title} sur Plex",
            "Film {title} dispo ?",
            "On peut voir {title} ?",
            "Mets {title}",
            "Lance {title}",
            "Je cherche le film {title}",
            "{title} c'est sur Plex ?",
            "Y a {title} ?",
            "Vidéo {title} ?",
            "Streaming {title} ?",
            "Le {title} est téléchargé ?",
            "Tu as {title} en vidéo ?",
        ],
        "search_show": [
            "Tu as la série {title} ?",
            "Cherche la série {title}",
            "Série {title} disponible ?",
            "Je veux regarder la série {title}",
            "{title} combien de saisons ?",
            "On a {title} en entier ?",
            "Trouve la série {title}",
            "Épisodes de {title} ?",
            "{title} saison complète ?",
            "Série TV {title}",
            "Show {title} dispo ?",
        ],
        "movies": [
            "Avatar", "Inception", "The Matrix", "Interstellar", "Oppenheimer",
            "Barbie", "Dune", "Gladiator", "Titanic", "Pulp Fiction",
            "The Dark Knight", "Fight Club", "Forrest Gump", "The Godfather",
            "Star Wars", "Jurassic Park", "The Avengers", "Spider-Man",
            "Joker", "Parasite", "Alien", "Terminator", "E.T.", "The Lion King",
            "Toy Story", "Shrek", "Finding Nemo", "The Incredibles",
        ],
        "shows": [
            "Breaking Bad", "Game of Thrones", "The Bear", "Stranger Things",
            "The Office", "Friends", "House of the Dragon", "The Mandalorian",
            "The Last of Us", "Wednesday", "Squid Game", "Peaky Blinders",
            "The Crown", "Narcos", "Better Call Saul", "True Detective",
            "The Boys", "Succession", "Ted Lasso", "Yellowstone",
            "The Witcher", "Arcane", "Severance", "Rings of Power",
        ],
        "recently_added": [
            "Quoi de neuf sur Plex ?",
            "Derniers ajouts ?",
            "Nouveautés Plex ?",
            "Films récemment ajoutés",
            "Qu'est-ce qui est nouveau ?",
            "Derniers films ajoutés",
            "Nouvelles séries ?",
            "Récemment téléchargé ?",
            "Ajouts récents Plex",
        ],
        "on_deck": [
            "Qu'est-ce que je regardais ?",
            "Continuer à regarder",
            "Reprendre mon film",
            "J'en étais où ?",
            "Mes films en cours",
            "Séries en cours",
            "On deck Plex",
        ],
        "libraries": [
            "Mes bibliothèques Plex",
            "Combien de films j'ai ?",
            "Liste les bibliothèques",
            "Qu'est-ce que j'ai sur Plex ?",
            "Stats Plex ?",
            "Collection Plex",
        ],
        "sessions": [
            "Qui regarde quoi ?",
            "Streams actifs ?",
            "Qui utilise Plex ?",
            "Sessions en cours",
            "Sessions actives Plex",
        ],
    },

    # ========================================================================
    # TAUTULLI - Stats et monitoring Plex
    # ========================================================================
    "tautulli": {
        "activity": [
            "Qui regarde quoi en ce moment ?",
            "Activité Plex ?",
            "Streams en cours ?",
            "Qui est connecté à Plex ?",
            "Combien de personnes regardent ?",
            "Y a du monde sur Plex ?",
            "Sessions Plex actives",
            "Qui streame ?",
            "Activité streaming",
        ],
        "history": [
            "Historique Plex",
            "Qu'est-ce qui a été regardé ?",
            "Films vus récemment",
            "Historique de visionnage",
            "Derniers films regardés",
            "Qui a regardé quoi ?",
            "Historique Tautulli",
        ],
        "stats": [
            "Stats Tautulli",
            "Statistiques Plex",
            "Combien de temps de visionnage ?",
            "Films les plus regardés",
            "Top séries",
            "Statistiques streaming",
        ],
    },

    # ========================================================================
    # KOMGA - Comics, mangas, BD
    # ========================================================================
    "komga": {
        "search": [
            "Tu as le manga {title} ?",
            "Cherche {title} dans Komga",
            "BD {title} disponible ?",
            "Je veux lire {title}",
            "Comic {title} ?",
            "Trouve le manga {title}",
            "{title} combien de tomes ?",
            "Bande dessinée {title}",
            "Le comic {title} est dispo ?",
            "Recherche BD {title}",
            "{title} sur Komga ?",
            "Je cherche {title} à lire",
            "Manga {title} ?",
            "Y a {title} en BD ?",
            "Série {title} manga ?",
        ],
        "titles": [
            "One Piece", "Naruto", "Dragon Ball", "Attack on Titan", "Death Note",
            "Demon Slayer", "My Hero Academia", "Jujutsu Kaisen", "Chainsaw Man",
            "One Punch Man", "Hunter x Hunter", "Bleach", "Fullmetal Alchemist",
            "Batman", "Spider-Man", "X-Men", "Avengers", "Superman", "Wonder Woman",
            "Astérix", "Tintin", "Lucky Luke", "Blake et Mortimer", "Largo Winch",
            "The Walking Dead", "Saga", "Sandman", "Watchmen", "V for Vendetta",
            "Berserk", "Tokyo Ghoul", "Spy x Family", "Mob Psycho 100",
        ],
        "libraries": [
            "Mes BD ?",
            "Bibliothèques Komga",
            "Combien de mangas j'ai ?",
            "Liste mes comics",
            "Mes bandes dessinées",
            "Collections Komga",
            "Collection BD",
        ],
        "stats": [
            "Stats Komga",
            "Statistiques BD",
            "Combien de BD j'ai lu ?",
            "Statistiques manga",
        ],
    },

    # ========================================================================
    # ROMM - ROMs et jeux rétro
    # ========================================================================
    "romm": {
        "search": [
            "Tu as {title} ?",
            "Cherche le jeu {title}",
            "ROM {title} ?",
            "Je veux jouer à {title}",
            "{title} sur quelle console ?",
            "Trouve {title}",
            "Jeu {title} disponible ?",
            "Y a {title} en ROM ?",
            "Le jeu {title} ?",
            "ROM de {title} ?",
        ],
        "games": [
            "Mario Kart", "Super Mario Bros", "Zelda", "Pokemon", "Metroid",
            "Sonic", "Street Fighter", "Mortal Kombat", "Final Fantasy",
            "Resident Evil", "Metal Gear Solid", "Castlevania", "Mega Man",
            "Donkey Kong", "Kirby", "F-Zero", "Star Fox", "Earthbound",
            "Chrono Trigger", "Secret of Mana", "Contra", "Gradius",
            "Tetris", "Pac-Man", "Space Invaders", "Galaga",
        ],
        "platforms": [
            "Quelles consoles tu as ?",
            "Liste les plateformes",
            "Consoles disponibles ?",
            "Émulateurs dispo ?",
            "Mes consoles rétro",
            "Plateformes RomM",
            "Quels émulateurs ?",
        ],
        "platform_queries": [
            ("Jeux Nintendo 64 ?", "n64"),
            ("ROMs PlayStation ?", "psx"),
            ("Jeux GameCube", "gamecube"),
            ("ROMs Super Nintendo", "snes"),
            ("Jeux Game Boy ?", "gb"),
            ("ROMs NES", "nes"),
            ("Jeux Mega Drive", "megadrive"),
            ("ROMs Dreamcast", "dreamcast"),
            ("Jeux PS2", "ps2"),
            ("ROMs GBA", "gba"),
        ],
        "collections": [
            "Mes collections de jeux",
            "Collections RomM",
            "Jeux favoris ?",
            "Ma liste de jeux",
            "Collection jeux rétro",
        ],
        "stats": [
            "Stats RomM",
            "Combien de jeux j'ai ?",
            "Statistiques jeux rétro",
            "Statistiques ROMs",
        ],
    },

    # ========================================================================
    # RADARR - Téléchargement films
    # ========================================================================
    "radarr": {
        "search": [
            "Télécharge {title}",
            "Ajoute le film {title}",
            "Je veux {title}",
            "Dl {title}",
            "Download {title}",
            "Récupère {title}",
            "Ajoute {title} à Radarr",
            "Film {title} à télécharger",
            "Met {title} en téléchargement",
            "Cherche {title} sur Radarr",
            "Télécharger le film {title}",
        ],
        "movies": [
            "Oppenheimer", "Barbie", "Dune Part Two", "Deadpool 3",
            "Inside Out 2", "Gladiator 2", "Joker 2", "Beetlejuice 2",
            "Furiosa", "Godzilla x Kong", "Kung Fu Panda 4", "Bad Boys 4",
            "Twisters", "Alien Romulus", "Venom 3", "Kraven the Hunter",
        ],
        "queue": [
            "Films en téléchargement ?",
            "Queue Radarr ?",
            "Qu'est-ce qui télécharge ?",
            "Téléchargements en cours",
            "État des téléchargements films",
            "File d'attente Radarr",
            "Downloads films",
        ],
        "calendar": [
            "Films à venir ?",
            "Calendrier Radarr",
            "Prochaines sorties films",
            "Films qui sortent bientôt",
            "Sorties ciné",
        ],
        "library": [
            "Films dans Radarr ?",
            "Ma collection Radarr",
            "Liste des films",
            "Combien de films dans Radarr ?",
            "Bibliothèque Radarr",
        ],
        "indexers": [
            "Indexeurs Radarr ?",
            "Liste indexeurs Radarr",
            "Quels indexeurs dans Radarr ?",
            "Sources Radarr",
        ],
        "test_indexers": [
            "Teste les indexeurs de Radarr",
            "Test indexeurs Radarr",
            "Vérifie les indexeurs Radarr",
            "Check indexeurs Radarr",
        ],
        "stats": [
            "Stats Radarr",
            "Statistiques Radarr",
            "Combien de films Radarr ?",
        ],
    },

    # ========================================================================
    # SONARR - Téléchargement séries
    # ========================================================================
    "sonarr": {
        "search": [
            "Télécharge la série {title}",
            "Ajoute {title} à Sonarr",
            "Je veux la série {title}",
            "Dl la série {title}",
            "Ajoute la série {title}",
            "Série {title} à télécharger",
            "Met {title} en téléchargement",
            "Récupère {title}",
            "Télécharger la série {title}",
        ],
        "shows": [
            "The Bear", "House of the Dragon", "The Boys", "Fallout",
            "Shogun", "3 Body Problem", "True Detective", "Fargo",
            "The Penguin", "Agatha All Along", "Daredevil Born Again",
            "Andor", "The Diplomat", "Slow Horses", "For All Mankind",
        ],
        "queue": [
            "Séries en téléchargement ?",
            "Queue Sonarr ?",
            "Épisodes en téléchargement",
            "Téléchargements séries",
            "File d'attente Sonarr",
            "Downloads séries",
        ],
        "calendar": [
            "Épisodes à venir ?",
            "Calendrier Sonarr",
            "Quels épisodes sortent ?",
            "Prochains épisodes",
            "Sorties de la semaine",
            "Épisodes cette semaine",
            "Prochaines sorties séries",
        ],
        "library": [
            "Séries dans Sonarr ?",
            "Ma collection Sonarr",
            "Liste des séries",
            "Combien de séries ?",
            "Bibliothèque Sonarr",
        ],
        "indexers": [
            "Indexeurs Sonarr ?",
            "Liste indexeurs Sonarr",
            "Sources Sonarr",
        ],
        "test_indexers": [
            "Teste les indexeurs de Sonarr",
            "Test indexeurs Sonarr",
            "Vérifie les indexeurs Sonarr",
            "Check indexeurs Sonarr",
        ],
        "stats": [
            "Stats Sonarr",
            "Statistiques Sonarr",
            "Combien de séries Sonarr ?",
        ],
    },

    # ========================================================================
    # PROWLARR - Indexeurs centralisés
    # ========================================================================
    "prowlarr": {
        "indexers": [
            "Liste mes indexeurs Prowlarr",
            "Indexeurs Prowlarr ?",
            "Quels indexeurs dans Prowlarr ?",
            "Mes sources Prowlarr",
            "Indexeurs disponibles Prowlarr",
        ],
        "test_indexers": [
            "Teste les indexeurs Prowlarr",
            "Test Prowlarr",
            "Vérifie indexeurs Prowlarr",
            "Check indexeurs Prowlarr",
        ],
        "stats": [
            "Stats Prowlarr",
            "Statistiques Prowlarr",
        ],
    },

    # ========================================================================
    # JACKETT - Indexeurs
    # ========================================================================
    "jackett": {
        "indexers": [
            "Indexeurs Jackett ?",
            "Liste Jackett",
            "Sources Jackett",
        ],
        "test_indexers": [
            "Teste les indexeurs de Jackett",
            "Test Jackett",
            "Vérifie indexeurs Jackett",
        ],
        "stats": [
            "Stats Jackett",
        ],
    },

    # ========================================================================
    # DELUGE - Torrents
    # ========================================================================
    "deluge": {
        "torrents": [
            "Mes torrents ?",
            "Téléchargements en cours ?",
            "État des torrents",
            "Vitesse de téléchargement ?",
            "Torrents actifs",
            "Qu'est-ce qui télécharge ?",
            "Liste torrents",
            "Downloads en cours ?",
            "Torrents Deluge",
        ],
        "stats": [
            "Stats Deluge",
            "Statistiques torrents",
            "Ratio global ?",
            "Stats téléchargement",
        ],
    },

    # ========================================================================
    # OVERSEERR - Demandes de médias
    # ========================================================================
    "overseerr": {
        "search": [
            "Demande {title}",
            "Je voudrais {title}",
            "Request {title}",
            "Peux-tu ajouter {title} ?",
            "Demander {title}",
            "{title} n'est pas dispo, peux-tu l'ajouter ?",
            "Faire une demande pour {title}",
        ],
        "titles": [
            "Gladiator 2", "Avatar 3", "Mission Impossible 8", "Fast & Furious 11",
            "Jurassic World 4", "Transformers 8", "John Wick 5", "Shrek 5",
        ],
        "requests": [
            "Demandes en attente ?",
            "Mes demandes ?",
            "Requests Overseerr",
            "État de mes demandes",
            "Liste des demandes",
        ],
    },

    # ========================================================================
    # WIKI.JS - Documentation
    # ========================================================================
    "wikijs": {
        "search": [
            "Comment {topic} ?",
            "Tuto {topic}",
            "Documentation {topic}",
            "Guide {topic}",
            "Howto {topic}",
            "Tu as un tuto pour {topic} ?",
            "Wiki {topic}",
            "Recherche {topic} dans le wiki",
            "Doc {topic}",
        ],
        "topics": [
            "configurer Plex", "installer Docker", "setup VPN", "backup",
            "reverse proxy", "SSL certificat", "Nginx", "Traefik",
            "configuration réseau", "firewall", "SSH", "authentification",
            "base de données", "migration", "monitoring", "alertes",
            "Kubernetes", "Portainer", "Watchtower", "Heimdall",
        ],
        "pages": [
            "Pages du wiki",
            "Liste documentation",
            "Tous les articles",
            "Index wiki",
        ],
        "stats": [
            "Stats Wiki.js",
            "Statistiques wiki",
        ],
    },

    # ========================================================================
    # SYSTEM - Monitoring système
    # ========================================================================
    "system": {
        "health": [
            "État du serveur ?",
            "Tout va bien ?",
            "Santé du système ?",
            "Le serveur fonctionne ?",
            "Health check",
            "Status serveur",
            "Ça va le serveur ?",
        ],
        "metrics": [
            "Métriques système ?",
            "CPU et RAM ?",
            "Utilisation ressources ?",
            "Charge du serveur ?",
            "Espace disque ?",
            "Température CPU ?",
        ],
        "services": [
            "État des services ?",
            "Services actifs ?",
            "Quels services tournent ?",
            "Liste des services",
            "Status services",
        ],
        "logs": [
            "Logs d'erreur ?",
            "Dernières erreurs ?",
            "Montre les logs",
            "Logs récents",
            "Erreurs système",
            "Journal système",
        ],
        "alerts": [
            "Alertes actives ?",
            "Y a des alertes ?",
            "Problèmes en cours ?",
            "Notifications système",
            "Alertes système",
        ],
        "test_services": [
            ("Teste Plex", "Plex"),
            ("Vérifie Sonarr", "Sonarr"),
            ("Test connexion Radarr", "Radarr"),
            ("Ping Tautulli", "Tautulli"),
            ("Check Prowlarr", "Prowlarr"),
            ("Status Deluge", "Deluge"),
        ],
    },

    # ========================================================================
    # OPENWEBUI - Chat IA
    # ========================================================================
    "openwebui": {
        "status": [
            "OpenWebUI fonctionne ?",
            "État OpenWebUI",
            "Status OpenWebUI",
            "OpenWebUI OK ?",
        ],
        "models": [
            "Modèles disponibles ?",
            "Quels LLM ?",
            "Liste des modèles IA",
            "Modèles OpenWebUI",
        ],
        "chats": [
            "Mes conversations OpenWebUI",
            "Historique chat",
            "Mes discussions",
        ],
        "stats": [
            "Stats OpenWebUI",
            "Statistiques OpenWebUI",
        ],
    },
}

# ============================================================================
# PROMPTS DE DISTINCTION (confusions fréquentes)
# ============================================================================

DISTINCTION_DATA = [
    # Audio vs Vidéo - variations
    {
        "patterns": [
            "Je veux écouter {title}",
            "Mets {title} en audio",
            "Lance l'audiobook {title}",
            "Écoute {title}",
        ],
        "correct_tool": "audiobookshelf_search",
        "tags": ["distinction", "audiobookshelf", "écouter"],
    },
    {
        "patterns": [
            "Je veux regarder {title}",
            "Mets {title}",
            "Lance le film {title}",
            "Voir {title}",
        ],
        "correct_tool": "plex_search_media",
        "tool_args": {"media_type": "movie"},
        "tags": ["distinction", "plex", "regarder"],
    },
    # Manga vs Anime
    {
        "patterns": [
            "Je veux lire {title}",
            "Lis {title}",
            "Manga {title}",
            "BD {title}",
        ],
        "correct_tool": "komga_search",
        "tags": ["distinction", "komga", "lire"],
    },
    {
        "patterns": [
            "Je veux regarder l'anime {title}",
            "Anime {title}",
            "Série animée {title}",
        ],
        "correct_tool": "plex_search_media",
        "tool_args": {"media_type": "show"},
        "tags": ["distinction", "plex", "anime"],
    },
    # Film vs Série téléchargement
    {
        "patterns": [
            "Télécharge le film {title}",
            "Dl le film {title}",
            "Ajoute le film {title}",
        ],
        "correct_tool": "radarr_search_movie",
        "tags": ["distinction", "radarr", "téléchargement", "film"],
    },
    {
        "patterns": [
            "Télécharge la série {title}",
            "Dl la série {title}",
            "Ajoute la série {title}",
        ],
        "correct_tool": "sonarr_search_series",
        "tags": ["distinction", "sonarr", "téléchargement", "série"],
    },
]

DISTINCTION_TITLES = [
    "Harry Potter", "Dune", "Le Seigneur des Anneaux", "1984", "Game of Thrones",
    "One Piece", "Naruto", "Attack on Titan", "Dragon Ball", "Death Note",
    "The Matrix", "Inception", "Interstellar", "Avatar", "Star Wars",
]


def generate_tool_response(tool_name: str, query: str = None) -> Dict[str, Any]:
    """Génère une réponse simulée pour un outil."""
    responses = {
        "audiobookshelf_search": {"items": [{"title": query or "Livre Audio", "author": "Auteur", "narrator": "Narrateur", "duration": "10h 30m"}]},
        "audiobookshelf_get_libraries": {"libraries": [{"name": "Audiobooks", "itemCount": 150}, {"name": "Podcasts", "itemCount": 45}]},
        "audiobookshelf_get_media_progress": {"items": [{"title": "En cours", "progress": 45, "currentTime": "4h30"}]},
        "audiobookshelf_get_statistics": {"totalItems": 200, "totalDuration": "1500h"},
        "plex_search_media": {"results": [{"title": query or "Film", "year": 2024, "type": "movie", "resolution": "4K"}]},
        "plex_get_libraries": {"libraries": [{"name": "Films", "type": "movie", "count": 500}]},
        "plex_get_recently_added": {"items": [{"title": "Film récent", "type": "movie"}]},
        "plex_get_on_deck": {"items": [{"title": "En cours", "progress": "45%"}]},
        "plex_get_active_sessions": {"sessions": [{"user": "User1", "title": "Film", "progress": "30%"}]},
        "tautulli_get_activity": {"stream_count": 2, "sessions": [{"user": "Alice", "title": "Film"}]},
        "tautulli_get_history": {"history": [{"title": "Film vu", "user": "User1"}]},
        "tautulli_get_statistics": {"totalPlays": 1500},
        "komga_search": {"results": [{"name": query or "Manga", "booksCount": 50}]},
        "komga_get_libraries": {"libraries": [{"name": "Manga", "booksCount": 300}]},
        "komga_get_statistics": {"seriesCount": 100},
        "romm_search_roms": {"roms": [{"name": query or "Jeu", "platform": "N64"}]},
        "romm_get_platforms": {"platforms": [{"name": "Nintendo 64", "slug": "n64", "rom_count": 50}]},
        "romm_get_roms": {"roms": [{"name": "Jeu", "platform": "N64"}]},
        "romm_get_collections": {"collections": [{"name": "Favoris", "rom_count": 25}]},
        "romm_get_statistics": {"totalRoms": 500},
        "radarr_search_movie": {"movies": [{"title": query or "Film", "year": 2024}]},
        "radarr_get_queue": {"records": [{"title": "Film en cours", "sizeleft": "2 GB"}]},
        "radarr_get_calendar": {"movies": [{"title": "Film à venir"}]},
        "radarr_get_movies": {"movies": [{"title": "Film 1"}]},
        "radarr_get_indexers": {"indexers": [{"name": "Indexer1", "enabled": True}]},
        "radarr_test_all_indexers": {"results": [{"indexer": "Indexer1", "success": True}]},
        "radarr_get_statistics": {"movieCount": 500},
        "sonarr_search_series": {"series": [{"title": query or "Série", "year": 2024}]},
        "sonarr_get_queue": {"records": [{"title": "Épisode en cours"}]},
        "sonarr_get_calendar": {"episodes": [{"title": "S01E05"}]},
        "sonarr_get_series": {"series": [{"title": "Série 1"}]},
        "sonarr_get_indexers": {"indexers": [{"name": "Indexer1", "enabled": True}]},
        "sonarr_test_all_indexers": {"results": [{"indexer": "Indexer1", "success": True}]},
        "sonarr_get_statistics": {"seriesCount": 150},
        "prowlarr_get_indexers": {"indexers": [{"name": "1337x", "enabled": True}]},
        "prowlarr_test_all_indexers": {"results": [{"indexer": "1337x", "success": True}]},
        "prowlarr_get_statistics": {"indexerCount": 10},
        "jackett_get_indexers": {"indexers": [{"name": "Indexer1"}]},
        "jackett_test_all_indexers": {"results": [{"indexer": "Indexer1", "success": True}]},
        "jackett_get_statistics": {"indexerCount": 5},
        "deluge_get_torrents": {"torrents": [{"name": "fichier.iso", "progress": 75}]},
        "deluge_get_statistics": {"download_rate": "10 MB/s"},
        "overseerr_search_media": {"results": [{"title": query or "Média"}]},
        "overseerr_get_requests": {"requests": [{"title": "Demande 1"}]},
        "wikijs_search": {"results": [{"title": "Guide " + (query or "Topic")}]},
        "wikijs_get_pages": {"pages": [{"title": "Page 1"}]},
        "wikijs_get_statistics": {"pageCount": 100},
        "system_get_health": {"status": "healthy"},
        "system_get_metrics": {"cpu_usage": "25%", "memory_usage": "45%"},
        "system_get_services": {"services": [{"name": "Plex", "status": "running"}]},
        "system_get_logs": {"logs": [{"level": "info", "message": "OK"}]},
        "system_get_alerts": {"alerts": []},
        "system_test_service": {"success": True},
        "openwebui_get_status": {"status": "running"},
        "openwebui_get_models": {"models": [{"name": "llama3.2"}]},
        "openwebui_get_chats": {"chats": [{"title": "Conversation 1"}]},
        "openwebui_get_statistics": {"totalChats": 50},
    }
    return responses.get(tool_name, {"result": "ok"})


def generate_response(tool_name: str, query: str = None) -> str:
    """Génère une réponse assistant appropriée."""
    responses = {
        "audiobookshelf_search": f"J'ai trouvé \"{query}\" en audiobook.",
        "audiobookshelf_get_libraries": "Voici tes bibliothèques audio.",
        "audiobookshelf_get_media_progress": "Ta progression d'écoute.",
        "audiobookshelf_get_statistics": "Statistiques Audiobookshelf.",
        "plex_search_media": f"\"{query}\" est disponible sur Plex.",
        "plex_get_libraries": "Voici tes bibliothèques Plex.",
        "plex_get_recently_added": "Derniers ajouts sur Plex.",
        "plex_get_on_deck": "Voici ce que tu regardais.",
        "plex_get_active_sessions": "Sessions Plex actives.",
        "tautulli_get_activity": "Activité en cours sur Plex.",
        "tautulli_get_history": "Historique de visionnage.",
        "tautulli_get_statistics": "Statistiques Plex.",
        "komga_search": f"\"{query}\" est disponible sur Komga.",
        "komga_get_libraries": "Tes bibliothèques BD.",
        "komga_get_statistics": "Statistiques Komga.",
        "romm_search_roms": f"ROM \"{query}\" trouvée.",
        "romm_get_platforms": "Plateformes disponibles.",
        "romm_get_roms": "ROMs de la plateforme.",
        "romm_get_collections": "Tes collections de jeux.",
        "romm_get_statistics": "Statistiques RomM.",
        "radarr_search_movie": f"Film \"{query}\" trouvé. Je peux l'ajouter.",
        "radarr_get_queue": "Films en téléchargement.",
        "radarr_get_calendar": "Prochaines sorties films.",
        "radarr_get_movies": "Ta collection de films.",
        "radarr_get_indexers": "Indexeurs configurés dans Radarr.",
        "radarr_test_all_indexers": "Tests indexeurs Radarr OK.",
        "radarr_get_statistics": "Statistiques Radarr.",
        "sonarr_search_series": f"Série \"{query}\" trouvée. Je peux l'ajouter.",
        "sonarr_get_queue": "Épisodes en téléchargement.",
        "sonarr_get_calendar": "Prochains épisodes.",
        "sonarr_get_series": "Ta collection de séries.",
        "sonarr_get_indexers": "Indexeurs configurés dans Sonarr.",
        "sonarr_test_all_indexers": "Tests indexeurs Sonarr OK.",
        "sonarr_get_statistics": "Statistiques Sonarr.",
        "prowlarr_get_indexers": "Indexeurs Prowlarr.",
        "prowlarr_test_all_indexers": "Tests Prowlarr OK.",
        "prowlarr_get_statistics": "Statistiques Prowlarr.",
        "jackett_get_indexers": "Indexeurs Jackett.",
        "jackett_test_all_indexers": "Tests Jackett OK.",
        "jackett_get_statistics": "Statistiques Jackett.",
        "deluge_get_torrents": "Torrents en cours.",
        "deluge_get_statistics": "Statistiques Deluge.",
        "overseerr_search_media": f"\"{query}\" trouvé. Je peux créer une demande.",
        "overseerr_get_requests": "Demandes en cours.",
        "wikijs_search": f"Documentation trouvée pour \"{query}\".",
        "wikijs_get_pages": "Pages du wiki.",
        "wikijs_get_statistics": "Statistiques Wiki.js.",
        "system_get_health": "Le serveur est en bonne santé.",
        "system_get_metrics": "Métriques système.",
        "system_get_services": "État des services.",
        "system_get_logs": "Logs système.",
        "system_get_alerts": "Aucune alerte active.",
        "system_test_service": "Service testé avec succès.",
        "openwebui_get_status": "OpenWebUI fonctionne.",
        "openwebui_get_models": "Modèles disponibles.",
        "openwebui_get_chats": "Tes conversations.",
        "openwebui_get_statistics": "Statistiques OpenWebUI.",
    }
    return responses.get(tool_name, "Opération effectuée.")


def create_prompt(name: str, user_input: str, tool_name: str, tool_args: Dict[str, Any],
                  category: str, tags: List[str]) -> Dict[str, Any]:
    """Crée un prompt au format d'import."""
    query = tool_args.get("query", "")
    return {
        "name": name[:200],
        "description": f"Prompt pour {tool_name}",
        "category": category,
        "difficulty": "basic",
        "source": "generated",
        "format": "chat",
        "system_prompt": SYSTEM_PROMPT,
        "user_input": user_input,
        "tool_call": {"name": tool_name, "arguments": tool_args},
        "tool_response": generate_tool_response(tool_name, query),
        "assistant_response": generate_response(tool_name, query),
        "expected_output": "",
        "tags": tags,
        "enabled": True
    }


def generate_all_prompts() -> List[Dict[str, Any]]:
    """Génère tous les prompts."""
    prompts = []

    # Audiobookshelf search
    for pattern in PROMPTS_DATA["audiobookshelf"]["search"]:
        for title in PROMPTS_DATA["audiobookshelf"]["titles"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"Audiobookshelf - {user_input[:150]}",
                user_input, "audiobookshelf_search",
                {"query": title}, "media", ["audiobookshelf", "audiobook"]
            ))

    # Audiobookshelf other
    for pattern in PROMPTS_DATA["audiobookshelf"]["libraries"]:
        prompts.append(create_prompt(f"Audiobookshelf - {pattern[:150]}", pattern, "audiobookshelf_get_libraries", {}, "media", ["audiobookshelf"]))
    for pattern in PROMPTS_DATA["audiobookshelf"]["podcasts"]:
        prompts.append(create_prompt(f"Audiobookshelf - {pattern[:150]}", pattern, "audiobookshelf_search", {"query": "podcast"}, "media", ["audiobookshelf", "podcast"]))
    for pattern in PROMPTS_DATA["audiobookshelf"]["progress"]:
        prompts.append(create_prompt(f"Audiobookshelf - {pattern[:150]}", pattern, "audiobookshelf_get_media_progress", {}, "media", ["audiobookshelf"]))
    for pattern in PROMPTS_DATA["audiobookshelf"]["stats"]:
        prompts.append(create_prompt(f"Audiobookshelf - {pattern[:150]}", pattern, "audiobookshelf_get_statistics", {}, "media", ["audiobookshelf"]))

    # Plex movies
    for pattern in PROMPTS_DATA["plex"]["search_movie"]:
        for title in PROMPTS_DATA["plex"]["movies"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"Plex Film - {user_input[:145]}",
                user_input, "plex_search_media",
                {"query": title, "media_type": "movie"}, "media", ["plex", "film", "regarder"]
            ))

    # Plex shows
    for pattern in PROMPTS_DATA["plex"]["search_show"]:
        for title in PROMPTS_DATA["plex"]["shows"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"Plex Série - {user_input[:145]}",
                user_input, "plex_search_media",
                {"query": title, "media_type": "show"}, "media", ["plex", "série", "regarder"]
            ))

    # Plex other
    for pattern in PROMPTS_DATA["plex"]["recently_added"]:
        prompts.append(create_prompt(f"Plex - {pattern[:150]}", pattern, "plex_get_recently_added", {"limit": 10}, "media", ["plex"]))
    for pattern in PROMPTS_DATA["plex"]["on_deck"]:
        prompts.append(create_prompt(f"Plex - {pattern[:150]}", pattern, "plex_get_on_deck", {"limit": 5}, "media", ["plex"]))
    for pattern in PROMPTS_DATA["plex"]["libraries"]:
        prompts.append(create_prompt(f"Plex - {pattern[:150]}", pattern, "plex_get_libraries", {}, "media", ["plex"]))
    for pattern in PROMPTS_DATA["plex"]["sessions"]:
        prompts.append(create_prompt(f"Plex - {pattern[:150]}", pattern, "plex_get_active_sessions", {}, "media", ["plex"]))

    # Tautulli
    for pattern in PROMPTS_DATA["tautulli"]["activity"]:
        prompts.append(create_prompt(f"Tautulli - {pattern[:150]}", pattern, "tautulli_get_activity", {}, "media", ["tautulli"]))
    for pattern in PROMPTS_DATA["tautulli"]["history"]:
        prompts.append(create_prompt(f"Tautulli - {pattern[:150]}", pattern, "tautulli_get_history", {}, "media", ["tautulli"]))
    for pattern in PROMPTS_DATA["tautulli"]["stats"]:
        prompts.append(create_prompt(f"Tautulli - {pattern[:150]}", pattern, "tautulli_get_statistics", {}, "media", ["tautulli"]))

    # Komga
    for pattern in PROMPTS_DATA["komga"]["search"]:
        for title in PROMPTS_DATA["komga"]["titles"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"Komga - {user_input[:150]}",
                user_input, "komga_search",
                {"query": title}, "media", ["komga", "manga", "bd"]
            ))
    for pattern in PROMPTS_DATA["komga"]["libraries"]:
        prompts.append(create_prompt(f"Komga - {pattern[:150]}", pattern, "komga_get_libraries", {}, "media", ["komga"]))
    for pattern in PROMPTS_DATA["komga"]["stats"]:
        prompts.append(create_prompt(f"Komga - {pattern[:150]}", pattern, "komga_get_statistics", {}, "media", ["komga"]))

    # RomM
    for pattern in PROMPTS_DATA["romm"]["search"]:
        for title in PROMPTS_DATA["romm"]["games"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"RomM - {user_input[:150]}",
                user_input, "romm_search_roms",
                {"query": title}, "media", ["romm", "jeu", "rétro"]
            ))
    for pattern in PROMPTS_DATA["romm"]["platforms"]:
        prompts.append(create_prompt(f"RomM - {pattern[:150]}", pattern, "romm_get_platforms", {}, "media", ["romm"]))
    for query, platform in PROMPTS_DATA["romm"]["platform_queries"]:
        prompts.append(create_prompt(f"RomM - {query[:150]}", query, "romm_get_roms", {"platform_id": platform}, "media", ["romm", platform]))
    for pattern in PROMPTS_DATA["romm"]["collections"]:
        prompts.append(create_prompt(f"RomM - {pattern[:150]}", pattern, "romm_get_collections", {}, "media", ["romm"]))
    for pattern in PROMPTS_DATA["romm"]["stats"]:
        prompts.append(create_prompt(f"RomM - {pattern[:150]}", pattern, "romm_get_statistics", {}, "media", ["romm"]))

    # Radarr
    for pattern in PROMPTS_DATA["radarr"]["search"]:
        for title in PROMPTS_DATA["radarr"]["movies"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"Radarr - {user_input[:150]}",
                user_input, "radarr_search_movie",
                {"query": title}, "media", ["radarr", "téléchargement", "film"]
            ))
    for pattern in PROMPTS_DATA["radarr"]["queue"]:
        prompts.append(create_prompt(f"Radarr - {pattern[:150]}", pattern, "radarr_get_queue", {}, "media", ["radarr"]))
    for pattern in PROMPTS_DATA["radarr"]["calendar"]:
        prompts.append(create_prompt(f"Radarr - {pattern[:150]}", pattern, "radarr_get_calendar", {"days": 7}, "media", ["radarr"]))
    for pattern in PROMPTS_DATA["radarr"]["library"]:
        prompts.append(create_prompt(f"Radarr - {pattern[:150]}", pattern, "radarr_get_movies", {}, "media", ["radarr"]))
    for pattern in PROMPTS_DATA["radarr"]["indexers"]:
        prompts.append(create_prompt(f"Radarr - {pattern[:150]}", pattern, "radarr_get_indexers", {}, "homelab", ["radarr", "indexeur"]))
    for pattern in PROMPTS_DATA["radarr"]["test_indexers"]:
        prompts.append(create_prompt(f"Radarr - {pattern[:150]}", pattern, "radarr_test_all_indexers", {}, "homelab", ["radarr", "test"]))
    for pattern in PROMPTS_DATA["radarr"]["stats"]:
        prompts.append(create_prompt(f"Radarr - {pattern[:150]}", pattern, "radarr_get_statistics", {}, "media", ["radarr"]))

    # Sonarr
    for pattern in PROMPTS_DATA["sonarr"]["search"]:
        for title in PROMPTS_DATA["sonarr"]["shows"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"Sonarr - {user_input[:150]}",
                user_input, "sonarr_search_series",
                {"query": title}, "media", ["sonarr", "téléchargement", "série"]
            ))
    for pattern in PROMPTS_DATA["sonarr"]["queue"]:
        prompts.append(create_prompt(f"Sonarr - {pattern[:150]}", pattern, "sonarr_get_queue", {}, "media", ["sonarr"]))
    for pattern in PROMPTS_DATA["sonarr"]["calendar"]:
        prompts.append(create_prompt(f"Sonarr - {pattern[:150]}", pattern, "sonarr_get_calendar", {"days": 7}, "media", ["sonarr"]))
    for pattern in PROMPTS_DATA["sonarr"]["library"]:
        prompts.append(create_prompt(f"Sonarr - {pattern[:150]}", pattern, "sonarr_get_series", {}, "media", ["sonarr"]))
    for pattern in PROMPTS_DATA["sonarr"]["indexers"]:
        prompts.append(create_prompt(f"Sonarr - {pattern[:150]}", pattern, "sonarr_get_indexers", {}, "homelab", ["sonarr", "indexeur"]))
    for pattern in PROMPTS_DATA["sonarr"]["test_indexers"]:
        prompts.append(create_prompt(f"Sonarr - {pattern[:150]}", pattern, "sonarr_test_all_indexers", {}, "homelab", ["sonarr", "test"]))
    for pattern in PROMPTS_DATA["sonarr"]["stats"]:
        prompts.append(create_prompt(f"Sonarr - {pattern[:150]}", pattern, "sonarr_get_statistics", {}, "media", ["sonarr"]))

    # Prowlarr
    for pattern in PROMPTS_DATA["prowlarr"]["indexers"]:
        prompts.append(create_prompt(f"Prowlarr - {pattern[:150]}", pattern, "prowlarr_get_indexers", {}, "homelab", ["prowlarr"]))
    for pattern in PROMPTS_DATA["prowlarr"]["test_indexers"]:
        prompts.append(create_prompt(f"Prowlarr - {pattern[:150]}", pattern, "prowlarr_test_all_indexers", {}, "homelab", ["prowlarr", "test"]))
    for pattern in PROMPTS_DATA["prowlarr"]["stats"]:
        prompts.append(create_prompt(f"Prowlarr - {pattern[:150]}", pattern, "prowlarr_get_statistics", {}, "homelab", ["prowlarr"]))

    # Jackett
    for pattern in PROMPTS_DATA["jackett"]["indexers"]:
        prompts.append(create_prompt(f"Jackett - {pattern[:150]}", pattern, "jackett_get_indexers", {}, "homelab", ["jackett"]))
    for pattern in PROMPTS_DATA["jackett"]["test_indexers"]:
        prompts.append(create_prompt(f"Jackett - {pattern[:150]}", pattern, "jackett_test_all_indexers", {}, "homelab", ["jackett", "test"]))
    for pattern in PROMPTS_DATA["jackett"]["stats"]:
        prompts.append(create_prompt(f"Jackett - {pattern[:150]}", pattern, "jackett_get_statistics", {}, "homelab", ["jackett"]))

    # Deluge
    for pattern in PROMPTS_DATA["deluge"]["torrents"]:
        prompts.append(create_prompt(f"Deluge - {pattern[:150]}", pattern, "deluge_get_torrents", {}, "homelab", ["deluge", "torrent"]))
    for pattern in PROMPTS_DATA["deluge"]["stats"]:
        prompts.append(create_prompt(f"Deluge - {pattern[:150]}", pattern, "deluge_get_statistics", {}, "homelab", ["deluge"]))

    # Overseerr
    for pattern in PROMPTS_DATA["overseerr"]["search"]:
        for title in PROMPTS_DATA["overseerr"]["titles"]:
            user_input = pattern.format(title=title)
            prompts.append(create_prompt(
                f"Overseerr - {user_input[:150]}",
                user_input, "overseerr_search_media",
                {"query": title}, "media", ["overseerr", "demande"]
            ))
    for pattern in PROMPTS_DATA["overseerr"]["requests"]:
        prompts.append(create_prompt(f"Overseerr - {pattern[:150]}", pattern, "overseerr_get_requests", {}, "media", ["overseerr"]))

    # Wiki.js
    for pattern in PROMPTS_DATA["wikijs"]["search"]:
        for topic in PROMPTS_DATA["wikijs"]["topics"]:
            user_input = pattern.format(topic=topic)
            prompts.append(create_prompt(
                f"Wiki.js - {user_input[:150]}",
                user_input, "wikijs_search",
                {"query": topic}, "homelab", ["wikijs", "documentation"]
            ))
    for pattern in PROMPTS_DATA["wikijs"]["pages"]:
        prompts.append(create_prompt(f"Wiki.js - {pattern[:150]}", pattern, "wikijs_get_pages", {}, "homelab", ["wikijs"]))
    for pattern in PROMPTS_DATA["wikijs"]["stats"]:
        prompts.append(create_prompt(f"Wiki.js - {pattern[:150]}", pattern, "wikijs_get_statistics", {}, "homelab", ["wikijs"]))

    # System
    for pattern in PROMPTS_DATA["system"]["health"]:
        prompts.append(create_prompt(f"System - {pattern[:150]}", pattern, "system_get_health", {}, "homelab", ["system"]))
    for pattern in PROMPTS_DATA["system"]["metrics"]:
        prompts.append(create_prompt(f"System - {pattern[:150]}", pattern, "system_get_metrics", {}, "homelab", ["system"]))
    for pattern in PROMPTS_DATA["system"]["services"]:
        prompts.append(create_prompt(f"System - {pattern[:150]}", pattern, "system_get_services", {}, "homelab", ["system"]))
    for pattern in PROMPTS_DATA["system"]["logs"]:
        prompts.append(create_prompt(f"System - {pattern[:150]}", pattern, "system_get_logs", {"level": "error"}, "homelab", ["system"]))
    for pattern in PROMPTS_DATA["system"]["alerts"]:
        prompts.append(create_prompt(f"System - {pattern[:150]}", pattern, "system_get_alerts", {}, "homelab", ["system"]))
    for query, service in PROMPTS_DATA["system"]["test_services"]:
        prompts.append(create_prompt(f"System - {query[:150]}", query, "system_test_service", {"service_name": service}, "homelab", ["system", "test"]))

    # OpenWebUI
    for pattern in PROMPTS_DATA["openwebui"]["status"]:
        prompts.append(create_prompt(f"OpenWebUI - {pattern[:150]}", pattern, "openwebui_get_status", {}, "homelab", ["openwebui"]))
    for pattern in PROMPTS_DATA["openwebui"]["models"]:
        prompts.append(create_prompt(f"OpenWebUI - {pattern[:150]}", pattern, "openwebui_get_models", {}, "homelab", ["openwebui"]))
    for pattern in PROMPTS_DATA["openwebui"]["chats"]:
        prompts.append(create_prompt(f"OpenWebUI - {pattern[:150]}", pattern, "openwebui_get_chats", {"limit": 10}, "homelab", ["openwebui"]))
    for pattern in PROMPTS_DATA["openwebui"]["stats"]:
        prompts.append(create_prompt(f"OpenWebUI - {pattern[:150]}", pattern, "openwebui_get_statistics", {}, "homelab", ["openwebui"]))

    # Distinction prompts
    for distinction in DISTINCTION_DATA:
        for pattern in distinction["patterns"]:
            for title in DISTINCTION_TITLES:
                user_input = pattern.format(title=title)
                tool_args = {"query": title}
                if "tool_args" in distinction:
                    tool_args.update(distinction["tool_args"])
                prompts.append(create_prompt(
                    f"Distinction - {user_input[:140]}",
                    user_input, distinction["correct_tool"],
                    tool_args, "media", distinction["tags"]
                ))

    print(f"Total prompts générés: {len(prompts)}")
    return prompts


def main():
    prompts = generate_all_prompts()

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)

    print(f"Fichier généré: {OUTPUT_FILE}")
    print(f"Taille: {len(prompts)} prompts")


if __name__ == "__main__":
    main()
