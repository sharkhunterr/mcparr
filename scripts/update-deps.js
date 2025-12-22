#!/usr/bin/env node

/**
 * Script de mise à jour des dépendances
 * Met à jour les dépendances npm de manière interactive
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

function checkOutdated() {
  console.log('🔍 Vérification des dépendances obsolètes...\n');

  try {
    execSync('npm outdated', { encoding: 'utf8', stdio: 'inherit' });
  } catch (error) {
    // npm outdated retourne un code d'erreur s'il y a des dépendances obsolètes
  }
}

function updateDependencies(type = 'minor') {
  console.log(`\n📦 Mise à jour des dépendances (${type})...\n`);

  if (!fs.existsSync('node_modules')) {
    console.log('📥 Installation initiale des dépendances...');
    exec('npm install');
  }

  if (type === 'patch') {
    // Mise à jour conservative (patch uniquement)
    console.log('🔧 Mise à jour patch (X.X.n)');
    exec('npm update');
  } else if (type === 'minor') {
    // Mise à jour mineure (X.n.0)
    console.log('🔧 Mise à jour minor (X.n.0)');
    exec('npm update');

    // Vérifier si npm-check-updates est disponible
    try {
      execSync('npx -v', { stdio: 'ignore' });
      console.log('🔄 Mise à jour vers les dernières versions mineures...');
      exec('npx npm-check-updates -u --target minor');
      exec('npm install');
    } catch (error) {
      console.log('⚠️  npm-check-updates non disponible, utilisation de npm update');
    }
  } else if (type === 'major') {
    // Mise à jour majeure (n.0.0)
    console.log('⚠️  Mise à jour major (n.0.0) - Attention aux breaking changes!');
    try {
      exec('npx npm-check-updates -u');
      exec('npm install');
    } catch (error) {
      console.error('❌ Erreur lors de la mise à jour majeure');
      throw error;
    }
  }

  console.log('\n✅ Dépendances mises à jour');
}

function auditDependencies() {
  console.log('\n🔒 Audit de sécurité...\n');

  try {
    exec('npm audit');
    console.log('\n💡 Pour corriger automatiquement les vulnérabilités:');
    console.log('   npm audit fix');
    console.log('   npm audit fix --force  (pour les breaking changes)');
  } catch (error) {
    console.log('\n⚠️  Des vulnérabilités ont été détectées');
  }
}

function cleanInstall() {
  console.log('\n🧹 Nettoyage et réinstallation...\n');

  if (fs.existsSync('node_modules')) {
    console.log('🗑️  Suppression de node_modules...');
    fs.rmSync('node_modules', { recursive: true, force: true });
  }

  if (fs.existsSync('package-lock.json')) {
    console.log('🗑️  Suppression de package-lock.json...');
    fs.unlinkSync('package-lock.json');
  }

  console.log('📥 Réinstallation...');
  exec('npm install');

  console.log('\n✅ Réinstallation terminée');
}

async function main() {
  console.log('\n🔄 Mise à jour des dépendances\n');

  const args = process.argv.slice(2);
  const command = args[0] || 'check';

  switch (command) {
    case 'check':
      checkOutdated();
      break;

    case 'patch':
      checkOutdated();
      updateDependencies('patch');
      auditDependencies();
      break;

    case 'minor':
      checkOutdated();
      updateDependencies('minor');
      auditDependencies();
      break;

    case 'major':
      checkOutdated();
      updateDependencies('major');
      auditDependencies();
      break;

    case 'audit':
      auditDependencies();
      break;

    case 'clean':
      cleanInstall();
      auditDependencies();
      break;

    default:
      console.log('❌ Commande inconnue\n');
      console.log('Usage: npm run update:deps [command]');
      console.log('\nCommandes disponibles:');
      console.log('  check  - Vérifier les dépendances obsolètes (défaut)');
      console.log('  patch  - Mise à jour patch (X.X.n)');
      console.log('  minor  - Mise à jour minor (X.n.0)');
      console.log('  major  - Mise à jour major (n.0.0)');
      console.log('  audit  - Audit de sécurité');
      console.log('  clean  - Nettoyage et réinstallation');
      process.exit(1);
  }

  console.log('\n✨ Terminé!\n');
}

main().catch(error => {
  console.error('\n❌ Erreur:', error.message);
  process.exit(1);
});
