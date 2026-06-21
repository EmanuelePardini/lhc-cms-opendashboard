import * as THREE from "three";
import { buildDetector } from "./buildDetector";
import { buildTracks }   from "./buildTracks";
import { buildCamera }   from "./buildCamera";

export function initScene(canvas, eventData) {
  const W = canvas.clientWidth  || 800;
  const H = canvas.clientHeight || 600;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W, H, false);
  renderer.setClearColor(0xf2f4f8, 1);

  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(0x0a1830, 4));
  const dLight = new THREE.DirectionalLight(0x00c8ff, 1);
  dLight.position.set(5, 10, 8);
  scene.add(dLight);

  const { group: detectorGroup, glow: beamGlow } = buildDetector(scene);
  buildTracks(scene, eventData);
  const { camera, tick: cameraTick, resize, destroy: destroyCamera } = buildCamera(canvas);

  const clock = new THREE.Clock();
  let alive   = true;

  const tick = () => {
    if (!alive) return;
    requestAnimationFrame(tick);
    const t = clock.getElapsedTime();
    beamGlow.material.opacity = 0.3 + 0.22 * Math.sin(t * 4.5);
    detectorGroup.rotation.z  = t * 0.035;
    cameraTick();
    renderer.render(scene, camera);
  };
  tick();

  const handleResize = () => {
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    resize();
  };
  window.addEventListener("resize", handleResize);

  return () => {
    alive = false;
    destroyCamera();
    window.removeEventListener("resize", handleResize);
    renderer.dispose();
  };
}