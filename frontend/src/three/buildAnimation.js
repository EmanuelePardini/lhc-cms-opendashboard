import * as THREE from "three";
import { THREE_COLORS } from "../constants/colors";
import { makeHelix } from "./makeHelix"; 

const PHASES = {
  APPROACH:    { start: 0.0,  end: 1.2 },
  COLLISION:   { start: 1.2,  end: 1.8 },
  PROPAGATION: { start: 1.8,  end: 4.5 },
  HOLD:        { start: 4.5,  end: 5.5 },
};
const TOTAL_DURATION = 5.5;

const B_FIELD    = 3.8;
const SCENE_SCALE = 8;

//  Helpers 

function easeInOut(t) {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

function lerpClamped(a, b, t) {
  return a + (b - a) * Math.max(0, Math.min(1, t));
}

function phaseProgress(t, phase) {
  const { start, end } = PHASES[phase];
  return Math.max(0, Math.min(1, (t - start) / (end - start)));
}

//  Proton bunches 

function makeProton(direction) {
  const group = new THREE.Group();

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(0.12, 12, 12),
    new THREE.MeshBasicMaterial({ color: 0x00c8ff, transparent: true, opacity: 0.9 })
  );
  group.add(core);

  // Lorentz-contracted disc (proton looks flattened at relativistic speed)
  const disc = new THREE.Mesh(
    new THREE.CylinderGeometry(0.22, 0.22, 0.04, 16),
    new THREE.MeshBasicMaterial({ color: 0x00c8ff, transparent: true, opacity: 0.35 })
  );
  disc.rotation.x = Math.PI / 2;
  group.add(disc);

  // Wake trail
  const trailGeo = new THREE.CylinderGeometry(0.03, 0.06, 1.8, 8);
  const trail = new THREE.Mesh(
    trailGeo,
    new THREE.MeshBasicMaterial({ color: 0x00c8ff, transparent: true, opacity: 0.18 })
  );
  trail.rotation.x = Math.PI / 2;
  trail.position.z = direction * 0.9;
  group.add(trail);

  return { group, core, disc, trail };
}

//  Collision flash 

function makeFlash(isZCandidate) {
  const color = isZCandidate ? THREE_COLORS.vertexZ : 0xffffff;
  const group = new THREE.Group();

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(0.08, 12, 12),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0 })
  );
  group.add(core);

  const rings = [];
  for (let i = 0; i < 3; i++) {
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.1 + i * 0.15, 0.015, 6, 32),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0 })
    );
    ring.rotation.x = Math.PI / 2 * (i % 2);
    group.add(ring);
    rings.push(ring);
  }

  return { group, core, rings };
}

//  Hadronic jets (procedural, illustrative) 

function makeJets(seed) {
  const group  = new THREE.Group();
  const nJets  = 6 + (seed % 4);
  const lines  = [];

  for (let i = 0; i < nJets; i++) {
    const angle  = (i / nJets) * Math.PI * 2 + seed * 0.3;
    const eta    = (((seed * 7 + i * 13) % 20) - 10) * 0.12; // pseudorapidity spread
    const len    = 2.5 + ((seed * 3 + i * 7) % 10) * 0.3;

    const dir = new THREE.Vector3(
      Math.cos(angle) * Math.cos(eta),
      Math.sin(angle) * Math.cos(eta),
      Math.sin(eta)
    ).normalize();

    const pts = [
      new THREE.Vector3(0, 0, 0),
      dir.clone().multiplyScalar(len),
    ];

    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = new THREE.LineBasicMaterial({
      color: 0xff8c00,
      transparent: true,
      opacity: 0,
    });
    const line = new THREE.Line(geo, mat);
    group.add(line);
    lines.push({ line, mat, maxLen: len, dir });
  }

  return { group, lines };
}

//  Animated muon track 

function makeAnimatedTrack(px, py, pz, charge) {
  // Usa esattamente la stessa formula della vista statica
  const spline = makeHelix(px, py, pz, charge);
  const color  = charge > 0 ? THREE_COLORS.muonPos : THREE_COLORS.muonNeg;

  const divisions = 200;
  const tubeGeo   = new THREE.TubeGeometry(spline, divisions, 0.024, 6, false);
  const glowGeo   = new THREE.TubeGeometry(spline, divisions, 0.07,  6, false);

  const tubeMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0 });
  const glowMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0 });

  const tube = new THREE.Mesh(tubeGeo, tubeMat);
  const glow = new THREE.Mesh(glowGeo, glowMat);

  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(0.14, 10, 10),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0 })
  );
  dot.position.copy(spline.getPoint(1));

  const group = new THREE.Group();
  group.add(tube, glow, dot);

  const totalIdx = tubeGeo.index
    ? tubeGeo.index.count
    : tubeGeo.attributes.position.count;

  const setProgress = (p) => {
    const clamped = Math.max(0, Math.min(1, p));
    tubeGeo.setDrawRange(0, Math.floor(clamped * totalIdx));
    glowGeo.setDrawRange(0, Math.floor(clamped * totalIdx));
    tubeMat.opacity = clamped > 0 ? 0.95 : 0;
    glowMat.opacity = clamped > 0 ? 0.15 : 0;
    dot.material.opacity = clamped > 0.98 ? 1 : 0;
  };

  setProgress(0);
  return { group, setProgress };
}

