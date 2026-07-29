import { Nav } from "@/components/nav";
import {
  Footer,
  Formats,
  Hero,
  Install,
  Pipeline,
  TwoPasses,
} from "@/components/sections";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <TwoPasses />
        <Formats />
        <Pipeline />
        <Install />
      </main>
      <Footer />
    </>
  );
}
