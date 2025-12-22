#!/usr/bin/env node

/**
 * Script de synchronisation avec le template
 * Récupère les dernières modifications du template sans écraser les personnalisations
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function exec(command, options = {}) {
  try {
    return execSync(command, { encoding: 'utf8', ...options });
  } catch (error) {
    return null;
  }
}

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync('.template-config.json', 'utf8'));
  } catch (error) {
    console.error('❌ Fichier .template-config.json non trouvé');
    console.error('💡 Ce projet n\'a pas été initialisé avec ce template');
    process.exit(1);
  }
}

function compareVersions(v1, v2) {
  const parts1 = v1.split('.').map(Number);
  const parts2 = v2.split('.').map(Number);

  for (let i = 0; i < 3; i++) {
    if (parts1[i] > parts2[i]) return 1;
    if (parts1[i] < parts2[i]) return -1;
  }
  return 0;
}

async function syncManagedFiles(config) {
  console.log('\n📥 Synchronisation des fichiers gérés...\n');

  const tempDir = path.join(process.cwd(), '.template-sync');

  try {
    // Cloner le template dans un dossier temporaire
    console.log('📦 Téléchargement du template...');
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }

    exec(`git clone --depth 1 ${config.templateRepo} ${tempDir}`, { stdio: 'ignore' });

    // Lire la version du template distant
    const remoteConfig = JSON.parse(
      fs.readFileSync(path.join(tempDir, '.template-config.json'), 'utf8')
    );

    console.log(`\n📊 Version actuelle: ${config.templateVersion}`);
    console.log(`📊 Version distante: ${remoteConfig.templateVersion}`);

    if (compareVersions(remoteConfig.templateVersion, config.templateVersion) <= 0) {
      console.log('\n✅ Vous avez déjà la dernière version du template');
      return;
    }

    console.log('\n🔄 Mise à jour disponible!\n');

    // Copier les fichiers gérés
    let updatedFiles = 0;
    for (const file of config.managedFiles) {
      const sourcePath = path.join(tempDir, file);
      const destPath = path.join(process.cwd(), file);

      // Gérer les globs
      if (file.includes('*')) {
        const glob = require('glob');
        const files = glob.sync(file, { cwd: tempDir });

        for (const matchedFile of files) {
          const src = path.join(tempDir, matchedFile);
          const dest = path.join(process.cwd(), matchedFile);

          if (fs.existsSync(src)) {
            fs.mkdirSync(path.dirname(dest), { recursive: true });
            fs.copyFileSync(src, dest);
            console.log(`  ✅ ${matchedFile}`);
            updatedFiles++;
          }
        }
      } else {
        if (fs.existsSync(sourcePath)) {
          fs.mkdirSync(path.dirname(destPath), { recursive: true });
          fs.copyFileSync(sourcePath, destPath);
          console.log(`  ✅ ${file}`);
          updatedFiles++;
        }
      }
    }

    // Mettre à jour la version dans .template-config.json
    config.templateVersion = remoteConfig.templateVersion;
    fs.writeFileSync('.template-config.json', JSON.stringify(config, null, 2));

    console.log(`\n✅ ${updatedFiles} fichier(s) mis à jour`);
    console.log(`📦 Version du template: ${config.templateVersion}`);

  } catch (error) {
    console.error('❌ Erreur lors de la synchronisation:', error.message);
    throw error;
  } finally {
    // Nettoyer le dossier temporaire
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  }
}

function showProtectedFiles(config) {
  console.log('\n🔒 Fichiers protégés (non mis à jour automatiquement):');
  config.protectedFiles.forEach(file => {
    console.log(`  - ${file}`);
  });
  console.log('\n💡 Pour mettre à jour ces fichiers, comparez-les manuellement avec le template');
}

async function main() {
  console.log('\n🔄 Synchronisation avec le template GitLab\n');

  const config = loadConfig();

  if (!config.templateRepo) {
    console.error('❌ URL du template non configurée dans .template-config.json');
    process.exit(1);
  }

  await syncManagedFiles(config);
  showProtectedFiles(config);

  console.log('\n✨ Synchronisation terminée!\n');
  console.log('💡 Prochaines étapes:');
  console.log('  1. Vérifier les fichiers mis à jour');
  console.log('  2. Tester votre application');
  console.log('  3. Commit les changements si tout fonctionne\n');
}

main().catch(error => {
  console.error('\n❌ Erreur:', error.message);
  process.exit(1);
});
