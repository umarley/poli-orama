import L from 'leaflet';

const globalScope = globalThis as typeof globalThis & { L?: typeof L };
if (!globalScope.L) {
  globalScope.L = L;
}

export { L };
