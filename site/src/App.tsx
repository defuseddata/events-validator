import {CtaBand} from './components/CtaBand';
import {Deploy} from './components/Deploy';
import {Features} from './components/Features';
import {Footer} from './components/Footer';
import {GitOps} from './components/GitOps';
import {Limits} from './components/Limits';
import {Header} from './components/Header';
import {Hero} from './components/Hero';
import {HowItWorks} from './components/HowItWorks';
import {OpenSource} from './components/OpenSource';
import {Problem} from './components/Problem';
import {UiShowcase} from './components/UiShowcase';

export default function App() {
  return (
    <>
      <a href="#features" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-3">
        Skip to content
      </a>
      <Header />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Features />
        <UiShowcase />
        <GitOps />
        <Deploy />
        <Limits />
        <OpenSource />
        <CtaBand />
      </main>
      <Footer />
    </>
  );
}
