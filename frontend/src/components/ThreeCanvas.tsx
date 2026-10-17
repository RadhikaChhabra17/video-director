import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

interface ThreeCanvasProps {
  className?: string;
  focalIndex?: number;
}

const FOCAL_COLORS = [0x00f0ff, 0xa855f7, 0xf43f5e, 0xf59e0b];

export const ThreeCanvas: React.FC<ThreeCanvasProps> = ({ className = '', focalIndex = 0 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const barrelLightRef = useRef<THREE.PointLight | null>(null);
  const dustMatRef = useRef<THREE.PointsMaterial | null>(null);
  const reelFramesRef = useRef<THREE.Group[]>([]);

  // Update light & glow colors dynamically when focalIndex changes
  useEffect(() => {
    const targetColor = FOCAL_COLORS[focalIndex] ?? 0x00f0ff;
    if (barrelLightRef.current) {
      barrelLightRef.current.color.setHex(targetColor);
    }
    if (dustMatRef.current) {
      dustMatRef.current.color.setHex(targetColor);
    }
    reelFramesRef.current.forEach((frame) => {
      const edgeGlow = frame.userData?.edgeGlow;
      if (edgeGlow && edgeGlow.material) {
        (edgeGlow.material as THREE.MeshBasicMaterial).color.setHex(targetColor);
      }
    });
  }, [focalIndex]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let animationFrameId: number;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030406, 0.05);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    const baseCamPos = { x: 0, y: 0.25, z: 13.2 };
    camera.position.set(baseCamPos.x, baseCamPos.y, baseCamPos.z);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Cinematic Film Reel
    const reelGroup = new THREE.Group();
    scene.add(reelGroup);
    const reelFrames: THREE.Group[] = [];
    const imageUrls = [
      'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=85',
      'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=900&q=85',
    ];
    const frameCount = imageUrls.length;
    const frameWidth = 2.42;
    const frameHeight = 1.55;
    const radius = 5.2;

    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin('anonymous');

    imageUrls.forEach((url, i) => {
      const angle = (i / frameCount) * Math.PI * 1.22 - Math.PI * 0.61;
      const frame = new THREE.Group();
      frame.position.set(
        Math.sin(angle) * radius,
        Math.sin(angle * 1.7) * 0.25,
        Math.cos(angle) * radius - radius + 0.15
      );
      frame.rotation.y = angle * 0.68;
      frame.rotation.z = Math.sin(angle) * -0.08;

      const backing = new THREE.Mesh(
        new THREE.PlaneGeometry(frameWidth + 0.18, frameHeight + 0.48),
        new THREE.MeshStandardMaterial({
          color: 0x08090b,
          metalness: 0.55,
          roughness: 0.32,
          side: THREE.DoubleSide,
        })
      );
      backing.position.z = -0.025;
      frame.add(backing);

      const imageMat = new THREE.MeshBasicMaterial({
        color: 0x9aa0a3,
        transparent: true,
        opacity: 0.84,
        side: THREE.DoubleSide,
      });
      const photo = new THREE.Mesh(new THREE.PlaneGeometry(frameWidth, frameHeight), imageMat);
      photo.position.z = 0.012;
      frame.add(photo);

      loader.load(url, (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        photo.material.map = texture;
        photo.material.color.set(0xffffff);
        photo.material.needsUpdate = true;
      });

      // Film perforations on both edges
      const holeMat = new THREE.MeshBasicMaterial({ color: 0x24282a, side: THREE.DoubleSide });
      for (let h = 0; h < 8; h++) {
        const x = -frameWidth / 2 + 0.15 + h * ((frameWidth - 0.3) / 7);
        [-1, 1].forEach((edge) => {
          const hole = new THREE.Mesh(new THREE.PlaneGeometry(0.105, 0.075), holeMat);
          hole.position.set(x, edge * (frameHeight / 2 + 0.16), 0.02);
          frame.add(hole);
        });
      }

      const edgeGlow = new THREE.Mesh(
        new THREE.PlaneGeometry(frameWidth + 0.22, frameHeight + 0.52),
        new THREE.MeshBasicMaterial({
          color: 0x00f0ff,
          transparent: true,
          opacity: 0,
          side: THREE.DoubleSide,
          wireframe: true,
        })
      );
      edgeGlow.position.z = 0.035;
      frame.add(edgeGlow);

      frame.userData = { photo, edgeGlow, angle, index: i };
      reelGroup.add(frame);
      reelFrames.push(frame);
    });
    reelFramesRef.current = reelFrames;

    // Lights
    const ambLight = new THREE.AmbientLight(0xffffff, 1.05);
    scene.add(ambLight);

    const initialColor = FOCAL_COLORS[focalIndex] ?? 0x00f0ff;
    const barrelLight = new THREE.PointLight(initialColor, 3.2, 24);
    barrelLight.position.set(0, 2, 4);
    scene.add(barrelLight);
    barrelLightRef.current = barrelLight;

    const warmLight = new THREE.PointLight(0xffb36b, 2.1, 18);
    warmLight.position.set(4, -2, 1);
    scene.add(warmLight);

    // Subtle background bokeh points
    const dustGeometry = new THREE.BufferGeometry();
    const dustPositions: number[] = [];
    for (let i = 0; i < 180; i++) {
      dustPositions.push(
        (Math.random() - 0.5) * 28,
        (Math.random() - 0.5) * 16,
        -2 - Math.random() * 15
      );
    }
    dustGeometry.setAttribute('position', new THREE.Float32BufferAttribute(dustPositions, 3));
    const dustMat = new THREE.PointsMaterial({ color: initialColor, size: 0.035, transparent: true, opacity: 0.35 });
    dustMatRef.current = dustMat;
    const dust = new THREE.Points(dustGeometry, dustMat);
    scene.add(dust);

    // Mouse Tracking parallax
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      mouseX = (x / rect.width) * 0.8;
      mouseY = (y / rect.height) * 0.5;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };
    window.addEventListener('resize', handleResize);

    const clock = new THREE.Clock();
    const lookAtTarget = new THREE.Vector3(0, 0, 0);

    const renderLoop = () => {
      animationFrameId = requestAnimationFrame(renderLoop);
      const elapsed = clock.getElapsedTime();

      // Continuous film transport
      reelGroup.rotation.y = Math.sin(elapsed * 0.22) * 0.12 + elapsed * 0.105;
      reelGroup.rotation.x = Math.sin(elapsed * 0.32) * 0.045;
      reelGroup.position.y = Math.sin(elapsed * 0.55) * 0.12;

      reelFrames.forEach((frame, i) => {
        const wave = Math.sin(elapsed * 1.15 - i * 0.72);
        const reveal = Math.max(0, Math.cos(frame.userData.angle + elapsed * 0.105));
        frame.userData.photo.material.opacity = 0.42 + reveal * 0.58;
        frame.userData.edgeGlow.material.opacity = Math.pow(reveal, 5) * 0.85;
        frame.scale.setScalar(0.92 + reveal * 0.13 + wave * 0.012);
      });

      dust.rotation.y = elapsed * 0.012;

      // Mouse Parallax Lerp
      camera.position.x += (baseCamPos.x + mouseX - camera.position.x) * 0.05;
      camera.position.y += (baseCamPos.y - mouseY - camera.position.y) * 0.05;
      camera.lookAt(lookAtTarget);

      renderer.render(scene, camera);
    };

    renderLoop();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (container && renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      dustGeometry.dispose();
      renderer.dispose();
      barrelLightRef.current = null;
      dustMatRef.current = null;
      reelFramesRef.current = [];
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`pointer-events-none absolute inset-0 overflow-hidden z-0 opacity-80 transition-opacity duration-1000 ${className}`}
    />
  );
};

