#!/usr/bin/env node

/**
 * Script pour déclencher un pipeline avec déploiement
 * Utilise l'API GitLab pour relancer le pipeline du dernier tag avec DEPLOY=true
 */

const { execSync } = require('child_process');
const https = require('https');
const http = require('http');

async function main() {
  console.log('\n🚀 Déclenchement du déploiement...\n');

  // Récupérer les infos Git
  const tag = execSync('git describe --tags --abbrev=0', { encoding: 'utf8' }).trim();
  const remoteUrl = execSync('git remote get-url origin', { encoding: 'utf8' }).trim();

  console.log(`📦 Tag: ${tag}`);

  // Parser l'URL GitLab
  const urlMatch = remoteUrl.match(/(?:https?:\/\/|git@)([^/:]+)[/:](.+?)(?:\.git)?$/);
  if (!urlMatch) {
    console.error('❌ Impossible de parser l\'URL du remote Git');
    process.exit(1);
  }

  const gitlabHost = urlMatch[1];
  const projectPath = urlMatch[2];
  const projectPathEncoded = encodeURIComponent(projectPath);

  console.log(`🌐 GitLab: ${gitlabHost}`);
  console.log(`📁 Projet: ${projectPath}`);

  // Vérifier si GITLAB_TOKEN ou CI_JOB_TOKEN est défini
  const token = process.env.GITLAB_TOKEN || process.env.CI_JOB_TOKEN;

  if (!token) {
    console.log('\n⚠️  Variable GITLAB_TOKEN non définie.');
    console.log('\n📋 Pour activer le déploiement, vous pouvez :');
    console.log('\n   Option 1 - Définir GITLAB_TOKEN :');
    console.log('   export GITLAB_TOKEN="votre-token-gitlab"');
    console.log('   npm run release:deploy');
    console.log('\n   Option 2 - Déclencher manuellement via GitLab :');
    console.log(`   1. Allez sur : https://${gitlabHost}/${projectPath}/-/pipelines`);
    console.log('   2. Cliquez sur "Run pipeline"');
    console.log(`   3. Sélectionnez le tag: ${tag}`);
    console.log('   4. Ajoutez la variable: DEPLOY = true');
    console.log('   5. Cliquez sur "Run pipeline"');
    console.log('');
    return;
  }

  // Déclencher le pipeline via l'API
  const apiUrl = `https://${gitlabHost}/api/v4/projects/${projectPathEncoded}/pipeline`;

  const postData = JSON.stringify({
    ref: tag,
    variables: [
      { key: 'DEPLOY', value: 'true' }
    ]
  });

  const isHttps = !gitlabHost.match(/^(localhost|127\.|192\.168\.|10\.)/);
  const httpModule = isHttps ? https : http;
  const port = isHttps ? 443 : 80;

  const options = {
    hostname: gitlabHost,
    port: port,
    path: `/api/v4/projects/${projectPathEncoded}/pipeline`,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'PRIVATE-TOKEN': token,
      'Content-Length': Buffer.byteLength(postData)
    }
  };

  const req = httpModule.request(options, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
      if (res.statusCode === 201) {
        const result = JSON.parse(data);
        console.log(`\n✅ Pipeline de déploiement déclenché !`);
        console.log(`   ID: ${result.id}`);
        console.log(`   URL: ${result.web_url}`);
      } else {
        console.error(`\n❌ Erreur: ${res.statusCode}`);
        console.error(data);
      }
    });
  });

  req.on('error', (e) => {
    console.error(`\n❌ Erreur de connexion: ${e.message}`);
  });

  req.write(postData);
  req.end();
}

main().catch(console.error);
