/** Pure colour estimate of a lit MeshStandard diffuse surface (no three import, used by the selftest gate for
 * GLB look calibration): albedo/pi * (hemisphere + key * N.L) + emissive, Khronos PBR Neutral tone map, sRGB out.
 * Lights come from props.json "lights", the same block main.mjs builds the scene lights from. */
const s2l = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const l2s = (c) => { c = Math.max(0, Math.min(1, c)); return 255 * (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055); };
const hexLin = (h) => { const n = parseInt(String(h).replace('#', ''), 16); return [16, 8, 0].map((s) => s2l((n >> s) & 255)); };
const norm = (v) => { const l = Math.hypot(...v); return v.map((x) => x / l); };

export function neutralToneMap(c) {
  const start = 0.76, desat = 0.15;
  const x = Math.min(...c); const off = x < 0.08 ? x - 6.25 * x * x : 0.04;
  c = c.map((v) => v - off); const peak = Math.max(...c);
  if (peak < start) return c;
  const d = 1 - start; const np = 1 - d * d / (peak + d - start);
  c = c.map((v) => v * np / peak);
  const g = 1 - 1 / (desat * (peak - np) + 1);
  return c.map((v) => v * (1 - g) + np * g);
}

/** texSrgb: mean base-colour texel (0..255). cfg: {color_mult, emissive, emissive_intensity, emissive_map}. Returns sRGB 0..255. */
export function litCream(texSrgb, cfg, lights, normal = [0, 0.45, 0.9]) {
  const n = norm(normal); const L = norm(lights.key.dir);
  const w = 0.5 + 0.5 * n[1]; const sky = hexLin(lights.hemi.sky); const gnd = hexLin(lights.hemi.ground);
  const nl = Math.max(0, n[0] * L[0] + n[1] * L[1] + n[2] * L[2]); const key = hexLin(lights.key.color);
  const irr = [0, 1, 2].map((i) => (gnd[i] * (1 - w) + sky[i] * w) * lights.hemi.intensity + key[i] * lights.key.intensity * nl);
  const tex = texSrgb.map(s2l); const e = Array.isArray(cfg.emissive) ? cfg.emissive : hexLin(cfg.emissive);   // array = linear
  const lin = [0, 1, 2].map((i) => tex[i] * cfg.color_mult[i] * irr[i] / Math.PI + cfg.emissive_intensity * e[i] * (cfg.emissive_map ? tex[i] : 1));
  return neutralToneMap(lin).map(l2s);
}

export const rgbDist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

export const PLAIN = { color_mult: [1, 1, 1], emissive: [0, 0, 0], emissive_intensity: 0, emissive_map: false };
/** Linear base-colour factor pi / irradiance(normal) per channel: under `lights`, a GLB face at `normal` shows its own
 * texture colour (before tone mapping). Derived from the lights block only, so it follows any light change. */
export function lightNeutralMult(lights, normal) {
  const n = norm(normal); const L = norm(lights.key.dir);
  const w = 0.5 + 0.5 * n[1]; const sky = hexLin(lights.hemi.sky); const gnd = hexLin(lights.hemi.ground);
  const nl = Math.max(0, n[0] * L[0] + n[1] * L[1] + n[2] * L[2]); const key = hexLin(lights.key.color);
  return [0, 1, 2].map((i) => Math.PI / ((gnd[i] * (1 - w) + sky[i] * w) * lights.hemi.intensity + key[i] * lights.key.intensity * nl));
}
