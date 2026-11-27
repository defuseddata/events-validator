import {LINKS} from '../links';

export function Footer() {
  return (
    <footer className="bg-ink text-sm text-slate-300">
      <div className="mx-auto max-w-7xl space-y-8 px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <img src={LINKS.logo} alt="Defused Data" className="h-7 w-auto" width={248} height={28} loading="lazy" />
            <p className="mt-4 max-w-sm text-slate-400">Events Validator is built and maintained by Defused Data.</p>
          </div>
          <ul className="space-y-2">
            <li><a className="hover:text-white" href={LINKS.repo} rel="noopener">GitHub</a></li>
            <li><a className="hover:text-white" href={LINKS.license} rel="noopener">GPL-3.0 licence</a></li>
            <li><a className="hover:text-white" href={LINKS.company} rel="noopener">defuseddata.com</a></li>
            <li><a className="hover:text-white" href={LINKS.contact} rel="noopener">Contact</a></li>
          </ul>
        </div>
        <div className="space-y-2 border-t border-white/10 pt-6 text-xs text-slate-400">
          <p>
            The Defused Data name and logo are trademarks of Defused Data and are not licensed under the GPL. The
            software licence covers the code only.
          </p>
          <p>
            BigQuery, Google Cloud, Google Analytics and Google Tag Manager are trademarks of Google LLC. This project
            is not affiliated with or endorsed by Google. Other product names are trademarks of their respective owners.
          </p>
          <p>
            This site sets no cookies and uses no analytics. It is hosted on GitHub Pages, which may log visitor IP
            addresses as part of serving the page.
          </p>
          <p>© {new Date().getFullYear()} Defused Data</p>
        </div>
      </div>
    </footer>
  );
}
