import {LINKS} from '../links';
import {Section} from './Section';

export function OpenSource() {
  return (
    <Section
      id="open-source"
      tag="Open source"
      title="Free to use, fork and improve."
      intro="Events Validator is licensed under GPL-3.0 and built in the open by Defused Data. Contributions are welcome."
      dark
    >
      <div className="flex flex-col gap-3 sm:flex-row">
        <a href={LINKS.repo} className="btn-primary" rel="noopener">Star or fork on GitHub</a>
        <a href={LINKS.issues} className="btn-ghost" rel="noopener">Open an issue</a>
        <a href={LINKS.roadmap} className="btn-ghost" rel="noopener">Public roadmap</a>
      </div>
      <p className="mt-6 text-slate-300">
        Want to help? Start with an issue or a pull request on GitHub.
      </p>
    </Section>
  );
}
