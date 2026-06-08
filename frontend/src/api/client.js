// const BASE = "https://markdownusingllm-pjbn-production.up.railway.app";

// export async function fetchDashboard(from_date, to_date) {
//   const params = from_date && to_date ? `?from_date=${from_date}&to_date=${to_date}` : "";
//   const res = await fetch(`${BASE}/api/dashboard${params}`);
//   if (!res.ok) throw new Error("Failed to fetch");
//   return res.json();
// }

// export async function fetchProducts(category = "All", risk = "All") {
//   const res = await fetch(`${BASE}/api/products?category=${category}&risk=${risk}`);
//   return res.json();
// }

// export async function fetchPlanner() {
//   const res = await fetch(`${BASE}/api/planner`);
//   return res.json();
// }

// export async function fetchHistory() {
//   const res = await fetch(`${BASE}/api/history`);
//   return res.json();
// }

// export async function runAgents(product_id) {
//   const res = await fetch(`${BASE}/api/run`, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify({ product_id }),
//   });
//   return res.json();
// }




const BASE = "https://markdownusingllm-pjbn-production.up.railway.app";

// Simple in-memory cache — survives page tab switches, cleared on refresh
const _cache = {};
const TTL = 5 * 60 * 1000; // 5 minutes

async function _fetch(url) {
  const now = Date.now();
  if (_cache[url] && now - _cache[url].ts < TTL) {
    return _cache[url].data;
  }
  const res  = await fetch(url);
  const data = await res.json();
  _cache[url] = { data, ts: now };
  return data;
}

export async function fetchDashboard() {
  return _fetch(`${BASE}/api/dashboard`);
}
export async function fetchProducts(category = "All", risk = "All") {
  return _fetch(`${BASE}/api/products?category=${category}&risk=${risk}`);
}
export async function fetchPlanner() {
  return _fetch(`${BASE}/api/planner`);
}
export async function fetchHistory() {
  return _fetch(`${BASE}/api/history`);
}
export async function fetchNotifications() {
  return _fetch(`${BASE}/api/notifications`);
}
export async function runAgents(product_id) {
  // Never cache POST requests
  _cache[`${BASE}/api/planner`]      = undefined;
  _cache[`${BASE}/api/dashboard`]    = undefined;
  _cache[`${BASE}/api/history`]      = undefined;
  _cache[`${BASE}/api/notifications`]= undefined;
  const res = await fetch(`${BASE}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id }),
  });
  return res.json();
}