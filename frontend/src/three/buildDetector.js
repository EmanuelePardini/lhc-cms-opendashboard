import * as THREE from "three";
import { THREE_COLORS } from "../constants/colors";

/**
 * Constructs a simplified 3D representation of a hermetic collider detector (e.g., CMS).
 * Uses standard HEP coordinate systems where the z-axis runs parallel to the beamline
 * and the origin (0,0,0) represents the primary Interaction Point (IP).
 */
export function buildDetector(scene) {
  const group = new THREE.Group();

  // Concentric Barrel layers representing major sub-detector subsystems.
  // In a real experiment, these correspond to the Inner Tracker, 
  // Electromagnetic Calorimeter (ECAL), and Hadronic Calorimeter (HCAL).
  const layers = [
    { r: 3, l: 14, color: THREE_COLORS.barrel[0], opacity: 0.20 }, // Innermost tracking volume
    { r: 5, l: 14, color: THREE_COLORS.barrel[1], opacity: 0.15 }, // Calorimetry layer (energy absorption)
    { r: 7, l: 14, color: THREE_COLORS.barrel[2], opacity: 0.10 }, // Outer magnet yoke / Muon spectrometer boundary
  ];

  layers.forEach(({ r, l, color, opacity }) => {
    // Generate the cylindrical barrel mesh. 
    // The open-ended cylinder ('true') leaves room for the forward endcaps.
    const fill = new THREE.Mesh(
      new THREE.CylinderGeometry(r, r, l, 48, 1, true),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity, side: THREE.DoubleSide })
    );
    // Rotate 90 degrees to align the cylinder's longitudinal axis with the z-axis (beamline)
    fill.rotation.x = Math.PI / 2;
    group.add(fill);

    // Structural wireframe mimicking the segmentation (readout channels/sectors) 
    // typical of particle detector modular configurations.
    const wire = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.CylinderGeometry(r, r, l, 24, 6, true)),
      new THREE.LineBasicMaterial({ color: 0x1e3a5f, transparent: true, opacity: 0.4 })
    );
    wire.rotation.x = Math.PI / 2;
    group.add(wire);
  });

  // Forward and Backward Endcaps located at z = +7 and z = -7 meters.
  // These planar discs ensure 4pi solid angle coverage (hermeticity), 
  // intercepting high-pseudorapidity particles flying close to the beam pipe.
  [7, -7].forEach(z => {
    layers.forEach(({ r }, i) => {
      // Calculates the inner radius of each ring to create gapless, nested discs
      const inner = i === 0 ? 0.25 : layers[i - 1].r;
      const cap = new THREE.Mesh(
        new THREE.RingGeometry(inner, r, 32),
        new THREE.MeshBasicMaterial({ color: 0x1a2a4a, transparent: true, opacity: 0.12, side: THREE.DoubleSide })
      );
      cap.position.z = z; // Position longitudinally along the beam axis
      group.add(cap);
    });
  });

  // The Central Beam Pipe.
  // A ultra-high vacuum tube (typically made of Beryllium to minimize 
  // secondary particle interactions/nuclear scattering) where the beams circulate.
  const pipe = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.18, 18, 16, 1, true),
    new THREE.MeshBasicMaterial({ color: THREE_COLORS.beamPipe, transparent: true, opacity: 0.7, side: THREE.DoubleSide })
  );
  pipe.rotation.x = Math.PI / 2;
  group.add(pipe);

  // Relativistic Particle Beam Glow.
  // Visualizes the trajectory of colliding proton bunches traveling at 99.999999% the speed of light.
  // Returned to the core render loop to allow dynamic amplitude pulsing.
  const glow = new THREE.Mesh(
    new THREE.CylinderGeometry(0.055, 0.055, 18, 8),
    new THREE.MeshBasicMaterial({ color: THREE_COLORS.beamGlow, transparent: true, opacity: 0.6 })
  );
  glow.rotation.x = Math.PI / 2;
  group.add(glow);

  scene.add(group);
  return { group, glow };
}