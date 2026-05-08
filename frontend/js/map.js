/**
 * AgriNet AI v2.0 — Leaflet Map Module
 * Transport pool map + supply chain map
 */

let _transportMap;
const TRANSPORT_ZOOM = 11;

// ── Transport Pool Map ─────────────────────────────────────────────────────────
function initTransportMap() {
  const container = document.getElementById('transport-map');
  if (!container || _transportMap) return;

  const lat = (typeof state !== 'undefined' && state.lat) || 19.9975;
  const lon = (typeof state !== 'undefined' && state.lon) || 73.7898;

  _transportMap = L.map('transport-map', { zoomControl: true }).setView([lat, lon], TRANSPORT_ZOOM);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 19
  }).addTo(_transportMap);

  // User marker
  const userIcon = L.divIcon({
    html: '<div style="width:20px;height:20px;background:#16A34A;border:3px solid #fff;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,.3);"></div>',
    className: '',
    iconAnchor: [10, 10],
  });
  L.marker([lat, lon], { icon: userIcon }).addTo(_transportMap)
    .bindPopup(`<b>📍 Your Farm</b><br>Transport origin`).openPopup();

  // Farmer markers
  const COLORS = ['#7C3AED','#D97706','#2563EB','#DC2626','#DB2777'];
  const FARMERS_LOCAL = typeof FARMERS !== 'undefined' ? FARMERS : [];

  FARMERS_LOCAL.forEach((f, i) => {
    const fLat = lat + (f.lat || (i * 0.01 - 0.02));
    const fLon = lon + (f.lon || (i * 0.015 - 0.02));
    const farmerIcon = L.divIcon({
      html: `<div style="width:16px;height:16px;background:${COLORS[i % COLORS.length]};border:2px solid #fff;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.3);"></div>`,
      className: '',
      iconAnchor: [8, 8],
    });
    L.marker([fLat, fLon], { icon: farmerIcon })
      .addTo(_transportMap)
      .bindPopup(`<b>${f.name}</b><br>🌱 ${f.crop} · ${f.acres} acres<br>📍 ${f.dist} km away`);
  });

  // Mandi marker
  const mandiLat = lat + 0.22;
  const mandiLon = lon + 0.14;
  const mandiIcon = L.divIcon({
    html: '<div style="background:#D97706;color:#fff;padding:4px 8px;border-radius:6px;font-size:11px;font-weight:700;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.3);">🏪 APMC Mandi</div>',
    className: '',
    iconAnchor: [40, 14],
  });
  L.marker([mandiLat, mandiLon], { icon: mandiIcon })
    .addTo(_transportMap)
    .bindPopup(`<b>APMC Mandi</b><br>Destination market`);

  // Draw dashed route line
  L.polyline([[lat, lon], [mandiLat, mandiLon]], {
    color: '#16A34A', weight: 2.5, dashArray: '8 6', opacity: 0.7
  }).addTo(_transportMap);
}

// ── Update transport map after pool calculation ───────────────────────────────
function updateTransportMap() {
  if (!_transportMap) { initTransportMap(); return; }
  // Animate the route color to show pool route
  _transportMap.eachLayer(layer => {
    if (layer instanceof L.Polyline) {
      layer.setStyle({ color: '#16A34A', weight: 3.5, dashArray: '0', opacity: 0.9 });
    }
  });
}

// ── Auto-init on transport tab ─────────────────────────────────────────────────
const _origNavTo = typeof navTo !== 'undefined' ? navTo : null;

document.addEventListener('DOMContentLoaded', () => {
  // Patch navTo to init transport map when section is opened
  const origNavTo = window.navTo;
  if (origNavTo) {
    window.navTo = function(tab, el) {
      origNavTo(tab, el);
      if (tab === 'transport') {
        setTimeout(initTransportMap, 200);
      }
    };
  }

  // Also init transport map if we start on that section
  if (document.querySelector('#s-transport.active')) {
    setTimeout(initTransportMap, 400);
  }
});
