#!/usr/bin/env node

/**
 * Script d'initialisation de projet
 * Configurer un nouveau projet à partir du template
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Fonction pour poser des questions interactives
function ask(question, defaultValue = '') {
  const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const prompt = `${question} ${defaultValue ? `(${defaultValue})` : ''}: `;

  return new Promise(resolve => {
    readline.question(prompt, answer => {
      readline.close();
      resolve(answer.trim() || defaultValue);
    });
  });
}

async function main() {
  console.log('\n🚀 Initialisation du projet GitLab\n');

  // Questions
  const projectName = await ask('Nom du projet', path.basename(process.cwd()));
  const projectType = await ask('Type de projet (backend/frontend/fullstack)', 'backend');
  const dockerHubUser = await ask('Utilisateur Docker Hub', '');
  const githubRepo = await ask('Repository GitHub (optionnel, format: user/repo)', '');
  const nodeVersion = await ask('Version de Node.js', '18');

  // Configuration
  const enableBackendTests = projectType === 'backend' || projectType === 'fullstack';
  const enableFrontendTests = projectType === 'frontend' || projectType === 'fullstack';
  const enableDockerBuild = true;
  const enableDockerHub = dockerHubUser !== '';
  const enableGithubDeploy = githubRepo !== '';

  console.log('\n📝 Configuration:');
  console.log(`  - Nom: ${projectName}`);
  console.log(`  - Type: ${projectType}`);
  console.log(`  - Tests backend: ${enableBackendTests ? '✅' : '❌'}`);
  console.log(`  - Tests frontend: ${enableFrontendTests ? '✅' : '❌'}`);
  console.log(`  - Docker Hub: ${enableDockerHub ? '✅' : '❌'}`);
  console.log(`  - GitHub: ${enableGithubDeploy ? '✅' : '❌'}`);

  const confirm = await ask('\nContinuer avec cette configuration? (y/n)', 'y');
  if (confirm.toLowerCase() !== 'y') {
    console.log('❌ Annulé');
    process.exit(0);
  }

  // Mise à jour de package.json
  console.log('\n📦 Mise à jour de package.json...');
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));

  packageJson.name = projectName;
  packageJson.version = '0.1.0';
  packageJson.config = {
    projectName,
    projectType,
    dockerImage: dockerHubUser ? `${dockerHubUser}/${projectName}` : `${projectName}`,
    dockerRegistry: 'docker.io',
    githubRepo,
    enableGithubDeploy
  };

  // Ajouter les scripts selon le type de projet
  if (enableBackendTests) {
    packageJson.scripts['test:backend'] = 'echo "Add your backend test command here (e.g., jest, mocha)"';
  }
  if (enableFrontendTests) {
    packageJson.scripts['test:frontend'] = 'echo "Add your frontend test command here (e.g., jest, vitest, cypress)"';
    packageJson.scripts['build'] = 'echo "Add your build command here (e.g., vite build, webpack)"';
  }

  fs.writeFileSync('package.json', JSON.stringify(packageJson, null, 2));
  console.log('✅ package.json mis à jour');

  // Mise à jour de .template-config.json
  console.log('\n⚙️  Mise à jour de .template-config.json...');
  const templateConfig = JSON.parse(fs.readFileSync('.template-config.json', 'utf8'));

  templateConfig.features.backend.enabled = enableBackendTests;
  templateConfig.features.frontend.enabled = enableFrontendTests;
  templateConfig.features.docker.enabled = enableDockerBuild;
  templateConfig.features.githubMirror.enabled = enableGithubDeploy;
  templateConfig.features.githubMirror.repository = githubRepo;

  fs.writeFileSync('.template-config.json', JSON.stringify(templateConfig, null, 2));
  console.log('✅ .template-config.json mis à jour');

  // Mise à jour de .nvmrc
  console.log('\n🔧 Mise à jour de .nvmrc...');
  fs.writeFileSync('.nvmrc', nodeVersion);
  console.log('✅ .nvmrc mis à jour');

  // Mise à jour de .gitlab-ci.yml
  console.log('\n🔄 Mise à jour de .gitlab-ci.yml...');
  let gitlabCi = fs.readFileSync('.gitlab-ci.yml', 'utf8');

  gitlabCi = gitlabCi
    .replace(/PROJECT_TYPE: ".*"/, `PROJECT_TYPE: "${projectType}"`)
    .replace(/NODE_VERSION: ".*"/, `NODE_VERSION: "${nodeVersion}"`)
    .replace(/ENABLE_BACKEND_TESTS: ".*"/, `ENABLE_BACKEND_TESTS: "${enableBackendTests}"`)
    .replace(/ENABLE_FRONTEND_TESTS: ".*"/, `ENABLE_FRONTEND_TESTS: "${enableFrontendTests}"`)
    .replace(/ENABLE_DOCKER_BUILD: ".*"/, `ENABLE_DOCKER_BUILD: "${enableDockerBuild}"`)
    .replace(/ENABLE_DOCKER_HUB: ".*"/, `ENABLE_DOCKER_HUB: "${enableDockerHub}"`)
    .replace(/ENABLE_GITHUB_DEPLOY: ".*"/, `ENABLE_GITHUB_DEPLOY: "${enableGithubDeploy}"`);

  fs.writeFileSync('.gitlab-ci.yml', gitlabCi);
  console.log('✅ .gitlab-ci.yml mis à jour');

  // Créer le Dockerfile si nécessaire
  if (enableDockerBuild && !fs.existsSync('Dockerfile')) {
    console.log('\n🐳 Création du Dockerfile...');
    const dockerfileTemplate = fs.readFileSync('Dockerfile.template', 'utf8');
    fs.writeFileSync('Dockerfile', dockerfileTemplate);
    console.log('✅ Dockerfile créé');
  }

  // Installation des dépendances
  console.log('\n📥 Installation des dépendances...');
  try {
    execSync('npm install', { stdio: 'inherit' });
    console.log('✅ Dépendances installées');
  } catch (error) {
    console.error('⚠️  Erreur lors de l\'installation des dépendances');
  }

  // Initialisation Git si nécessaire
  if (!fs.existsSync('.git')) {
    console.log('\n🔧 Initialisation Git...');
    execSync('git init', { stdio: 'inherit' });
    execSync('git add .', { stdio: 'inherit' });
    execSync('git commit -m "Initial commit from template"', { stdio: 'inherit' });
    console.log('✅ Git initialisé');
  }

  console.log('\n✅ Initialisation terminée!\n');
  console.log('📚 Prochaines étapes:');
  console.log('  1. Configurer les variables GitLab CI/CD:');
  if (enableDockerHub) {
    console.log('     - DOCKER_HUB_USER');
    console.log('     - DOCKER_HUB_TOKEN');
  }
  if (enableGithubDeploy) {
    console.log('     - GITHUB_TOKEN');
    console.log('     - GITHUB_REPO');
  }
  console.log('  2. Personnaliser les scripts de test dans package.json');
  console.log('  3. Adapter le Dockerfile à votre application');
  console.log('  4. Pusher vers GitLab pour déclencher le pipeline\n');
  console.log('💡 Commandes utiles:');
  console.log('  - npm run release:first    # Créer la première release');
  console.log('  - npm run version:patch    # Incrémenter patch version');
  console.log('  - npm run update:template  # Synchroniser avec le template\n');
}

main().catch(console.error);
