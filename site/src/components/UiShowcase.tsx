import {useEffect, useRef, useState} from 'react';
import {Section} from './Section';

const base = import.meta.env.BASE_URL;

const SHOTS = [
  {file: 'explorer', w: 1800, h: 930, name: 'Explorer', text: 'All schemas, their branch and their health in one view.', alt: 'Schema Explorer listing GA4 event schemas on the main branch'},
  {file: 'builder', w: 1800, h: 620, name: 'Builder', text: 'Add parameters from the library and see the schema JSON update live.', alt: 'Schema Builder showing the purchase schema fields next to the live JSON preview'},
  {file: 'params-repo', w: 1800, h: 930, name: 'Params Repo', text: 'A parameter library that starts with the GA4 recommended parameters.', alt: 'Parameters Repository listing 48 GA4 parameters'},
  {file: 'validation-report', w: 1340, h: 930, name: 'Validation Report', text: 'Which events fail, how often, and the raw failure logs.', alt: 'Validation Report chart of event failures per day with a raw failure log table'},
  {file: 'parameter-performance', w: 1340, h: 780, name: 'Parameter Performance', text: 'Rank parameters by error rate, with the top issue and a daily trend.', alt: 'Parameter Performance table ranking parameters by error rate'},
  {file: 'export', w: 1380, h: 930, name: 'Export', text: 'Hand a schema to developers as JSON or a PDF.', alt: 'Export view showing the purchase schema as JSON with a Download PDF button'},
];

export function UiShowcase() {
  const [active, setActive] = useState<number | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const d = dialogRef.current;
    if (!d) return;
    if (active !== null && !d.open) d.showModal();
    if (active === null && d.open) d.close();
  }, [active]);

  const close = () => {
    setActive(null);
    openerRef.current?.focus();
  };

  const shot = active !== null ? SHOTS[active] : null;

  return (
    <Section
      id="ui"
      tag="Schema manager"
      title="A UI your whole team can use."
      intro="Manage schemas without touching JSON, and see what breaks in production. Click a screenshot to enlarge it."
    >
      <ul className="grid items-start gap-6 md:grid-cols-2">
        {SHOTS.map((s, i) => (
          <li key={s.file} className="overflow-hidden border border-line bg-white">
            <button
              type="button"
              className="block w-full cursor-zoom-in border-b border-line"
              aria-label={`Enlarge ${s.name} screenshot`}
              onClick={(e) => {
                openerRef.current = e.currentTarget;
                setActive(i);
              }}
            >
              <img
                src={`${base}screenshots/${s.file}.webp`}
                alt={s.alt}
                width={s.w}
                height={s.h}
                loading="lazy"
                decoding="async"
                className="h-auto w-full"
              />
            </button>
            <div className="p-5">
              <h3 className="text-lg font-semibold">{s.name}</h3>
              <p className="mt-1 text-muted">{s.text}</p>
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-muted">All screenshots show generated sample data, not real client data.</p>

      <dialog
        ref={dialogRef}
        aria-label={shot ? `${shot.name} screenshot` : 'Screenshot'}
        onClose={() => setActive(null)}
        onClick={(e) => {
          if (e.target === e.currentTarget) close();
        }}
        className="m-auto max-h-[95vh] max-w-[95vw] bg-transparent p-0 backdrop:bg-black/80"
      >
        {shot && (
          <div className="relative">
            <img
              src={`${base}screenshots/${shot.file}.webp`}
              alt={shot.alt}
              width={shot.w}
              height={shot.h}
              className="max-h-[90vh] w-auto max-w-[95vw] bg-white object-contain"
            />
            <button
              type="button"
              onClick={close}
              aria-label="Close"
              className="absolute right-2 top-2 bg-ink px-3 py-1.5 text-sm font-bold text-white hover:bg-brand"
            >
              Close ✕
            </button>
          </div>
        )}
      </dialog>
    </Section>
  );
}
