import { Hero } from "@/components/sections/hero";
import { WakeWordDemo } from "@/components/sections/wake-word-demo";
import { Architecture } from "@/components/sections/architecture";
import { PlatformStory } from "@/components/sections/platform-story";
import { QuickStart } from "@/components/sections/quick-start";
import { Status } from "@/components/sections/status";
import { Footer } from "@/components/sections/footer";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col">
      <Hero />
      <WakeWordDemo />
      <Architecture />
      <PlatformStory />
      <QuickStart />
      <Status />
      <Footer />
    </main>
  );
}
