import {Section} from './Section';

const STEPS = [
  {n: '1', title: 'Branch', text: 'Create a branch from the UI or from Git and change a schema there. Nothing reaches production yet.'},
  {n: '2', title: 'Pull request', text: 'Open a pull request to main and review the change like code.'},
  {n: '3', title: 'Merge', text: 'A GitHub Action checks the JSON and syncs the changed schemas from main to Cloud Storage.'},
  {n: '4', title: 'Live', text: 'The validator uses the new schema from the next event.'},
];

export function GitOps() {
  return (
    <Section
      id="gitops"
      tag="Git workflow"
      title="Schemas can live in version control."
      intro="Optional, and recommended once more than one person edits schemas. Without GitHub, schemas live in Cloud Storage and you manage them in the UI. With it, your schema repository is the source of truth, with history and review. Only main reaches production. Authentication to Google Cloud uses Workload Identity Federation, so no long-lived keys are stored in GitHub."
      dark
    >
      <ol className="grid gap-4 md:grid-cols-4">
        {STEPS.map((s) => (
          <li key={s.n} className="border border-white/15 p-6">
            <span className="text-3xl font-semibold text-brand">{s.n}</span>
            <h3 className="mt-3 text-lg font-semibold">{s.title}</h3>
            <p className="mt-2 text-slate-300">{s.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
