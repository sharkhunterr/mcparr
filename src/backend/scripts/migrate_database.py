#!/usr/bin/env python3
"""
Script de migration de base de données avec Alembic.
Ce script permet de gérer les migrations sans perte de données.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.database.connection import init_database


async def backup_database():
    """Créer une sauvegarde de la base de données."""
    db_path = Path("data/mcparr.db")
    if db_path.exists():
        backup_path = db_path.with_suffix(f".db.backup.{int(asyncio.get_event_loop().time())}")
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Base de données sauvegardée: {backup_path}")
        return backup_path
    else:
        print("ℹ️  Aucune base de données existante à sauvegarder")
        return None


def run_alembic_command(command):
    """Exécuter une commande Alembic."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)

    result = subprocess.run(
        ["alembic"] + command.split(),
        cwd=Path(__file__).parent.parent,
        env=env,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"❌ Erreur Alembic: {result.stderr}")
        return False
    else:
        print(f"✅ {' '.join(['alembic'] + command.split())}")
        if result.stdout.strip():
            print(result.stdout)
        return True


async def migrate_database(message="Auto migration"):
    """Effectuer une migration complète."""
    print("🔄 Début de la migration de base de données...")

    # 1. Sauvegarde
    backup_path = await backup_database()

    try:
        # 2. Créer une nouvelle migration si nécessaire
        if not run_alembic_command(f'revision --autogenerate -m "{message}"'):
            # Aucune migration nécessaire
            print("ℹ️  Aucune migration nécessaire")
            return True

        # 3. Appliquer les migrations
        if not run_alembic_command("upgrade head"):
            raise Exception("Erreur lors de l'application des migrations")

        print("✅ Migration terminée avec succès!")
        return True

    except Exception as e:
        print(f"❌ Erreur durant la migration: {e}")

        # Restauration depuis la sauvegarde
        if backup_path and backup_path.exists():
            print("🔄 Restauration de la sauvegarde...")
            import shutil
            shutil.copy2(backup_path, "data/mcparr.db")
            print("✅ Base de données restaurée")

        return False


async def initialize_fresh_database():
    """Initialiser une nouvelle base de données."""
    print("🔄 Initialisation d'une nouvelle base de données...")

    # Créer les tables avec SQLAlchemy
    db_manager = init_database()
    await db_manager.create_tables()

    # Marquer comme à jour dans Alembic
    run_alembic_command("stamp head")

    print("✅ Nouvelle base de données initialisée!")


async def main():
    """Point d'entrée principal."""
    if len(sys.argv) < 2:
        print("""
Usage: python migrate_database.py <command> [options]

Commandes:
  init          - Initialiser une nouvelle base de données
  migrate       - Effectuer une migration (avec sauvegarde)
  backup        - Créer seulement une sauvegarde
  current       - Afficher la version actuelle
  history       - Afficher l'historique des migrations
  upgrade       - Appliquer les migrations en attente

Exemples:
  python migrate_database.py init
  python migrate_database.py migrate "Add new user fields"
  python migrate_database.py backup
""")
        return

    command = sys.argv[1]

    if command == "init":
        await initialize_fresh_database()

    elif command == "migrate":
        message = sys.argv[2] if len(sys.argv) > 2 else "Auto migration"
        await migrate_database(message)

    elif command == "backup":
        await backup_database()

    elif command == "current":
        run_alembic_command("current")

    elif command == "history":
        run_alembic_command("history")

    elif command == "upgrade":
        backup_path = await backup_database()
        if run_alembic_command("upgrade head"):
            print("✅ Migrations appliquées avec succès!")
        else:
            print("❌ Erreur lors de l'application des migrations")

    else:
        print(f"❌ Commande inconnue: {command}")


if __name__ == "__main__":
    asyncio.run(main())