import * as THREE from "three";
import { THREE_COLORS } from "../constants/colors";

export function buildDetector(scene) {
  const group = new THREE.Group();

  // Barrel layers
  const layers = [
    { r: 3, l: 14, color: THREE_COLORS.barrel[0], opacity: 0.20 },
    { r: 5, l: 14, color: THREE_COLORS.barrel[1], opacity: 0.15 },
    { r: 7, l: 14, color: THREE_COLORS.barrel[2], opacity: 0.10 },
  ];

  layers.forEach(({ r, l, color, opacity }) => {
    const fill = new THREE.Mesh(
      new THREE.CylinderGeometry(r, r, l, 48, 1, true),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity, side: THREE.DoubleSide })
    );
    fill.rotation.x = Math.PI / 2;
    group.add(fill);

    const wire = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.CylinderGeometry(r, r, l, 24, 6, true)),
      new THREE.LineBasicMaterial({ color: 0x1e3a5f, transparent: true, opacity: 0.4 })
    );
    wire.rotation.x = Math.PI / 2;
    group.add(wire);
  });

  // End caps
  [7, -7].forEach(z => {
    layers.forEach(({ r }, i) => {
      const inner = i === 0 ? 0.25 : layers[i - 1].r;
      const cap = new THREE.Mesh(
        new THREE.RingGeometry(inner, r, 32),
        new THREE.MeshBasicMaterial({ color: 0x1a2a4a, transparent: true, opacity: 0.12, side: THREE.DoubleSide })
      );
      cap.position.z = z;
      group.add(cap);
    });
  });

  // Beam pipe
  const pipe = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.18, 18, 16, 1, true),
    new THREE.MeshBasicMaterial({ color: THREE_COLORS.beamPipe, transparent: true, opacity: 0.7, side: THREE.DoubleSide })
  );
  pipe.rotation.x = Math.PI / 2;
  group.add(pipe);

  // Beam glow (returned so render loop can pulse it)
  const glow = new THREE.Mesh(
    new THREE.CylinderGeometry(0.055, 0.055, 18, 8),
    new THREE.MeshBasicMaterial({ color: THREE_COLORS.beamGlow, transparent: true, opacity: 0.6 })
  );
  glow.rotation.x = Math.PI / 2;
  group.add(glow);

  scene.add(group);
  return { group, glow };
}