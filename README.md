# Template GitLab CI/CD

Template complet pour vos projets GitLab avec pipeline CI/CD automatisé, versioning sémantique, Docker et déploiement.

## Fonctionnalités

- Pipeline GitLab CI/CD avec 6 stages (validate, test, build, test-docker, publish, deploy)
- Tests automatisés avec Jest et couverture de code
- Build Docker multi-stage optimisé
- Tests Docker automatiques (santé, sécurité, taille)
- Publication sur Docker Hub et GitLab Registry
- Déploiement GitHub (optionnel)
- Versioning sémantique automatique avec CHANGELOG
- Releases GitLab automatiques avec notes extraites du CHANGELOG

---

## Démarrer un nouveau projet

### 1. Cloner le template

```bash
git clone https://votre-gitlab.com/namespace/template.git mon-projet
cd mon-projet
rm -rf .git
git init
git remote add origin https://votre-gitlab.com/namespace/mon-projet.git
```

### 2. Installer les dépendances

Prérequis : Node.js 20+ et npm 10+

```bash
npm install
```

### 3. Initialiser le projet

```bash
npm run init
```

Le script interactif configurera le nom du projet, le type et les options Docker/GitHub.

### 4. Configurer les variables GitLab

Dans **Settings > CI/CD > Variables**, ajoutez :

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `DOCKER_HUB_USER` | Nom d'utilisateur Docker Hub | Si Docker Hub activé |
| `DOCKER_HUB_TOKEN` | Token d'accès Docker Hub | Si Docker Hub activé |
| `GITHUB_TOKEN` | Personal Access Token GitHub | Si déploiement GitHub |
| `GITHUB_REPO` | Format `username/repository` | Si déploiement GitHub |
| `GITLAB_TOKEN` | Token GitLab (pour `npm run release:deploy`) | Optionnel |

### 5. Premier commit et release

```bash
git add .
git commit -m "feat: initial setup from template"
git push -u origin main

# Créer la première release
npm run release:first
```

---

## Commandes disponibles

### Développement

| Commande | Description |
|----------|-------------|
| `npm start` | Démarrer le serveur |
| `npm run dev` | Mode développement |
| `npm test` | Lancer les tests avec couverture |
| `npm run lint` | Vérifier le code avec ESLint |

### Docker

| Commande | Description |
|----------|-------------|
| `npm run docker:build` | Construire l'image Docker |
| `npm run docker:test` | Construire et tester l'image |

### Versioning et Release

| Commande | Description |
|----------|-------------|
| `npm run release:first` | Créer la première release (0.1.0) |
| `npm run release` | Créer une release (analyse les commits) |
| `npm run release:deploy` | Release + déclencher le déploiement |
| `npm run release:dry` | Prévisualiser la prochaine release |
| `npm run version:patch` | Bump version patch (1.0.X) |
| `npm run version:minor` | Bump version minor (1.X.0) |
| `npm run version:major` | Bump version major (X.0.0) |

### Maintenance

| Commande | Description |
|----------|-------------|
| `npm run init` | Initialiser/reconfigurer le projet |
| `npm run update:deps` | Mettre à jour les dépendances |
| `npm run update:template` | Synchroniser avec le template |

---

## Convention de commits

Utilisez les préfixes conventionnels pour le versioning automatique :

```bash
feat: nouvelle fonctionnalité     # Bump MINOR (1.X.0)
fix: correction de bug            # Bump PATCH (1.0.X)
feat!: breaking change            # Bump MAJOR (X.0.0)

# Autres préfixes (pas de bump automatique)
perf: amélioration performance
refactor: refactoring
docs: documentation
test: tests
ci: configuration CI/CD
chore: maintenance
```

Exemple :
```bash
git commit -m "feat: add user authentication"
git commit -m "fix: resolve login timeout issue"
git commit -m "feat!: new API incompatible with v1"
```

---

## Pipeline CI/CD

### Stages

