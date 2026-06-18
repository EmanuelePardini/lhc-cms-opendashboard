import * as THREE from "three";
import { THREE_COLORS } from "../constants/colors";

const B_FIELD   = 3.8;   // Tesla, campo magnetico CMS
const SCENE_SCALE = 8;   // fattore di scala GeV/c → unità scena

function makeHelix(px, py, pz, charge, length = 9.5, steps = 120) {
  const pTotal = Math.sqrt(px * px + py * py + pz * pz) || 1;
  const pT     = Math.sqrt(px * px + py * py) || 0.001;  // momento trasverso reale

  // Direzione iniziale nel piano trasverso
  const sinPhi = px / pT;
  const cosPhi = py / pT;

  // Curvatura fisica: inversamente proporzionale a pT
  // Alta energia → quasi dritta; bassa energia → molto curva
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

function buildTrack(px, py, pz, charge) {
  const spline = makeHelix(px, py, pz, charge);
  const color  = charge > 0 ? THREE_COLORS.muonPos : THREE_COLORS.muonNeg;
  const group  = new THREE.Group();

  group.add(new THREE.Mesh(
    new THREE.TubeGeometry(spline, 64, 0.024, 6, false),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.95 })
  ));
  group.add(new THREE.Mesh(
    new THREE.TubeGeometry(spline, 40, 0.07, 6, false),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.15 })
  ));

  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(0.14, 10, 10),
    new THREE.MeshBasicMaterial({ color })
  );
  dot.position.copy(spline.getPoint(1));
  group.add(dot);

  return group;
}

function buildVertex(isZCandidate) {
  const color = isZCandidate ? THREE_COLORS.vertexZ : THREE_COLORS.vertexOther;
  const group = new THREE.Group();

  group.add(new THREE.Mesh(
    new THREE.SphereGeometry(0.18, 16, 16),
    new THREE.MeshBasicMaterial({ color })
  ));
  group.add(new THREE.Mesh(
    new THREE.SphereGeometry(0.42, 16, 16),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.12, wireframe: true })
  ));
  return group;
}

export function buildTracks(scene, eventData) {
  const group = new THREE.Group();
  if (eventData) {
    const { px1, py1, pz1, px2, py2, pz2, q1, q2, z_candidate } = eventData;
    group.add(buildTrack(px1, py1, pz1, q1));
    group.add(buildTrack(px2, py2, pz2, q2));
    group.add(buildVertex(z_candidate === 1));
  }
  scene.add(group);
  return group;
}