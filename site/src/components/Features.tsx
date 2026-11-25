import {Section} from './Section';

const FEATURES = [
  {
    title: 'Checks that match real tracking bugs',
    text: 'Type, exact value, contains (case-sensitive or not), regex, optional fields, and nested arrays. Missing required parameters are caught too.',
  },
  {
    title: 'Conditional rules',
    text: 'Require a field only when another one is present, or only when it has a given value. For example item_id only if item_list_name exists.',
  },
  {
    title: 'Ready-made GA4 schemas',
    text: '35 recommended GA4 event schemas and a master parameter repository come pre-loaded, so you start from a working baseline instead of a blank page. Your own events work the same way.',
  },
  {
    title: 'Failures you can query',
    text: 'Every failed field is a BigQuery row with event, field, error type, expected and actual value. Optional flags log valid fields and attach the payload.',
  },
  {
    title: 'Change a parameter once',
    text: 'Edit a parameter in the Params Repo, review a diff for every schema that uses it, then apply it to the schemas you select.',
  },
  {
    title: 'Drift health checks',
    text: 'The Explorer flags schemas that no longer match your parameter repository and syncs them with one click.',
  },
  {
    title: 'Schemas in Git (optional)',
    text: 'Turn on GitOps for branches, pull requests and review. Merging to main syncs to Cloud Storage with a GitHub Action, keyless. Or skip it and manage schemas in the UI.',
  },
  {
    title: 'Secured by default',
    text: 'The event endpoint sits behind API Gateway and needs an API key. The schema manager is behind Identity-Aware Proxy, so only users you authorize can open it.',
  },
  {
    title: 'Cheap to run',
    text: 'About $0.50 per day for 50,000 processed events in our tests of the validator backend. Sample incoming data to keep costs down.',
  },
];

export function Features() {
  return (
    <Section
      id="features"
      tag="Features"
      title="Everything you need to trust your events."
      intro="Rules that fit how tracking breaks, logs that answer where and how often, and a safe way to change schemas."
    >
      <ul className="grid gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f) => (
          <li key={f.title} className="bg-white p-6">
            <h3 className="text-lg font-semibold">{f.title}</h3>
            <p className="mt-2 text-muted">{f.text}</p>
          </li>
        ))}
      </ul>
      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-xl font-semibold">A schema is a small JSON file</h3>
          <p className="mt-2 text-muted">
            Build it in the UI or edit it by hand. Anything that is not marked optional is required, and one file
            covers one event name. Nested objects and exact length checks are available when you edit the JSON
            directly.
          </p>
        </div>
        <pre className="overflow-x-auto bg-ink p-5 text-sm leading-relaxed text-slate-200" tabIndex={0}>
          <code>{`{
  "event_name":    { "type": "string", "value": "page_view" },
  "page_title":    { "type": "string" },
  "page_location": { "type": "string",
                     "value_contains": "/checkout",
                     "value_contains_case_sensitive": false },
  "user_id":       { "type": "string", "regex": "^user_\\\\d+$" },
  "promo_code":    { "type": "string", "optional": true }
}`}</code>
        </pre>
      </div>
    </Section>
  );
}
