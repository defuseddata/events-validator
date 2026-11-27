import type {ReactNode} from 'react';

type Props = {
  id: string;
  tag: string;
  title: string;
  intro?: string;
  dark?: boolean;
  children: ReactNode;
};

export function Section({id, tag, title, intro, dark, children}: Props) {
  return (
    <section id={id} className={dark ? 'bg-ink text-white' : 'bg-paper text-ink-soft'}>
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <p className="dd-tag">{tag}</p>
        <h2 className="mt-4 max-w-3xl text-3xl font-semibold sm:text-4xl">{title}</h2>
        {intro && <p className={`mt-4 max-w-3xl text-lg leading-relaxed ${dark ? 'text-slate-300' : 'text-muted'}`}>{intro}</p>}
        <div className="mt-10">{children}</div>
      </div>
    </section>
  );
}
