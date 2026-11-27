import {Section} from './Section';

const LIMITS = [
  {
    title: 'Google Cloud only',
    text: 'The backend runs on Cloud Functions, Cloud Storage, API Gateway and BigQuery. There is no other cloud target.',
  },
  {
    title: 'You send the events',
    text: 'It validates the events you post to it, not all of your traffic. Sample or select events in your tracking setup, for example in server-side GTM.',
  },
  {
    title: 'GA4 schemas included, build your own',
    text: 'GA4 recommended events come ready-made, but you can easily build your own schemas. Any JSON event format works with the configurable event name field and data path.',
  },
  {
    title: 'Only listed fields are checked',
    text: 'Parameters that are not in the schema are ignored. There is no strict mode that rejects unknown parameters.',
  },
  {
    title: 'No schema, no verdict',
    text: 'An event name without a schema file gets a 404 response and nothing is written to BigQuery.',
  },
  {
    title: 'Regex matches partially',
    text: 'A pattern like \\d+ also accepts "abc123xyz", because it only has to match somewhere in the value. To match the whole value, write ^\\d+$.',
  },
  {
    title: 'UI and JSON differ a little',
    text: 'The no-code UI covers strings, numbers, booleans, arrays and conditional rules. Object type and exact length are set by editing the schema JSON.',
  },
];

export function Limits() {
  return (
    <Section
      id="limits"
      tag="Good to know"
      title="What it does not do."
      intro="Better to know before you deploy than after."
    >
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {LIMITS.map((l) => (
          <li key={l.title} className="border border-line bg-white p-6">
            <h3 className="text-lg font-semibold">{l.title}</h3>
            <p className="mt-2 text-muted">{l.text}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
