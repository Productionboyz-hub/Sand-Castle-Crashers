# patch_water11.py <in.html> <out.html> - lacy foam and see-through shallows (drawing only).
# Reference: J's beach clips (reference.beach/) - foam is a wide band of white lace (a web of strands with water
# showing through the holes), thickest at the leading edge; the shallows are clear green-turquoise over sand,
# with darker patches on the bottom, and only turn deep blue further out.
# Applied on top of the combined feature/sprites-water build.
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, ('anchor not found exactly once', old[:80])
    s = s.replace(old, new)


# 1. colours + knobs
rep('''const WATER_SHALLOW = [118, 212, 206];
const WATER_MID     = [36, 148, 186];
const WATER_DEEP    = [14, 60, 120];
''', '''const WATER_SHALLOW = [72, 196, 192];    // clear green-turquoise: mostly sand shows through it
const WATER_MID     = [26, 136, 168];
const WATER_DEEP    = [14, 60, 120];
const SHALLOW_CLEAR = 4.5;    // ← TUNE: tiles of see-through water behind the tide line before it turns opaque
const SHALLOW_ALPHA = 0.30;   // ← TUNE: water colour over the sand at the very edge (0 = clear as glass)
const SEABED_PATCH  = 0.40;   // ← TUNE: strength of the dark weed / rock patches seen through the shallows
const SEABED_TINT   = 'rgba(40,70,60,0.16)';    // sand under water is darker, like wet sand
const FOAM_DEPTH    = 2.6;    // ← TUNE: tiles of lacy foam behind the leading edge (a fresh wave gets all of it)
const FOAM_LACE     = 0.7;    // ← TUNE: size of the holes in the foam web, in tiles (bigger = coarser lace)
const FOAM_RESIDUAL = 0.15;   // ← TUNE: faint lace left floating over the rest of the shallows
''')

# 2. see-through shallows + seabed patches
rep('''      let a = 0.40 + 0.60 * Math.min(1, dp / (th * 1.5));
''', '''      const cl = Math.min(1, dp / (th * SHALLOW_CLEAR)), clS = cl * cl * (3 - 2 * cl);   // 0 at the tide line, 1 = open water
      let a = SHALLOW_ALPHA + (1 - SHALLOW_ALPHA) * clS;
      if (clS < 1) {                          // the bottom seen through clear water: darker weed / rock patches
        const sb = seabed[y * WW + x];        // the bottom does not move: worked out once per zoom (seabedFor)
        if (sb > 0) {
          const f = sb * SEABED_PATCH * (1 - clS) * Math.min(1, dp / (th * 0.6));
          r += (30 - r) * f; g += (84 - g) * f; b += (80 - b) * f;
          a += (0.62 - a) * f;
        }
      }
''')

