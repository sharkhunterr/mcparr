#!/usr/bin/env node

/**
 * Script de test Docker
 * Teste l'image Docker localement
 */

const { execSync } = require('child_process');
const fs = require('fs');

function exec(command, options = {}) {
  try {
    return execSync(command, { encoding: 'utf8', stdio: 'inherit', ...options });
  } catch (error) {
    console.error(`❌ Erreur lors de l'exécution de: ${command}`);
    throw error;
  }
}

function getVersion() {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
  return packageJson.version;
}

function getImageName() {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
  return packageJson.config.dockerImage || packageJson.name;
}

function buildImage() {
  console.log('\n🐳 Construction de l\'image Docker...\n');

  const version = getVersion();
  const imageName = getImageName();

  exec(`docker build -t ${imageName}:${version} -t ${imageName}:latest .`);

  console.log('\n✅ Image construite avec succès');
  return { imageName, version };
}

function testImage(imageName, version) {
  console.log('\n🧪 Test de l\'image Docker...\n');

  // Test 1: Vérifier que l'image existe
  console.log('1️⃣  Vérification de l\'image...');
  exec(`docker images ${imageName}:${version}`);

  // Test 2: Démarrer un conteneur
  console.log('\n2️⃣  Démarrage du conteneur...');
  const containerId = execSync(
    `docker run -d --name test-container ${imageName}:${version}`,
    { encoding: 'utf8' }
  ).trim();

  console.log(`   Container ID: ${containerId.substring(0, 12)}`);

  try {
    // Test 3: Attendre que le conteneur soit prêt
    console.log('\n3️⃣  Vérification du statut...');

    let running = false;
    for (let i = 0; i < 10; i++) {
      const status = execSync(
        `docker inspect -f '{{.State.Status}}' ${containerId}`,
        { encoding: 'utf8' }
      ).trim();

      if (status === 'running') {
        console.log('   ✅ Conteneur en cours d\'exécution');
        running = true;
        break;
      }

      if (status === 'exited') {
        console.log('   ❌ Conteneur arrêté');
        console.log('\n📋 Logs du conteneur:');
        exec(`docker logs ${containerId}`);
        throw new Error('Le conteneur s\'est arrêté de manière inattendue');
      }

      // Attendre 1 seconde
      execSync('sleep 1');
    }

    if (!running) {
      throw new Error('Le conteneur n\'a pas démarré dans les temps');
    }

    // Test 4: Afficher les logs
    console.log('\n4️⃣  Logs du conteneur:');
    exec(`docker logs ${containerId}`);

    // Test 5: Vérifier Node.js (si applicable)
    console.log('\n5️⃣  Vérification de Node.js...');
    try {
      const nodeVersion = execSync(
        `docker exec ${containerId} node --version`,
        { encoding: 'utf8' }
      ).trim();
      console.log(`   ✅ Node.js ${nodeVersion}`);
    } catch (error) {
      console.log('   ⚠️  Node.js non disponible ou conteneur non interactif');
    }

    // Test 6: Statistiques
    console.log('\n6️⃣  Statistiques du conteneur:');
    exec(`docker stats ${containerId} --no-stream`);

    console.log('\n✅ Tests réussis!');

  } finally {
    // Nettoyage
    console.log('\n🧹 Nettoyage...');
    try {
      execSync(`docker stop ${containerId}`, { stdio: 'ignore' });
      execSync(`docker rm ${containerId}`, { stdio: 'ignore' });
      console.log('   ✅ Conteneur supprimé');
    } catch (error) {
      console.log('   ⚠️  Erreur lors du nettoyage');
    }
  }
}

function showImageInfo(imageName, version) {
  console.log('\n📊 Informations sur l\'image:\n');

  exec(`docker images ${imageName}:${version}`);

  console.log('\n💡 Pour démarrer le conteneur:');
  console.log(`   docker run -d -p 3000:3000 ${imageName}:${version}`);
  console.log('\n💡 Pour publier sur Docker Hub:');
  console.log(`   docker push ${imageName}:${version}`);
}

async function main() {
  console.log('\n🐳 Test Docker Local\n');

  // Vérifier que Docker est disponible
  try {
    execSync('docker --version', { stdio: 'ignore' });
  } catch (error) {
    console.error('❌ Docker n\'est pas installé ou n\'est pas démarré');
    process.exit(1);
  }

  // Vérifier qu'un Dockerfile existe
  if (!fs.existsSync('Dockerfile')) {
    console.error('❌ Aucun Dockerfile trouvé');
    console.error('💡 Créez un Dockerfile ou copiez Dockerfile.template');
    process.exit(1);
  }

  const { imageName, version } = buildImage();
  testImage(imageName, version);
  showImageInfo(imageName, version);

  console.log('\n✨ Terminé!\n');
}

main().catch(error => {
  console.error('\n❌ Erreur:', error.message);
  process.exit(1);
});
