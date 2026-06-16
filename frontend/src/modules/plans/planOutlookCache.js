const CACHE_PREFIX = 'plan-outlook-v1';
const CURRENT_MONTH_STALE_MS = 5 * 60 * 1000;
const memoryCache = new Map();

function normalizeRust(rustProcent) {
  const rust = Number(String(rustProcent).replace(',', '.'));
  return Number.isNaN(rust) ? '10' : String(rust);
}

export function outlookCacheParamsKey({
  forecastRok,
  forecastCompareRoky,
  vyhledFirma,
  vyhledProdejny,
  rustProcent,
}) {
  const roky = [...(forecastCompareRoky || [])].sort((a, b) => a - b).join(',');
  const pids = vyhledFirma || !(vyhledProdejny || []).length
    ? 'firma'
    : [...vyhledProdejny].sort((a, b) => a - b).join(',');
  return `${forecastRok}:${roky}:${pids}:${normalizeRust(rustProcent)}`;
}

function storageKey(paramsKey) {
  return `${CACHE_PREFIX}:${paramsKey}`;
}

export function readOutlookCache(paramsKey) {
  const mem = memoryCache.get(paramsKey);
  if (mem) return mem;
  try {
    const raw = sessionStorage.getItem(storageKey(paramsKey));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    memoryCache.set(paramsKey, parsed);
    return parsed;
  } catch {
    return null;
  }
}

export function writeOutlookCache(paramsKey, payload) {
  const entry = { ...payload, fetchedAt: Date.now() };
  memoryCache.set(paramsKey, entry);
  try {
    sessionStorage.setItem(storageKey(paramsKey), JSON.stringify(entry));
  } catch {
    // sessionStorage plné – modulová cache stačí
  }
}

export function invalidateOutlookCache(paramsKey) {
  memoryCache.delete(paramsKey);
  try {
    sessionStorage.removeItem(storageKey(paramsKey));
  } catch {
    // ignore
  }
}

function mergeMesice(cachedMesice, freshMesice, rok, now = new Date()) {
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  if (rok < currentYear) {
    return cachedMesice?.length ? cachedMesice : freshMesice;
  }
  if (rok > currentYear) {
    return freshMesice;
  }

  const freshByMesic = new Map((freshMesice || []).map((m) => [m.mesic, m]));
  const source = cachedMesice?.length ? cachedMesice : freshMesice;
  const mesice = (source || []).map((cached) => {
    if (cached.mesic < currentMonth) return cached;
    return freshByMesic.get(cached.mesic) || cached;
  });
  for (const freshMonth of freshMesice || []) {
    if (freshMonth.mesic >= currentMonth && !mesice.some((m) => m.mesic === freshMonth.mesic)) {
      mesice.push(freshMonth);
    }
  }
  mesice.sort((a, b) => a.mesic - b.mesic);
  return mesice;
}

export function mergeOutlookData(cachedData, freshData, hlavniRok, now = new Date()) {
  if (!cachedData) return freshData;
  if (!freshData) return cachedData;

  const mergedPredikce = {
    ...freshData.predikce,
    mesice: mergeMesice(
      cachedData.predikce?.mesice,
      freshData.predikce?.mesice,
      hlavniRok,
      now,
    ),
  };

  const cachedPorovnani = new Map((cachedData.porovnani_roky || []).map((s) => [s.rok, s]));
  const porovnani_roky = (freshData.porovnani_roky || []).map((freshSerie) => {
    const cachedSerie = cachedPorovnani.get(freshSerie.rok);
    if (!cachedSerie) return freshSerie;
    return {
      ...freshSerie,
      mesice: mergeMesice(cachedSerie.mesice, freshSerie.mesice, freshSerie.rok, now),
    };
  });

  return {
    ...freshData,
    predikce: mergedPredikce,
    porovnani_roky,
    meta: freshData.meta || cachedData.meta,
  };
}

export function needsOutlookBackgroundRefresh(forecastRok, cached, now = new Date()) {
  if (!cached) return true;
  const currentYear = now.getFullYear();
  if (forecastRok < currentYear) return false;
  if (forecastRok > currentYear) return true;
  return Date.now() - (cached.fetchedAt || 0) > CURRENT_MONTH_STALE_MS;
}
