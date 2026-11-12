// probe_block.cjs <url> : FAIL if the water texture on a phone is much blockier than on desktop.
// Metric: mean |luma difference| between horizontally adjacent texels in fully opaque water,
// converted to "per CSS px" (divide by W_SCALE) so it measures what you see, not the texture size.
const { chromium, devices } = require('playwright');
(async () => { const b = await chromium.launch(); const out = {};
 for (const [n,o] of [['desk',{viewport:{width:1280,height:720}}],['iphone',devices['iPhone 13']],['ipad',devices['iPad (gen 7)']]]) {
  const c = await b.newContext(o); const p = await c.newPage(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
  await p.goto(process.argv[2]); await p.waitForTimeout(1500);
  out[n] = await p.evaluate(() => { let tot=0,cnt=0; const d=wImg.data;
    for (let y=0;y<WH;y++) for (let x=0;x<WW-1;x++){ const i=(y*WW+x)*4, j=i+4; if(d[i+3]<250||d[j+3]<250) continue;
      tot+=Math.abs((d[i]*.3+d[i+1]*.59+d[i+2]*.11)-(d[j]*.3+d[j+1]*.59+d[j+2]*.11)); cnt++; }
    return { W_SCALE, th:+TH().toFixed(1), perCssPx: +(tot/cnt/W_SCALE).toFixed(2), samples: cnt }; });
  out[n].errs = errs.length; await c.close(); }
 await b.close();
 const base = out.desk.perCssPx; let fail=0;
 for (const n of ['iphone','ipad']) { const ok = out[n].perCssPx <= base*1.6 && out[n].errs===0; if(!ok) fail++; console.log((ok?'PASS':'FAIL')+'  '+n+' blockiness '+out[n].perCssPx+' vs desktop '+base+' (limit '+(base*1.6).toFixed(2)+')', JSON.stringify(out[n])); }
 console.log('desk', JSON.stringify(out.desk)); process.exit(fail?1:0); })();
