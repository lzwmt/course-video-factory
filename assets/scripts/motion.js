/**
 * MotionEngine - Lightweight GSAP Animation & Particle DSL for HyperFrames
 */
(function (global) {
  if (typeof gsap !== "undefined") {
    gsap.config({ force3D: false, nullTargetWarn: false });
  }
  const MotionEngine = {
    /**
     * Enter element with fade-in and smooth upward translation
     */
    enter(target, opts = {}) {
      const { duration = 0.4, y = 20, scale = 1, opacity = 1, ease = "power2.out", delay = 0 } = opts;
      return gsap.fromTo(
        target,
        { opacity: 0, y: y, scale: scale * 0.95 },
        { opacity: opacity, y: 0, scale: scale, duration: duration, ease: ease, delay: delay }
      );
    },

    /**
     * Exit element
     */
    exit(target, opts = {}) {
      const { duration = 0.3, y = -15, ease = "power2.in" } = opts;
      return gsap.to(target, { opacity: 0, y: y, duration: duration, ease: ease });
    },

    /**
     * Highlight element / node with color glow
     */
    highlight(target, opts = {}) {
      const { color = "#3B82F6", duration = 0.4, scale = 1.05 } = opts;
      const tl = gsap.timeline();
      tl.to(target, {
        scale: scale,
        borderColor: color,
        boxShadow: `0 0 35px ${color}`,
        duration: duration,
        ease: "power2.out",
      }).to(target, {
        scale: 1,
        duration: duration * 0.8,
        ease: "power2.inOut",
      });
      return tl;
    },

    /**
     * Animate SVG path stroke draw
     */
    connect(pathTarget, opts = {}) {
      const { duration = 0.6, ease = "power2.out" } = opts;
      const el = typeof pathTarget === "string" ? document.querySelector(pathTarget) : pathTarget;
      if (!el) return gsap.timeline();
      const len = el.getTotalLength ? el.getTotalLength() : 300;
      gsap.set(el, { strokeDasharray: len, strokeDashoffset: len, opacity: 1 });
      return gsap.to(el, { strokeDashoffset: 0, duration: duration, ease: ease });
    },

    /**
     * Request Particle Animator (Moves along coordinates x1,y1 -> x2,y2)
     */
    packet(particleTarget, fromCoords, toCoords, opts = {}) {
      const { duration = 0.7, color = "#3B82F6", ease = "power1.inOut" } = opts;
      const tl = gsap.timeline();
      tl.fromTo(
        particleTarget,
        {
          cx: fromCoords.x,
          cy: fromCoords.y,
          opacity: 0,
          scale: 0.5,
          fill: color,
        },
        {
          opacity: 1,
          scale: 1,
          duration: 0.1,
          ease: "power1.out",
        }
      )
        .to(particleTarget, {
          cx: toCoords.x,
          cy: toCoords.y,
          duration: duration,
          ease: ease,
        })
        .to(particleTarget, {
          opacity: 0,
          scale: 0.5,
          duration: 0.15,
        });
      return tl;
    },

    /**
     * Numeric Counter Transition
     */
    counter(target, fromVal, toVal, opts = {}) {
      const { duration = 0.8, suffix = "", ease = "power2.out" } = opts;
      const obj = { val: fromVal };
      const el = typeof target === "string" ? document.querySelector(target) : target;
      return gsap.to(obj, {
        val: toVal,
        duration: duration,
        ease: ease,
        onUpdate: () => {
          if (el) el.innerText = Math.round(obj.val).toLocaleString() + suffix;
        },
      });
    },

    /**
     * Metric Gauge / Bar Animation
     */
    metricBar(target, targetPercent, opts = {}) {
      const { duration = 0.6, ease = "back.out(1.4)" } = opts;
      return gsap.to(target, {
        width: `${targetPercent}%`,
        duration: duration,
        ease: ease,
      });
    },

    /**
     * Pulse Warning / Focus
     */
    pulse(target, opts = {}) {
      const { duration = 0.35, scale = 1.08, repeat = 2 } = opts;
      return gsap.to(target, {
        scale: scale,
        duration: duration,
        yoyo: true,
        repeat: repeat,
        ease: "sine.inOut",
      });
    },

    /**
     * Shake Shake Warning Error
     */
    shake(target, opts = {}) {
      const { duration = 0.4, x = 12 } = opts;
      const tl = gsap.timeline();
      tl.to(target, { x: -x, duration: duration * 0.2, ease: "power1.inOut" })
        .to(target, { x: x, duration: duration * 0.2, ease: "power1.inOut" })
        .to(target, { x: -x * 0.6, duration: duration * 0.2, ease: "power1.inOut" })
        .to(target, { x: x * 0.6, duration: duration * 0.2, ease: "power1.inOut" })
        .to(target, { x: 0, duration: duration * 0.2, ease: "power1.out" });
      return tl;
    },

    /**
     * Camera Viewport Zoom/Focus
     */
    zoom(container, opts = {}) {
      const { scale = 1.12, x = 0, y = 0, duration = 0.6, ease = "power2.inOut" } = opts;
      return gsap.to(container, {
        scale: scale,
        x: x,
        y: y,
        transformOrigin: "50% 50%",
        duration: duration,
        ease: ease,
        force3D: false,
      });
    },

    focus(target, opts = {}) {
      const { others = ".node-box", duration = 0.4 } = opts;
      const tl = gsap.timeline();
      tl.to(others, { opacity: 0.35, duration: duration, ease: "none" });
      tl.to(target, { opacity: 1, duration: duration, ease: "none" }, 0);
      return tl;
    },
  };

  global.motion = MotionEngine;
})(window);
