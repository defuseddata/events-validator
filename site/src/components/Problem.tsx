import {Section} from './Section';

const LEVELS = [
  {
    name: 'Manual or scripted tests',
    note: 'Low entry barrier, but hard to scale and slow to notice a regression.',
  },
  {
    name: 'Assertions on aggregated data',
    note: 'Fits dbt and Dataform workflows, but runs after the wrong data is already in your tables.',
  },
  {
    name: 'Event-level schema validation',
    note: 'Checked per event, down to the single parameter, before anyone builds a report on it. This is what Events Validator does.',
    hl: true,
  },
];

export function Problem() {
  return (
    <Section
      id="problem"
      tag="The problem"
      title="Tracking decays quietly."
      intro="A renamed parameter, a value sent as text instead of a number, a tag that stops firing after a release. People leave, projects move on, and a report is wrong for weeks before anyone notices. There are three places to catch it, and the later you do, the more data is already affected."
    >
      <ul className="grid gap-4 md:grid-cols-3">
        {LEVELS.map((l) => (
          <li
            key={l.name}
            className={`border p-6 ${l.hl ? 'border-brand bg-white' : 'border-line bg-white/60'}`}
          >
            <h3 className="text-lg font-semibold">{l.name}</h3>
            <p className="mt-2 text-muted">{l.note}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
