const { execSync } = require('child_process');
const path = require('path');

// Source resolve-ports.sh to get dynamic port configuration
const scriptPath = path.join(__dirname, 'scripts', 'resolve-ports.sh');
let apiPort = 8787;
let webPort = 3737;
let suffix = '';

try {
  const output = execSync(`bash "${scriptPath}"`, { encoding: 'utf-8' });
  const lines = output.trim().split('\n');
  for (const line of lines) {
    const [key, value] = line.split('=');
    if (key === 'ORBITAL_API_PORT') apiPort = parseInt(value, 10);
    if (key === 'ORBITAL_WEB_PORT') webPort = parseInt(value, 10);
    if (key === 'ORBITAL_INSTANCE_SUFFIX') suffix = value;
  }
} catch (e) {
  // Fall back to defaults if script fails
  console.error('Warning: Could not resolve ports, using defaults');
}

module.exports = {
  apps: [
    {
      name: `orbital-api${suffix}`,
      cwd: './api',
      script: 'uv',
      args: `run uvicorn app.main:app --reload --port ${apiPort}`,
      watch: false,
      max_memory_restart: '1G',
      env: {
        ALLOWED_ORIGINS: `http://localhost:${webPort}`,
      },
    },
    {
      name: `orbital-web${suffix}`,
      cwd: './web',
      script: 'npm',
      args: `run dev -- --port ${webPort}`,
      env: {
        NODE_ENV: 'development',
        NEXT_PUBLIC_API_URL: `http://localhost:${apiPort}`,
      },
      watch: false,
      max_memory_restart: '1G',
    }
  ]
};
