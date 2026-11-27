import {LINKS} from '../links';

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden bg-ink text-white">
      <div className="pointer-events-none absolute left-1/2 top-1/3 -z-0 h-[350px] w-[700px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand/10 blur-3xl" />
      <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-14 sm:px-6 lg:px-8 lg:pb-28 lg:pt-20">
        <div className="mx-auto max-w-4xl text-center">
          <p className="dd-tag justify-center">Open source · GPL-3.0</p>
          <h1 className="mt-6 text-4xl font-semibold leading-tight sm:text-5xl lg:text-6xl">
            Catch broken tracking events <span className="text-brand">before they break your reports.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-3xl text-lg leading-relaxed text-slate-300 sm:text-xl">
            Send your tracking events to an endpoint in your own Google Cloud project. Each event is checked
            against your schema and gets a pass or fail response straight away. Every failure is logged to BigQuery
            with the field, the expected value and the actual one.
          </p>
          <ul className="mx-auto mt-6 flex max-w-3xl flex-wrap justify-center gap-2">
            <li className="dd-chip">Runs in your own project</li>
            <li className="dd-chip">Ready-made GA4 recommended event schemas</li>
            <li className="dd-chip">Free, GPL-3.0</li>
          </ul>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a href={LINKS.repo} className="btn-primary w-full sm:w-auto" rel="noopener">
              View on GitHub
            </a>
            <a href={LINKS.contact} className="btn-ghost w-full sm:w-auto" rel="noopener">
              Let&apos;s talk about deploying it
            </a>
          </div>
          <div className="mx-auto mt-12 max-w-xl border-t border-white/15 pt-6">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Deployed at</p>
            <p className="mt-2 text-xl font-semibold text-white sm:text-2xl">
              Going <span className="px-2 text-brand" aria-hidden="true">·</span> Fenris Creations
              <span className="font-normal text-slate-300"> (CCP Games)</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