1. **validate** - Lint du code (optionnel, n'échoue pas)
2. **test** - Tests backend/frontend avec couverture
3. **build** - Construction de l'image Docker
4. **test-docker** - Tests de santé, sécurité et taille de l'image
5. **publish** - Publication sur Docker Hub et/ou GitLab Registry
6. **deploy** - Déploiement GitHub + création de release GitLab

### Déclenchement

- **Push sur branche** : validate + test + build + test-docker
- **Push sur main** : Pipeline complet (sans déploiement)
- **Tag `vX.X.X`** : Pipeline complet + release GitLab
- **`npm run release:deploy`** : Pipeline complet + déploiement Docker Hub/GitHub

### Variables du pipeline

Modifiez dans [.gitlab-ci.yml](.gitlab-ci.yml) :

```yaml
variables:
  PROJECT_TYPE: "backend"           # backend, frontend, fullstack
  NODE_VERSION: "22"

  ENABLE_BACKEND_TESTS: "true"
  ENABLE_FRONTEND_TESTS: "false"
  ENABLE_DOCKER_BUILD: "true"
  ENABLE_GITLAB_REGISTRY: "false"

  # Déploiement (activé via DEPLOY=true ou npm run release:deploy)
  DEPLOY: "false"
  DOCKER_HUB_ENABLED: "true"
  GITHUB_DEPLOY_ENABLED: "true"
```

---

## Déploiement

Le déploiement (Docker Hub + GitHub) n'est exécuté que si `DEPLOY=true`.

### Option 1 : Via npm (recommandé)

```bash
# Crée une release ET déclenche le déploiement
npm run release:deploy
```

Prérequis : variable `GITLAB_TOKEN` définie localement :
```bash
export GITLAB_TOKEN="votre-token-gitlab"
npm run release:deploy
```

### Option 2 : Via GitLab manuellement

1. Allez dans **CI/CD > Pipelines > Run pipeline**
2. Sélectionnez le tag (ex: `v0.1.5`)
3. Ajoutez la variable : `DEPLOY = true`
4. Cliquez sur **Run pipeline**

---

## Configuration du runner GitLab

Pour le build Docker, votre runner doit être configuré avec Docker-in-Docker.

### Prérequis runner

Dans le fichier `config.toml` du runner :

```toml
[[runners]]
  [runners.docker]
    privileged = true
```

### Pour Docker Compose

```yaml
services:
  gitlab-runner:
    image: gitlab/gitlab-runner:latest
    privileged: true
    volumes:
      - ./config:/etc/gitlab-runner
      - /var/run/docker.sock:/var/run/docker.sock
```

---

## Structure du projet

```
.
├── .gitlab-ci.yml          # Pipeline CI/CD principal
├── Dockerfile              # Build Docker multi-stage
├── package.json            # Configuration et scripts npm
├── jest.config.js          # Configuration Jest
├── .eslintrc.json          # Configuration ESLint
├── .nvmrc                  # Version Node.js
├── .versionrc.json         # Configuration standard-version
├── src/
│   ├── index.js            # Point d'entrée de l'application
│   └── index.test.js       # Tests
├── scripts/
│   ├── init-project.js     # Initialisation du projet
│   ├── update-deps.js      # Mise à jour des dépendances
│   ├── sync-template.js    # Synchronisation template
│   ├── docker-test.js      # Tests Docker locaux
│   └── trigger-deploy.js   # Déclenchement déploiement
├── CHANGELOG.md            # Historique des versions (auto-généré)
└── README.md               # Ce fichier
```

---

## Workflow recommandé

```bash
# 1. Développer et commiter
git add .
git commit -m "feat: add new feature"
git push

# 2. Quand prêt pour une release
npm run release          # Release sans déploiement
# ou
npm run release:deploy   # Release + déploiement Docker Hub/GitHub

# 3. Le pipeline GitLab se déclenche automatiquement
#    - Tests
#    - Build Docker
#    - Publication (si DEPLOY=true)
#    - Release GitLab avec notes du CHANGELOG
```

---

## FAQ

### Comment désactiver Docker Hub ?

Dans [.gitlab-ci.yml](.gitlab-ci.yml) :
```yaml
DOCKER_HUB_ENABLED: "false"
```

### Comment changer la version de Node.js ?

1. Modifier [.nvmrc](.nvmrc)
2. Modifier [.gitlab-ci.yml](.gitlab-ci.yml) : `NODE_VERSION: "22"`
3. Modifier [Dockerfile](Dockerfile) : `ARG NODE_VERSION=22`

### Le pipeline échoue sur les tests Docker ?

Vérifiez que votre runner est en mode `privileged`. Voir la section "Configuration du runner GitLab".

### Comment ignorer un commit dans le CHANGELOG ?

Utilisez le préfixe `chore:` :
```bash
git commit -m "chore: update readme"
```

### Comment voir le contenu d'une release ?

Les notes de release GitLab incluent automatiquement le contenu du CHANGELOG pour la version concernée, avec un lien vers le CHANGELOG complet.

---

## Licence

MIT
