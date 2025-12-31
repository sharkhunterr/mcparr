# MCParr - Tests et Corrections Automatiques

## ⚙️ Installation (première fois)

```bash
npm run setup             # Configure backend (Poetry) + frontend
```

Cette commande installe Poetry si nécessaire et configure tout l'environnement.

## 🚀 Commandes rapides

```bash
# Tests
npm run test              # Tous les tests
npm run test:back         # Tests backend
npm run test:front        # Tests frontend

# Corrections automatiques
npm run fix               # Corrige tout
npm run fix:back          # Corrige backend
npm run fix:front         # Corrige frontend

# Rapports
npm run reports           # Génère les rapports
cat reports/SUMMARY.md    # Voir le résumé

# Vérification
npm run lint              # Vérifie tout
npm run lint:back         # Vérifie backend
npm run lint:front        # Vérifie frontend
```

## 📋 Fichiers générés

### Rapports (`./reports/`)
- `SUMMARY.md` - Résumé consolidé
- `ruff-fixes.patch` - Patch des corrections backend
- `ruff-report.txt` - Erreurs backend
- `eslint-report.txt` - Erreurs frontend
- `htmlcov/index.html` - Couverture de code HTML

### Appliquer les corrections
```bash
# Méthode 1: Auto-fix complet
npm run fix

# Méthode 2: Appliquer le patch
patch -p1 < reports/ruff-fixes.patch
```

## 🔄 GitLab CI

### Jobs disponibles
- `validate:backend` - Vérifie et corrige le backend (génère rapports)
- `validate:frontend` - Vérifie et corrige le frontend (génère rapports)
- `auto-fix` - Applique les corrections et crée un commit (manuel ou avec `[auto-fix]`)
- `test:backend` - Lance les tests backend
- `test:frontend` - Build le frontend

### Déclencher l'auto-fix dans le CI
```bash
# Option 1: Message de commit
git commit -m "fix: something [auto-fix]"

# Option 2: Variable GitLab
# Settings → CI/CD → Variables → AUTO_FIX_ENABLED=true

# Option 3: Manuel dans GitLab UI
# Pipelines → Run job "auto-fix"
```

## 📁 Structure créée

```
mcparr/
├── scripts/
│   ├── setup-backend.sh        # Installation Poetry + backend
│   ├── run-backend-tests.sh    # Tests backend
│   ├── run-backend-lint.sh     # Vérification backend
│   ├── run-backend-fix.sh      # Correction backend
│   ├── ci-auto-fix.sh          # Correction automatique complète
│   ├── generate-reports.sh     # Génération rapports
│   └── fix-linting.sh          # Correction simple
├── src/backend/tests/          # Tests backend (nouveau)
│   ├── test_health.py
│   └── conftest.py
├── reports/                    # Rapports générés
├── Makefile                    # Commandes make (optionnel)
└── TEST-CI.md                  # Ce fichier
```

## 🔧 Problèmes résolus

✅ Backend: créé des tests de base (plus d'erreur "no tests collected")
✅ Linting: 272+ erreurs corrigées automatiquement avec `npm run fix`
✅ Rapports: génération automatique avec `npm run reports`
✅ CI: auto-fix disponible dans le pipeline GitLab