# 3. the foam. Low-res water texture: only a milky body under thick foam and faint lace drifting over the shallows.
#    The crisp web of strands is drawn by buildFoamTex() at full screen resolution (section FOAM LAYER).
rep('''      if (dv < band) {
        const lace = noise2(wxf * 2.3 + t * 0.5, wy * 4.2 + t * 0.9);
        const f = (1 - dv / band) * (lace > -0.05 ? 0.78 : 0.16);
        r += (255 - r) * f; g += (255 - g) * f; b += (255 - b) * f;
        if (f > a) a = f;
      }
''', '''      // FOAM (body): milky white under the thick foam near the edge - the strands themselves are buildFoamTex()
      const fc = dv < FOAM_DEPTH * th ? foamCover(dv, th, tideY - edgeY, colPatch) : 0;
      const fw = fc * fc * 0.32;
      if (fw > 0.005) {
        r += (250 - r) * fw; g += (253 - g) * fw; b += (255 - b) * fw;
        if (fw > a) a = fw;
      }
''')
rep('''  wCtx.putImageData(wImg, 0, 0);
}
''', '''  wCtx.putImageData(wImg, 0, 0);
  buildFoamTex(t);
}

// ── FOAM LAYER (full resolution) ──────────────────────────────────
// The foam's web of strands, drawn at screen resolution so the lace stays crisp (the water texture above is
// built at 1/W_SCALE). A tileable lace field is made once; each build only looks it up and thresholds it:
// strands fatten and the holes close up where the foam cover is thick. Drawing only.
const LACE_N = 256;                         // lace field size, px (tiles seamlessly)
const LACE_CELL = LACE_N / 6;               // px per web cell in the field
const laceField = new Uint8Array(LACE_N * LACE_N);
(function buildLaceField() {
  const pnoise = function (x, y, P) {       // gradient noise that repeats every P cells
    const X = Math.floor(x), Y = Math.floor(y), xf = x - X, yf = y - Y;
    const h = function (i, j) { return PERM[(PERM[(X + i) % P] + (Y + j) % P) & 255] & 7; };
    const u = fade(xf), v = fade(yf);
    return lerp(lerp(grad2(h(0, 0), xf, yf), grad2(h(1, 0), xf - 1, yf), u),
                lerp(grad2(h(0, 1), xf, yf - 1), grad2(h(1, 1), xf - 1, yf - 1), u), v);
  };
  for (let y = 0; y < LACE_N; y++) for (let x = 0; x < LACE_N; x++) {
    // each family = two octaves, the finer one shifted off the lattice: plain gradient noise is 0 at every lattice
    // point, which would put a bright star on a regular grid
    const u = x / LACE_CELL, v = y / LACE_CELL;
    const n1 = Math.abs(pnoise(u, v, 6) + 0.45 * pnoise(u * 2 + 0.37, v * 2 + 0.71, 12));
    const n2 = Math.abs(pnoise(u * 1.833 + 0.53, v * 1.833 + 0.19, 11) + 0.45 * pnoise(u * 3.667 + 0.21, v * 3.667 + 0.87, 22));
    laceField[y * LACE_N + x] = Math.min(255, Math.round(Math.min(n1, n2 * 1.25) / 0.6 * 255));
  }
})();
const foamCanvas = document.createElement('canvas');
const foamCtx = foamCanvas.getContext('2d');
let foamImg = null, foamY0 = 0, foamRows = 0;
let foamFlow = null;                        // sideways drift for the lace: flowPh with its slope limited (see buildFoamTex)
const FOAM_FLOW_SLOPE = 0.25;               // max px of drift difference per px across - steeper smears the lace into stripes

// stretches of the beach carry more foam than others (0 .. 1.5)
function foamPatch(wxf, wy, t) { return Math.max(0, 0.7 + 0.8 * noise2(wxf * 0.17 + t * 0.03, wy * 0.33 - t * 0.02)); }
// foam cover 0..1 at dv px behind the leading edge; run = how far the current wave has run up past the tide line
function foamCover(dv, th, run, patch) {
  const fresh = Math.min(1, Math.max(0, run) / (th * 1.6));
  const depth = FOAM_DEPTH * (0.45 + 0.55 * fresh) * th, lip = th * (0.25 + 0.3 * Math.min(1, patch));
  let cov = dv < depth ? Math.pow(1 - dv / depth, 0.8) * patch : 0;
  if (dv < lip) cov = Math.max(cov, 1 - 0.4 * dv / lip);   // the rolled lip right at the edge, lumpy
  return cov > 1 ? 1 : cov;
}

const FOAM_POW = new Float32Array(257);     // x^0.8 (cover falloff), by 1/256
const FOAM_SW  = new Float32Array(257);     // strand half-width for a cover, by 1/256
for (let i = 0; i <= 256; i++) { FOAM_POW[i] = Math.pow(i / 256, 0.8); FOAM_SW[i] = (0.045 + 0.42 * Math.pow(i / 256, 1.25)) * 255 / 0.6; }

function buildFoamTex(t) {
  const th = Math.max(TH(), WATER_PATTERN_MIN_PX);
  const reach = Math.ceil((FOAM_DEPTH + SHALLOW_CLEAR * 0.5) * th) + 2;   // the foam band, then faint lace over the shallows
  let y0 = 1e9, y1 = -1e9;
  for (let i = 0; i < SWASH_N; i++) { if (visY[i] < y0) y0 = visY[i]; if (visY[i] > y1) y1 = visY[i]; }
  y0 = Math.max(0, Math.floor(y0)); y1 = Math.min(SH, Math.ceil(y1) + reach);
  const rows = y1 - y0;
  foamY0 = y0; foamRows = rows;
  if (rows <= 0) return;
  if (!foamImg || foamImg.height < rows || foamImg.width !== SW) {
    foamCanvas.width = SW; foamCanvas.height = rows + 32;
    foamImg = foamCtx.createImageData(SW, rows + 32);
  }
  const d = foamImg.data;
  d.fill(0);
  const k = LACE_CELL / (1.5 * th * FOAM_LACE);            // lace field px per screen px
  const m = LACE_N - 1;
  const ay = t * 7, by = -t * 5, bx = t * 9;               // the two webs drift apart slowly, so the lace keeps changing
  const ky1 = k * 1.15, ky2 = k * 0.9;
  const kw = k > 1 ? k : 1;                                 // small screens: keep strands at least ~1 px wide (else they break into dots)
  const soft = 255 / 0.6 * 0.07 * kw;
  // the lace rides the sideways flow, but where neighbouring columns slide at very different speeds the web would
  // be stretched into streaks: limit how fast the drift may change across the screen (forward + backward pass)
  const lim = FOAM_FLOW_SLOPE * SWASH_STEP;
  if (!foamFlow) foamFlow = new Float32Array(SWASH_N);   // SWASH_N is declared further down the file
  foamFlow[0] = flowPh[0];
  for (let i = 1; i < SWASH_N; i++) { const p = foamFlow[i - 1]; foamFlow[i] = Math.max(p - lim, Math.min(p + lim, flowPh[i])); }
  for (let i = SWASH_N - 2; i >= 0; i--) { const p = foamFlow[i + 1]; foamFlow[i] = Math.max(p - lim, Math.min(p + lim, foamFlow[i])); }
  for (let x = 0; x < SW; x++) {
    const edge = visShoreYAt(x), tide = baseShoreYAt(x), run = tide - edge, flow = swashLerp(foamFlow, x);
    const patch = foamPatch((x - flow) / th, edge / th, t);
    // foamCover(), unrolled for this column
    const fresh = Math.min(1, Math.max(0, run) / (th * 1.6));
    const depth = FOAM_DEPTH * (0.45 + 0.55 * fresh) * th, lip = th * (0.25 + 0.3 * Math.min(1, patch));
    const resK = FOAM_RESIDUAL * patch, clSpan = th * SHALLOW_CLEAR;
    const ax = ((x - flow) * k) & m, bxx = ((x - flow) * k * 0.8 + bx + 97) & m;
    const ys = Math.max(y0, Math.ceil(edge)), ye = Math.min(y1, Math.ceil(edge) + reach);
    for (let y = ys; y < ye; y++) {
      const dv = y - edge;
      let cov = dv < depth ? FOAM_POW[(256 * (1 - dv / depth)) | 0] * patch : 0;
      if (dv < lip) { const l = 1 - 0.4 * dv / lip; if (l > cov) cov = l; }
      if (resK > 0) {                                       // faint lace left floating over the shallows
        let cl = y > tide ? (y - tide) / clSpan : 0; if (cl > 1) cl = 1;
        const tail = 1 - dv / reach;                        // fades to nothing before the end of the layer
        const res = resK * (1 - cl * cl * (3 - 2 * cl)) * (tail < 0.3 ? tail / 0.3 : 1);
        if (res > cov) cov = res;
      }
      if (cov < 0.02) continue;
      if (cov > 1) cov = 1;
      const fa = laceField[((y * ky1 + ay) & m) * LACE_N + ax];
      const fb = laceField[((y * ky2 + by) & m) * LACE_N + bxx];
      // how far this pixel is from the nearest strand vs how fat the strands are at this cover
      let f = (FOAM_SW[(cov * 256) | 0] * kw - (fa < fb ? fa : fb)) / soft;
      if (f <= 0) continue;
      if (f > 1) f = 1;
      const i = ((y - y0) * SW + x) * 4;
      d[i] = 248; d[i + 1] = 252; d[i + 2] = 255; d[i + 3] = f * (0.62 + 0.38 * cov) * 255;
    }
  }
  foamCtx.clearRect(0, 0, foamCanvas.width, foamCanvas.height);
  foamCtx.putImageData(foamImg, 0, 0);
}
''')

