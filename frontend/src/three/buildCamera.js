import * as THREE from "three";

export function buildCamera(canvas) {
  const W = canvas.clientWidth  || 800;
  const H = canvas.clientHeight || 600;
  const camera = new THREE.PerspectiveCamera(55, W / H, 0.1, 1000);

  let theta = 0.3, phi = 0.35, radius = 22;
  let isDragging = false, prev = { x: 0, y: 0 };
  let autoRotate = true;

  const update = () => {
    camera.position.set(
      radius * Math.sin(theta) * Math.cos(phi),
      radius * Math.sin(phi),
      radius * Math.cos(theta) * Math.cos(phi)
    );
    camera.lookAt(0, 0, 0);
  };
  update();

  // Mouse
  const onDown  = e => { isDragging = true; autoRotate = false; prev = { x: e.clientX, y: e.clientY }; };
  const onMove  = e => {
    if (!isDragging) return;
    theta -= (e.clientX - prev.x) * 0.008;
    phi    = Math.max(-1.2, Math.min(1.2, phi + (e.clientY - prev.y) * 0.006));
    prev   = { x: e.clientX, y: e.clientY };
    update();
  };
  const onUp    = () => { isDragging = false; };
  const onWheel = e => { radius = Math.max(8, Math.min(55, radius + e.deltaY * 0.04)); update(); };

  // Touch
  let lastTouch = null;
  const onTouchStart = e => { lastTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY }; autoRotate = false; };
  const onTouchMove  = e => {
    if (!lastTouch) return;
    theta -= (e.touches[0].clientX - lastTouch.x) * 0.008;
    phi    = Math.max(-1.2, Math.min(1.2, phi + (e.touches[0].clientY - lastTouch.y) * 0.006));
    lastTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    update();
  };

  canvas.addEventListener("mousedown",  onDown);
  canvas.addEventListener("wheel",      onWheel, { passive: true });
  canvas.addEventListener("touchstart", onTouchStart);
  canvas.addEventListener("touchmove",  onTouchMove);
  window.addEventListener("mousemove",  onMove);
  window.addEventListener("mouseup",    onUp);

  const tick = () => {
    if (autoRotate) { theta += 0.003; update(); }
  };

  const resize = () => {
    camera.aspect = canvas.clientWidth / canvas.clientHeight;
    camera.updateProjectionMatrix();
  };
  window.addEventListener("resize", resize);

  const destroy = () => {
    canvas.removeEventListener("mousedown",  onDown);
    canvas.removeEventListener("wheel",      onWheel);
    canvas.removeEventListener("touchstart", onTouchStart);
    canvas.removeEventListener("touchmove",  onTouchMove);
    window.removeEventListener("mousemove",  onMove);
    window.removeEventListener("mouseup",    onUp);
    window.removeEventListener("resize",     resize);
  };

  return { camera, tick, resize, destroy };
}