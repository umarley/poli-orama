const fs = require('node:fs');
const path = require('node:path');

const rootDir = __dirname;
const isWindows = process.platform === 'win32';

function resolvePython(projectDir) {
  const virtualenvPython = path.join(
    projectDir,
    '.venv',
    isWindows ? 'Scripts' : 'bin',
    isWindows ? 'python.exe' : 'python',
  );

  return fs.existsSync(virtualenvPython) ? virtualenvPython : 'python';
}

const apiDir = path.join(rootDir, 'backend_core');
const jobsDir = path.join(rootDir, 'backend_jobs_celery');
const frontendDir = path.join(rootDir, 'frontend_core');
const publicSiteDir = path.join(rootDir, 'site_publico');

const apiPython = resolvePython(apiDir);
const jobsPython = resolvePython(jobsDir);

module.exports = {
  apps: [
    {
      name: 'poliorama-api',
      cwd: apiDir,
      script: apiPython,
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '750M',
      exp_backoff_restart_delay: 100,
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: path.join(apiDir, 'src'),
      },
    },
    {
      name: 'poliorama-worker',
      cwd: jobsDir,
      script: jobsPython,
      args: isWindows
        ? '-m celery -A jobs.celery_app worker --loglevel=INFO --pool=solo'
        : '-m celery -A jobs.celery_app worker --loglevel=INFO',
      interpreter: 'none',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      exp_backoff_restart_delay: 100,
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: path.join(jobsDir, 'src'),
      },
    },
    {
      name: 'poliorama-scheduler',
      cwd: jobsDir,
      script: jobsPython,
      args: '-m celery -A jobs.celery_app beat --loglevel=INFO',
      interpreter: 'none',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      exp_backoff_restart_delay: 100,
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: path.join(jobsDir, 'src'),
      },
    },
    {
      name: 'poliorama-app',
      cwd: frontendDir,
      script: "serve",
      interpreter: "node",
      env: {
        PM2_SERVE_PATH: "dist",
        PM2_SERVE_PORT: "5173",
        PM2_SERVE_SPA: "true",
        NODE_ENV: "production",
      },
    },
    {
      name: 'poliorama-site',
      cwd: publicSiteDir,
      script: "./dist/server/entry.mjs",
      interpreter: "node",
      env: {
        HOST: "127.0.0.1",
        PORT: "4321",
        NODE_ENV: "production",
        API_SERVER_URL: process.env.API_SERVER_URL || "http://127.0.0.1:8000",
        PUBLIC_API_URL: process.env.PUBLIC_API_URL || "/api"
      },
    },
  ],
};
