(function () {
  function qs(sel, root=document){ return root.querySelector(sel); }
  const floor = qs('#floorplan');
  const svg = qs('#floorplan-svg');
  const routeLayer = qs('#route-layer');
  const distEl = qs('#dist-to-exit');
  const etaEl = qs('#eta');
  const stepsList = qs('#steps-list');
  const mockBtn = qs('#mock-btn');

  function clientPointToPercent(evt){
    const rect = floor.getBoundingClientRect();
    const cx = (evt.clientX - rect.left) / rect.width * 100;
    const cy = (evt.clientY - rect.top) / rect.height * 100;
    return { x: Math.max(0, Math.min(100, cx)), y: Math.max(0, Math.min(100, cy)) };
  }
  function clearRoute(){ while(routeLayer.firstChild) routeLayer.removeChild(routeLayer.firstChild); }
  function drawPoint(p, color='#00ffd2', r=0.9){
    const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx', p.x); c.setAttribute('cy', p.y); c.setAttribute('r', r);
    c.setAttribute('fill', color); c.setAttribute('opacity','0.95');
    routeLayer.appendChild(c);
  }
  function drawPath(points){
    if(!points||points.length<2) return;
    const poly = document.createElementNS('http://www.w3.org/2000/svg','polyline');
    poly.setAttribute('points', points.map(p=>`${p.x},${p.y}`).join(' '));
    poly.setAttribute('fill','none'); poly.setAttribute('stroke','#00ffd2');
    poly.setAttribute('stroke-width','0.8'); poly.setAttribute('opacity','0.95');
    routeLayer.appendChild(poly);
  }

  async function requestRoute(point){
    try{
      const res = await fetch('/api/route/', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(point)
      });
      if(!res.ok) throw new Error('Request failed '+res.status);
      return await res.json();
    }catch(e){
      console.error('route request failed', e);
      return null;
    }
  }

  async function handlePoint(pt){
    clearRoute();
    drawPoint(pt,'#00ffd2',1.2);
    const res = await requestRoute(pt);
    if(!res || !res.path) return;
    // draw nodes and polyline
    drawPath(res.path);
    res.path.forEach(p=>{
      if(p.type==='user') return;
      drawPoint(p, p.type==='exit' ? '#ff8a5b' : '#7c4dff', 1.0);
    });
    // update UI numbers
    distEl.textContent = (res.distance_m !== undefined) ? `${res.distance_m} m` : '— m';
    etaEl.textContent = (res.eta_s !== undefined) ? `Odhad: ${Math.round(res.eta_s/60)} min ${res.eta_s%60} s` : '';
    // steps
    stepsList.innerHTML = '';
    if(Array.isArray(res.steps)){
      res.steps.forEach(s=>{
        const d = document.createElement('div');
        d.className = 'step';
        d.textContent = s.text;
        stepsList.appendChild(d);
      });
    }
    console.log('route', res);
  }

  floor.addEventListener('click', async function(evt){
    const p = clientPointToPercent(evt);
    await handlePoint(p);
  });

  // convenience: pick a few test points to simulate different rooms
  const tests = [
    {x:46,y:18}, // C101
    {x:64,y:18}, // C102
    {x:80,y:50}, // Gym
    {x:12,y:50}, // Entrance area
  ];
  mockBtn.addEventListener('click', function(){
    const t = tests[Math.floor(Math.random()*tests.length)];
    handlePoint(t);
  });

  // initial demo draw
  document.addEventListener('DOMContentLoaded', function(){ /* no-op */ });
})();