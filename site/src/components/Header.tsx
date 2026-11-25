import {useState} from 'react';
import {LINKS, NAV} from '../links';

export function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 bg-ink text-white">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <a href="#top" className="flex items-center gap-3" aria-label="Events Validator, home">
          <img src={LINKS.logo} alt="Defused Data" className="h-7 w-auto" width={248} height={28} />
        </a>
        <nav className="hidden items-center gap-8 md:flex" aria-label="Main">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="dd-nav-link">
              {n.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <a href={LINKS.repo} className="btn-primary hidden text-sm sm:inline-flex" rel="noopener">
            View on GitHub
          </a>
          <button
            type="button"
            className="p-2 text-slate-200 hover:text-white md:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? 'Close menu' : 'Open menu'}
            onClick={() => setOpen(!open)}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>
      {open && (
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-white/10 px-4 pb-6 pt-2 md:hidden">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} onClick={() => setOpen(false)} className="block py-3 text-slate-200">
              {n.label}
            </a>
          ))}
          <a href={LINKS.repo} className="btn-primary mt-2 w-full" rel="noopener">
            View on GitHub
          </a>
        </nav>
      )}
    </header>
  );
}