//  Main export 

export function buildAnimation(scene, eventData) {
  if (!eventData) return { update: () => {}, dispose: () => {} };

  const { px1, py1, pz1, px2, py2, pz2, q1, q2, z_candidate, id } = eventData;
  const root = new THREE.Group();

  // Proton bunches: approach from ±z
  const proton1 = makeProton(-1);
  const proton2 = makeProton(+1);
  root.add(proton1.group, proton2.group);

  // Collision flash
  const flash = makeFlash(z_candidate === 1);
  root.add(flash.group);

  // Hadronic jets (illustrative, uses event id as seed for determinism)
  const jets = makeJets(id ?? 0);
  root.add(jets.group);

  // Animated muon tracks
  const track1 = makeAnimatedTrack(px1, py1, pz1, q1);
  const track2 = makeAnimatedTrack(px2, py2, pz2, q2);
  root.add(track1.group, track2.group);

  scene.add(root);

  //  Per-frame update 

  const update = (elapsed) => {
    // Loop
    const t = elapsed % TOTAL_DURATION;

    //  PHASE 1: Approach 
    const approachP = phaseProgress(t, "APPROACH");
    const eased     = easeInOut(approachP);

    // Protons travel from z=±11 toward z=0
    const startZ = 11;
    proton1.group.position.z =  lerpClamped( startZ, 0, eased);
    proton2.group.position.z =  lerpClamped(-startZ, 0, eased);

    // Fade in as they approach
    const approachOpacity = approachP > 0.1 ? 1 : approachP * 10;
    proton1.core.material.opacity = approachOpacity * 0.9;
    proton2.core.material.opacity = approachOpacity * 0.9;
    proton1.disc.material.opacity = approachOpacity * 0.35;
    proton2.disc.material.opacity = approachOpacity * 0.35;
    proton1.trail.material.opacity = approachOpacity * 0.18;
    proton2.trail.material.opacity = approachOpacity * 0.18;

    // Hide protons after collision
    const hideProtons = t > PHASES.COLLISION.start ? 1 : 0;
    if (hideProtons) {
      proton1.core.material.opacity = 0;
      proton2.core.material.opacity = 0;
      proton1.disc.material.opacity = 0;
      proton2.disc.material.opacity = 0;
      proton1.trail.material.opacity = 0;
      proton2.trail.material.opacity = 0;
    }

    //  PHASE 2: Collision 
    const collP = phaseProgress(t, "COLLISION");

    // Flash: peaks at midpoint then fades
    const flashIntensity = Math.sin(collP * Math.PI);
    flash.core.material.opacity  = flashIntensity * 0.95;
    flash.core.scale.setScalar(1 + collP * 3);
    flash.rings.forEach((ring, i) => {
      const ringP = Math.max(0, collP - i * 0.15);
      ring.material.opacity = Math.sin(ringP * Math.PI) * 0.6;
      ring.scale.setScalar(1 + ringP * 4);
    });

    // Jets: appear during collision, fade out early in propagation
    const jetFade = collP > 0.3
      ? Math.max(0, 1 - phaseProgress(t, "PROPAGATION") * 2.5)
      : collP * 3;
    jets.lines.forEach(({ mat, line, maxLen, dir }, i) => {
      const offset = i * 0.08;
      const p      = Math.max(0, Math.min(1, (collP - offset) * 3));
      mat.opacity  = jetFade * 0.22 * p;
    });

    //  PHASE 3: Propagation 
    const propP = phaseProgress(t, "PROPAGATION");

    // Flash fades as tracks appear
    if (t > PHASES.PROPAGATION.start) {
      flash.core.material.opacity = Math.max(0, flash.core.material.opacity - 0.04);
    }

    track1.setProgress(easeInOut(propP));
    track2.setProgress(easeInOut(propP));

    //  PHASE 4: Hold — everything visible, smooth loop prep 
    const holdP = phaseProgress(t, "HOLD");
    if (holdP > 0) {
      // Fade everything out for clean loop
      const fadeOut = easeInOut(holdP);
      track1.group.children.forEach(m => { if (m.material) m.material.opacity *= (1 - fadeOut); });
      track2.group.children.forEach(m => { if (m.material) m.material.opacity *= (1 - fadeOut); });
      flash.core.material.opacity  *= (1 - fadeOut);
      flash.rings.forEach(r => { r.material.opacity *= (1 - fadeOut); });
    }
  };

  const dispose = () => {
    scene.remove(root);
  };

  return { update, dispose };
}