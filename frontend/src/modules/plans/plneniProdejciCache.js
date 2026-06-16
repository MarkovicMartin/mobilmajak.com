const CACHE_PREFIX = 'plneni-prodejci-v1';
const CURRENT_MONTH_STALE_MS = 60 * 1000;
const memoryCache = new Map();

function storageKey(rok, mesic) {
  return `${CACHE_PREFIX}:${rok}-${mesic}`;
}

export function readPlneniProdejciCache(rok, mesic) {
  const key = storageKey(rok, mesic);
  const mem = memoryCache.get(key);
  if (mem) return mem;
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    memoryCache.set(key, parsed);
    return parsed;
  } catch {
    return null;
  }
}

export function writePlneniProdejciCache(rok, mesic, prodejci) {
  const key = storageKey(rok, mesic);
  const entry = { data: prodejci, fetchedAt: Date.now() };
  memoryCache.set(key, entry);
  try {
    sessionStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // sessionStorage plné – modulová cache stačí
  }
}

export function invalidatePlneniProdejciCache(rok, mesic) {
  const key = storageKey(rok, mesic);
  memoryCache.delete(key);
  try {
    sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
}

export function needsPlneniProdejciBackgroundRefresh(rok, mesic, cached, now = new Date()) {
  if (!cached) return true;
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  if (rok < currentYear || (rok === currentYear && mesic < currentMonth)) {
    return false;
  }
  if (rok > currentYear || (rok === currentYear && mesic > currentMonth)) {
    return true;
  }
  return Date.now() - (cached.fetchedAt || 0) > CURRENT_MONTH_STALE_MS;
}
