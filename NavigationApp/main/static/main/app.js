(function () {
  function qs(sel, root=document) { return root.querySelector(sel); }

  const floor = qs('#floorplan');
  const svg = qs('#floorplan-svg');
  const routeLayer = qs('#route-layer');

  function clientPointToPercent(evt) {
    const rect = floor.getBoundingClientRect();
    const cx = (evt.clientX - rect.left) / rect.width * 100;
    const cy = (evt.clientY - rect.top) / rect.height * 100;
    return { x: Math.max(0, Math.min(100, cx)), y: Math.max(0, Math.min(100, cy)) };
  }

  function clearRoute() {
    while (routeLayer.firstChild) routeLayer.removeChild(routeLayer.firstChild);
  }

  function drawPoint(p, color='#00ffd2', r=1.6) {
    const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx', p.x);
    c.setAttribute('cy', p.y);
    c.setAttribute('r', r);
    c.setAttribute('fill', color);
    c.setAttribute('opacity', '0.95');
    routeLayer.appendChild(c);
  }

  function drawPath(points) {
    if (!points || points.length < 2) return;
    const poly = document.createElementNS('http://www.w3.org/2000/svg','polyline');
    const pts = points.map(p => `${p.x},${p.y}`).join(' ');
    poly.setAttribute('points', pts);
    poly.setAttribute('fill', 'none');
    poly.setAttribute('stroke', '#00ffd2');
    poly.setAttribute('stroke-width', '1.6');
    poly.setAttribute('stroke-linecap', 'round');
    poly.setAttribute('stroke-linejoin', 'round');
    poly.setAttribute('opacity', '0.9');
    routeLayer.appendChild(poly);
    const last = points[points.length - 1];
    const tri = document.createElementNS('http://www.w3.org/2000/svg','circle');
    tri.setAttribute('cx', last.x);
    tri.setAttribute('cy', last.y);
    tri.setAttribute('r', 2.6);
    tri.setAttribute('fill', '#ff6b7f');
    routeLayer.appendChild(tri);
  }

  async function requestRoute(point) {
    try {
      const res = await fetch('/api/route/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(point)
      });
      if (!res.ok) {
        console.error('Route request failed', res.status);
        return null;
      }
      return await res.json();
    } catch (e) {
      console.error('Network error', e);
      return null;
    }
  }

  floor.addEventListener('click', async function (evt) {
    const pt = clientPointToPercent(evt);
    clearRoute();
    drawPoint(pt, '#00ffd2', 1.8);
    const result = await requestRoute(pt);
    if (!result || !result.path) return;
    drawPath(result.path);
    result.path.forEach((p) => {
      if (p.type === 'user') return;
      drawPoint(p, p.type === 'exit' ? '#ff8a5b' : '#7c4dff', 1.6);
    });
    console.log('Route:', result.path.map(p => p.label || p.id));
  });
})();