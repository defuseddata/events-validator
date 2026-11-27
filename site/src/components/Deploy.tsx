import {LINKS} from '../links';
import {Section} from './Section';

export function Deploy() {
  return (
    <Section
      id="deploy"
      tag="Deploy"
      title="Running in about 15 minutes."
      intro="You need a Google Cloud project with billing enabled, plus gcloud, Terraform and jq. The GitHub CLI is needed only if you enable GitOps."
    >
      <div className="grid gap-8 lg:grid-cols-2">
        <pre className="overflow-x-auto bg-ink p-5 text-sm leading-relaxed text-slate-200" tabIndex={0}>
          <code>{`git clone ${LINKS.repo}.git
cd events-validator
./install.sh`}</code>
        </pre>
        <div className="space-y-3 text-muted">
          <p>The wizard checks your project, uses your own gcloud login instead of JSON keys, optionally creates the schema repository on GitHub (GitOps), deploys the backend, optionally deploys the UI, and prints your endpoint. For the UI you create an OAuth client in the Google Cloud console when the wizard asks, to protect it with Identity-Aware Proxy.</p>
          <p>
            The setup wizard (<code className="bg-white px-1">install.sh</code>) supports macOS and Linux. On Windows, use the manual Terraform path described in the README.
          </p>
          <p>
            <a className="font-semibold text-brand-dark underline" href={LINKS.repo} rel="noopener">Read the full guide on GitHub</a>
          </p>
        </div>
      </div>
    </Section>
  );
}
