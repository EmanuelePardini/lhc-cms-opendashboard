import * as THREE from "three";

const B_FIELD    = 3.8;
const SCENE_SCALE = 8;

export function makeHelix(px, py, pz, charge, length = 9.5, steps = 120) {
  const pTotal = Math.sqrt(px * px + py * py + pz * pz) || 1;
  const pT     = Math.sqrt(px * px + py * py) || 0.001;
  const sinPhi = px / pT;
  const cosPhi = py / pT;

  const curvature = charge * (0.3 * B_FIELD) / (pT * SCENE_SCALE);

  const pts = [];
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * length;
    const a = curvature * t;
    pts.push(new THREE.Vector3(
      t * (sinPhi * Math.cos(a) + cosPhi * Math.sin(a)),
      t * (cosPhi * Math.cos(a) - sinPhi * Math.sin(a)),
      t * (pz / pTotal)
    ));
  }
  return new THREE.CatmullRomCurve3(pts);
}