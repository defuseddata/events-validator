const base = import.meta.env.BASE_URL;

export const LINKS = {
  repo: 'https://github.com/defuseddata/events-validator',
  issues: 'https://github.com/defuseddata/events-validator/issues',
  roadmap: 'https://github.com/orgs/defuseddata/projects/1',
  license: 'https://github.com/defuseddata/events-validator/blob/main/LICENSE',
  contact: 'https://www.defuseddata.com/contact',
  company: 'https://www.defuseddata.com',
  logo: `${base}defusedata-logotype.svg`,
};

export const NAV = [
  {label: 'Features', href: '#features'},
  {label: 'How it works', href: '#how-it-works'},
  {label: 'Deploy', href: '#deploy'},
  {label: 'Limits', href: '#limits'},
  {label: 'Open source', href: '#open-source'},
];
