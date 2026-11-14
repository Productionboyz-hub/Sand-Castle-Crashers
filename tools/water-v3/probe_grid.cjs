// probe_grid.cjs <url> : FAIL if the tile grid shows through the shallow water.
// Metric: in the shallows (4-60 px behind the water edge), compare the colour jump between horizontally
// adjacent pixels that straddle a shore-tile / non-shore-tile boundary vs pixels inside one tile.
// A visible per-tile tint makes boundary jumps much larger than interior ones. Averaged over 5 frames.
const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const c = await b.newContext({viewport:{width:1280,height:720},deviceScaleFactor:1});
 const p = await c.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
 await p.goto(process.argv[2]); await p.evaluate(() => { getTideT = () => 1; shoreD = SHORE_LOW; }); await p.waitForTimeout(2500);
 const r = await p.evaluate(async () => {
  const o = iso(0,0,0), ex = iso(1,0,0), ey = iso(0,1,0);
  const ax = ex.x-o.x, ay = ex.y-o.y, bx = ey.x-o.x, by = ey.y-o.y, det = ax*by - ay*bx;
  const tileAt = (x,y) => { const dx=x-o.x, dy=y-o.y; return [Math.floor((dx*by-dy*bx)/det), Math.floor((ax*dy-ay*dx)/det)]; };
  let bd=0,bn=0,id=0,inn=0;
  for (let f=0; f<5; f++) {
   await new Promise(r=>requestAnimationFrame(r));
   const img = ctx.getImageData(0,0,SW,SH).data; const L = i => img[i]*.3+img[i+1]*.59+img[i+2]*.11;
   for (let x=0; x<SW-1; x++) { const e = visShoreYAt(x);
    for (let y=Math.ceil(e+4); y<Math.min(SH, e+60); y++) {
     const t1 = tileAt(x+0.5,y+0.5), t2 = tileAt(x+1.5,y+0.5);
     const d = Math.abs(L((y*SW+x)*4) - L((y*SW+x+1)*4));
     if (t1[0]===t2[0] && t1[1]===t2[1]) { id+=d; inn++; }
     else if (t1[0]>=0&&t1[1]>=0&&t2[0]>=0&&t2[1]>=0&&t1[0]<GCOLS&&t2[0]<GCOLS&&t1[1]<GROWS&&t2[1]<GROWS && isShore(t1[0],t1[1]) !== isShore(t2[0],t2[1])) { bd+=d; bn++; }
    } } }
  return { boundary: +(bd/bn).toFixed(2), interior: +(id/inn).toFixed(2), ratio: +((bd/bn)/(id/inn)).toFixed(2), boundaryPairs: bn };
 });
 const ok = r.boundaryPairs > 200 && r.ratio < 1.5 && errs.length === 0;
 console.log((ok?'PASS':'FAIL')+'  tile grid under the shallows: boundary/interior jump ratio '+r.ratio+' (limit 1.5)', JSON.stringify(r), 'errs', errs.length);
 await b.close(); process.exit(ok?0:1); })();
