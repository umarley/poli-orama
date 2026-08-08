import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const appDir = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(appDir, 'dist');
const host = process.env.HOST || '127.0.0.1';
const port = Number.parseInt(process.env.PORT || '4321', 10);

const contentTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.gif', 'image/gif'],
  ['.html', 'text/html; charset=utf-8'],
  ['.ico', 'image/x-icon'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml; charset=utf-8'],
  ['.txt', 'text/plain; charset=utf-8'],
  ['.webp', 'image/webp'],
  ['.xml', 'application/xml; charset=utf-8'],
]);

function sendFile(request, response, filePath, fileStat, statusCode = 200) {
  const extension = path.extname(filePath).toLowerCase();
  const isVersionedAsset = filePath.startsWith(path.join(publicDir, '_astro'));

  response.writeHead(statusCode, {
    'Content-Type': contentTypes.get(extension) || 'application/octet-stream',
    'Content-Length': fileStat.size,
    'Cache-Control': isVersionedAsset
      ? 'public, max-age=31536000, immutable'
      : 'public, max-age=0, must-revalidate',
  });

  if (request.method === 'HEAD') {
    response.end();
    return;
  }

  createReadStream(filePath).pipe(response);
}

async function findFile(pathname) {
  const relativePath = pathname.replace(/^\/+/, '');
  const candidate = path.resolve(publicDir, relativePath);
  const relativeToPublic = path.relative(publicDir, candidate);

  if (relativeToPublic.startsWith('..') || path.isAbsolute(relativeToPublic)) {
    return null;
  }

  try {
    const candidateStat = await stat(candidate);
    if (candidateStat.isFile()) return { filePath: candidate, fileStat: candidateStat };

    if (candidateStat.isDirectory()) {
      const indexPath = path.join(candidate, 'index.html');
      const indexStat = await stat(indexPath);
      if (indexStat.isFile()) return { filePath: indexPath, fileStat: indexStat };
    }
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error;
  }

  return null;
}

const server = createServer(async (request, response) => {
  try {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      response.writeHead(405, { Allow: 'GET, HEAD' });
      response.end('Method Not Allowed');
      return;
    }

    const url = new URL(request.url || '/', `http://${request.headers.host || 'localhost'}`);

    if (url.pathname === '/favicon.ico') {
      response.writeHead(308, { Location: '/favicon.svg' });
      response.end();
      return;
    }

    let pathname;
    try {
      pathname = decodeURIComponent(url.pathname);
    } catch {
      response.writeHead(400);
      response.end('Bad Request');
      return;
    }

    const result = await findFile(pathname);
    if (result) {
      sendFile(request, response, result.filePath, result.fileStat);
      return;
    }

    const notFoundPath = path.join(publicDir, '404.html');
    const notFoundStat = await stat(notFoundPath);
    sendFile(request, response, notFoundPath, notFoundStat, 404);
  } catch (error) {
    console.error('Error while serving request:', error);
    response.writeHead(500);
    response.end('Internal Server Error');
  }
});

server.listen(port, host, () => {
  console.log(`Public site listening on http://${host}:${port}`);
});