# 4. sand under the water is darker (one fill under the clipped water)
rep('''function drawOceanOverlay() {
  drawWetSand();
  buildShorelinePath();
  ctx.save();
  ctx.clip();
''', '''function drawOceanOverlay() {
  drawWetSand();
  buildShorelinePath();
  ctx.save();
  ctx.clip();
  ctx.fillStyle = SEABED_TINT;                 // the sand under the clear shallows is wet and darker
  ctx.fillRect(0, 0, SW, SH);
''')

rep('''  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(wCanvas, 0, 0, SW, SH);
  ctx.restore();
''', '''  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(wCanvas, 0, 0, SW, SH);
  if (foamRows > 0) ctx.drawImage(foamCanvas, 0, foamY0);   // crisp foam strands (FOAM LAYER)
  ctx.restore();
''')

# 5. speed: foam patchiness once per column, seabed patches worked out once per zoom
rep('''    const tideY = baseShoreYAt(sx);           // the tide line the surge runs up from
''', '''    const tideY = baseShoreYAt(sx);           // the tide line the surge runs up from
    const colPatch = foamPatch((sx - (foamFlow ? swashLerp(foamFlow, sx) : 0)) / th, edgeY / th, t);   // how much foam this stretch carries
''')
rep('''function buildWaterTex(t) {
  const data = wImg.data;
  const th = Math.max(TH(), WATER_PATTERN_MIN_PX);   // pattern scale, floored so phones don't alias
''', '''// Dark patches on the bottom (weed, rock), 0..1 per water texel. Worked out once for each pattern scale.
let seabed = null, seabedTh = -1;
function seabedFor(th) {
  if (seabedTh === th) return seabed;
  seabedTh = th;
  seabed = new Float32Array(WW * WH);
  for (let y = 0; y < WH; y++) for (let x = 0; x < WW; x++) {
    const wx = x * W_SCALE / th, wy = y * W_SCALE / th;
    const sb = noise2(wx * 0.32 + 5.1, wy * 0.62 - 2.3) + 0.5 * noise2(wx * 0.9 + 1.7, wy * 1.7 + 7.7);
    seabed[y * WW + x] = sb > 0.12 ? Math.min(1, (sb - 0.12) * 2.2) : 0;
  }
  return seabed;
}

function buildWaterTex(t) {
  const data = wImg.data;
  const th = Math.max(TH(), WATER_PATTERN_MIN_PX);   // pattern scale, floored so phones don't alias
  const seabed = seabedFor(th);
''')

open(dst, 'w', encoding='utf-8').write(s)
print('patch_water11: ok ->', dst)
