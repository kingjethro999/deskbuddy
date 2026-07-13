"use client";

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import { Canvas } from "@react-three/fiber";
import { MeshDistortMaterial, Icosahedron } from "@react-three/drei";
import { Code2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TerminalBlock } from "@/components/shared/terminal-block";
import { useReducedMotionSafe } from "@/hooks/use-reduced-motion-safe";

function ListeningBlob() {
  return (
    <Canvas camera={{ position: [0, 0, 3.2] }} dpr={[1, 1.5]} frameloop="always">
      <ambientLight intensity={0.6} />
      <pointLight position={[2, 2, 2]} intensity={1.2} color="#4AB3D4" />
      <pointLight position={[-2, -1, 1]} intensity={0.8} color="#E8521A" />
      <Icosahedron args={[1.1, 12]}>
        <MeshDistortMaterial
          color="#1B5C52"
          emissive="#4AB3D4"
          emissiveIntensity={0.25}
          roughness={0.35}
          distort={0.38}
          speed={1.6}
        />
      </Icosahedron>
    </Canvas>
  );
}

function StaticOrb() {
  return (
    <div
      className="h-full w-full rounded-full"
      style={{
        background:
          "radial-gradient(circle at 35% 30%, var(--color-accent-dim), var(--color-bg) 70%)",
      }}
      aria-hidden
    />
  );
}

export function Hero() {
  const reduced = useReducedMotionSafe();
  const canvasWrap = useRef<HTMLDivElement>(null);
  const inView = useInView(canvasWrap, { amount: 0.3 });

  return (
    <section className="relative mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center gap-12 px-6 py-24 lg:flex-row lg:gap-16">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        className="flex-1 text-center lg:text-left"
      >
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.25em] text-[var(--color-accent)]">
          Voice-powered desktop companion
        </p>
        <h1 className="text-5xl font-semibold leading-[1.05] sm:text-6xl lg:text-7xl">
          Alexa, but for your PC.
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-[var(--color-text-secondary)] lg:mx-0">
          Install it from the terminal. Say the wake word. A styled GUI takes over and runs your computer hands-off, opening apps, typing, and reading the screen while you watch.
        </p>

        <div className="mt-8">
          <TerminalBlock
            label="install"
            code={'curl -fsSL https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.sh | bash'}
          />
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
          <Button
            size="lg"
            onClick={() =>
              document.getElementById("quick-start")?.scrollIntoView({ behavior: "smooth" })
            }
          >
            Install now
          </Button>
          <Button
            size="lg"
            variant="outline"
            asChild
          >
            <a href="https://github.com/kingjethro999/deskbuddy" target="_blank" rel="noreferrer">
              <Code2 className="h-4 w-4" /> View on GitHub
            </a>
          </Button>
        </div>
      </motion.div>

      <motion.div
        ref={canvasWrap}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.9, ease: "easeOut" }}
        className="relative h-64 w-64 sm:h-80 sm:w-80 lg:h-96 lg:w-96"
        aria-label="Animated listening orb representing DeskBuddy waiting for the wake word"
      >
        {reduced || !inView ? (
          <StaticOrb />
        ) : (
          <ListeningBlob />
        )}
      </motion.div>
    </section>
  );
}
