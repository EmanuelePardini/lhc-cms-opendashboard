import * as THREE from "three";
import { THREE_COLORS } from "../constants/colors";

// Nominal axial magnetic field of the CMS solenoid along the z-axis (beam axis)
const B_FIELD   = 3.8;   // Tesla
// Visual scaling factor to map physical momentum (GeV/c) to WebGL scene units
const SCENE_SCALE = 8;   

/**
 * Simulates the helical trajectory of a relativistic charged lepton (muon) 
 * moving through a uniform axial magnetic field.
 */
function makeHelix(px, py, pz, charge, length = 9.5, steps = 120) {
  // Total momentum magnitude: $p = \sqrt{p_x^2 + p_y^2 + p_z^2}$
  const pTotal = Math.sqrt(px * px + py * py + pz * pz) || 1;
  
  // Transverse momentum: $p_T = \sqrt{p_x^2 + p_y^2}$. 
  // Crucial in collider physics as it is invariant under longitudinal Lorentz boosts.
  const pT     = Math.sqrt(px * px + py * py) || 0.001;  

  // Initial azimuthal angle ($\phi$) orientation in the transverse ($xy$) plane
  const sinPhi = px / pT;
  const cosPhi = py / pT;

  // Relativistic Cyclotron Radius Formula: $p_T = 0.3 \cdot B \cdot R$
  // Curvature ($\kappa = 1/R$) is inversely proportional to $p_T$.
  // High $p_T$ particles yield straight tracks; low $p_T$ tracks curve aggressively.
  // The sign of the charge dictates the direction of bending via the Lorentz force: $\vec{F} = q(\vec{v} \times \vec{B})$
  const curvature = charge * (0.3 * B_FIELD) / (pT * SCENE_SCALE);

  const pts = [];
  for (let i = 0; i <= steps; i++) {
    // Parameter t represents the radial step propagating outward from the interaction point
    const t = (i / steps) * length;
    
    // Bending angle in radians accumulated due to the transverse magnetic field deflection
    const a = curvature * t;
    
    // Parametric coordinates of the helix. 
    // The axial field causes circular motion in $xy$, while the $z$ motion remains unaffected.
    pts.push(new THREE.Vector3(
      t * (sinPhi * Math.cos(a) + cosPhi * Math.sin(a)),
      t * (cosPhi * Math.cos(a) - sinPhi * Math.sin(a)),
      t * (pz / pTotal) // Constant velocity propagation along the longitudinal beam axis (z)
    ));
  }
  return new THREE.CatmullRomCurve3(pts);
}

/**
 * Builds the visual representation of a muon track.
 * Differentiates matter ($\mu^-$) from antimatter ($\mu^+$) using distinct color channels.
 */
function buildTrack(px, py, pz, charge) {
  const spline = makeHelix(px, py, pz, charge);
  // Color coding tracks based on charge sign for quick topological analysis
  const color  = charge > 0 ? THREE_COLORS.muonPos : THREE_COLORS.muonNeg;
  const group  = new THREE.Group();

  // Core high-energy ionization path (the track core)
  group.add(new THREE.Mesh(
    new THREE.TubeGeometry(spline, 64, 0.024, 6, false),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.95 })
  ));
  
  // Outer halo mimicking the electromagnetic shower interaction glow
  group.add(new THREE.Mesh(
    new THREE.TubeGeometry(spline, 40, 0.07, 6, false),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.15 })
  ));

  // Visual terminal marker indicating where the particle hits the outer Muon Chambers
  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(0.14, 10, 10),
    new THREE.MeshBasicMaterial({ color })
  );
  dot.position.copy(spline.getPoint(1));
  group.add(dot);

  return group;
}

/**
 * Renders the primary interaction vertex (the beam-beam collision point).
 * Highlights resonant states such as $Z^0 \rightarrow \mu^+\mu^-$ candidates.
 */
function buildVertex(isZCandidate) {
  // If the dimuon invariant mass falls within the $Z$-boson window ($\approx 91\text{ GeV/c}^2$), 
  // it flashes the designated resonance color code.
  const color = isZCandidate ? THREE_COLORS.vertexZ : THREE_COLORS.vertexOther;
  const group = new THREE.Group();

  // Primary vertex dense core
  group.add(new THREE.Mesh(
    new THREE.SphereGeometry(0.18, 16, 16),
    new THREE.MeshBasicMaterial({ color })
  ));
  
  // Wireframe bubble representing the space-time uncertainty of the decay vertex
  group.add(new THREE.Mesh(
    new THREE.SphereGeometry(0.42, 16, 16),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.12, wireframe: true })
  ));
  return group;
}

/**
 * Main entry point to map raw CMS dimuon event data arrays into the 3D WebGL space.
 */
export function buildTracks(scene, eventData) {
  const group = new THREE.Group();
  if (eventData) {
    const { px1, py1, pz1, px2, py2, pz2, q1, q2, z_candidate } = eventData;
    
    // Reconstruct muon 1 and muon 2 tracks using their 3-momentum vectors and electrical charges
    group.add(buildTrack(px1, py1, pz1, q1));
    group.add(buildTrack(px2, py2, pz2, q2));
    
    // Plot the shared origin decay vertex
    group.add(buildVertex(z_candidate === 1));
  }
  scene.add(group);
  return group;
}