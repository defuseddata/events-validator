import {LINKS} from '../links';

export function CtaBand() {
  return (
    <section className="bg-brand text-white">
      <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-4 py-14 sm:px-6 md:flex-row md:items-center lg:px-8">
        <div>
          <h2 className="text-3xl font-semibold">Want it running in your project?</h2>
          <p className="mt-2 text-white">Deploy it yourself, or talk to the people who built it.</p>
        </div>
        <a href={LINKS.contact} className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 font-bold text-brand hover:bg-paper" rel="noopener">
          Let&apos;s talk about deploying it
        </a>
      </div>
    </section>
  );
}
