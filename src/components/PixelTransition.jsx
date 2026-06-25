import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import "./PixelTransition.css";

function PixelTransition({
  firstContent,
  secondContent,
  gridSize = 9,
  pixelColor = "rgba(12, 16, 14, 0.96)",
  animationStepDuration = 0.75,
  aspectRatio = "16 / 10",
  active = false,
  onComplete,
  className = "",
  style = {},
}) {
  const gridRef = useRef(null);
  const firstRef = useRef(null);
  const secondRef = useRef(null);
  const tweenRef = useRef(null);

  useEffect(() => {
    const gridEl = gridRef.current;
    if (!gridEl) return;

    gridEl.innerHTML = "";

    for (let row = 0; row < gridSize; row += 1) {
      for (let col = 0; col < gridSize; col += 1) {
        const pixel = document.createElement("span");
        pixel.className = "pixel-transition__pixel";
        pixel.style.backgroundColor = pixelColor;
        const size = 100 / gridSize;
        pixel.style.width = `${size}%`;
        pixel.style.height = `${size}%`;
        pixel.style.left = `${col * size}%`;
        pixel.style.top = `${row * size}%`;
        gridEl.appendChild(pixel);
      }
    }
  }, [gridSize, pixelColor]);

  useEffect(() => {
    const gridEl = gridRef.current;
    const firstEl = firstRef.current;
    const secondEl = secondRef.current;
    if (!gridEl || !firstEl || !secondEl) return undefined;

    const pixels = gridEl.querySelectorAll(".pixel-transition__pixel");
    if (!pixels.length) return undefined;

    tweenRef.current?.kill();
    gsap.killTweensOf([pixels, firstEl, secondEl]);

    if (!active) {
      gsap.set(firstEl, { autoAlpha: 1, display: "block" });
      gsap.set(secondEl, { autoAlpha: 0, display: "none" });
      gsap.set(pixels, { autoAlpha: 0, display: "none" });
      return undefined;
    }

    gsap.set(firstEl, { autoAlpha: 1, display: "block" });
    gsap.set(secondEl, { autoAlpha: 0, display: "block" });
    gsap.set(pixels, { autoAlpha: 0, display: "block", scale: 0.94, transformOrigin: "center" });

    const revealDuration = Math.max(0.42, animationStepDuration * 0.58);
    const staggerStep = revealDuration / pixels.length;
    const tl = gsap.timeline({
      onComplete: () => {
        gsap.set(firstEl, { autoAlpha: 0, display: "none" });
        gsap.set(secondEl, { autoAlpha: 1, display: "block" });
        gsap.set(pixels, { autoAlpha: 0, display: "none" });
        onComplete?.();
      },
    });

    tl.to(pixels, {
      autoAlpha: 1,
      scale: 1,
      duration: 0.001,
      stagger: { each: staggerStep, from: "random" },
    })
      .to(
        secondEl,
        {
          autoAlpha: 1,
          duration: Math.max(0.18, animationStepDuration * 0.22),
          ease: "power2.out",
        },
        revealDuration * 0.36
      )
      .to(
        firstEl,
        {
          autoAlpha: 0,
          duration: Math.max(0.18, animationStepDuration * 0.22),
          ease: "power2.out",
        },
        revealDuration * 0.36
      )
      .to(
        pixels,
        {
          autoAlpha: 0,
          duration: 0.001,
          stagger: { each: staggerStep, from: "random" },
        },
        revealDuration * 0.54
      );

    tweenRef.current = tl;
    return () => tl.kill();
  }, [active, animationStepDuration, onComplete]);

  return (
    <div className={`pixel-transition ${className}`.trim()} style={{ ...style, aspectRatio }}>
      <div className="pixel-transition__layer pixel-transition__layer--first" ref={firstRef}>
        {firstContent}
      </div>
      <div className="pixel-transition__layer pixel-transition__layer--second" ref={secondRef}>
        {secondContent}
      </div>
      <div className="pixel-transition__grid" ref={gridRef} aria-hidden="true" />
    </div>
  );
}

export default PixelTransition;
