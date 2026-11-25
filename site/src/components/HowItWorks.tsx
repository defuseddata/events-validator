import type {ReactNode} from 'react';
import {Section} from './Section';

function Box({title, sub, accent}: {title: string; sub?: string; accent?: boolean}) {
  return (
    <div className={`border px-4 py-3 text-center ${accent ? 'border-brand bg-brand/10' : 'border-white/20 bg-white/5'}`}>
      <div className="font-semibold">{title}</div>
      {sub && <div className="text-sm text-slate-400">{sub}</div>}
    </div>
  );
}

const Arrow = () => (
  <div className="flex items-center justify-center text-brand" aria-hidden="true">
    <span className="hidden text-2xl md:inline">→</span>
    <span className="text-2xl md:hidden">↓</span>
  </div>
);

function ExampleStep({n, title, note, badge, children}: {n: string; title: string; note?: string; badge?: string; children: ReactNode}) {
  return (
    <div className="border border-white/15 bg-black/30 p-4">
      <div className="flex items-center gap-3">
        <span className="flex h-6 w-6 flex-none items-center justify-center bg-brand text-xs font-bold text-white">{n}</span>
        <h4 className="font-semibold text-white">{title}</h4>
        {badge && <span className="ml-auto bg-brand px-2 py-0.5 text-xs font-bold text-white">{badge}</span>}
      </div>
      <div className="mt-3 overflow-x-auto whitespace-pre-wrap break-words font-mono text-sm leading-relaxed text-slate-200" tabIndex={0}>
        {children}
      </div>
      {note && <p className="mt-2 text-sm text-slate-400">{note}</p>}
    </div>
  );
}

export function HowItWorks() {
  return (
    <Section
      id="how-it-works"
      tag="How it works"
      title="Send an event, get a verdict."
      intro="The validator is a single Cloud Function behind API Gateway. It loads the schema named after the event, checks the payload and answers right away. Failures are written to BigQuery, so you can see what breaks, where and how often."
      dark
    >
      <div className="grid items-center gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        <Box title="Event source" sub="Any HTTP client, e.g. server-side GTM" />
        <Arrow />
        <Box title="API Gateway" sub="API key" />
        <Arrow />
        <Box title="Validator function" sub="Cloud Functions, Node.js" accent />
        <Arrow />
        <Box title="BigQuery" sub="one row per failed field" />
      </div>
      <div className="mt-3 grid items-center gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        <div className="hidden md:block" />
        <div className="hidden md:block" />
        <div className="hidden md:block" />
        <div className="hidden md:block" />
        <div className="text-center text-sm text-slate-400 md:col-span-1">
          <span aria-hidden="true" className="text-brand">↑ </span>reads schemas
        </div>
        <div className="hidden md:block" />
        <div className="hidden md:block" />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        <Box title="Schema manager UI" sub="Streamlit on Cloud Run, behind IAP" />
        <Arrow />
        <Box title="Schemas" sub="JSON in Cloud Storage, optionally synced from Git" accent />
        <div className="hidden md:col-span-4 md:block" />
      </div>
      <div className="mt-10 grid gap-8 lg:grid-cols-2">
        <div className="min-w-0 space-y-3 text-slate-300">
          <h3 className="text-xl font-semibold text-white">What you get back</h3>
          <p>
            Any POST with a JSON body can be validated. A common source is a server-side Google Tag Manager
            container with a JSON HTTP request tag, but any backend, SDK or tool that can send JSON works. Send a sample of your traffic, or only the
            events you care about, to keep costs down.
          </p>
          <p>
            The response says what happened: <code className="bg-white/10 px-1">200</code> for a valid event,{' '}
            <code className="bg-white/10 px-1">400</code> when validation failed, and{' '}
            <code className="bg-white/10 px-1">404</code> when no schema exists for that event name. The event name
            field and the place of the event data in the body are configurable.
          </p>
          <p>
            A failed field becomes one BigQuery row with the event name, field path, error type (for example type,
            value, regex or missing), expected and actual value. Logging valid fields and attaching the full payload
            are switches, so you choose how much to store.
          </p>
        </div>
        <div className="min-w-0 space-y-3" aria-label="Example: an invalid event">
          <ExampleStep n="1" title="You send a purchase event" note="The GA4 purchase schema says value must be a number.">
            <code className="block">
              <span className="text-slate-400">POST /eventsValidator?key=…</span>
              {'\n'}
              {`{ "data": {
    "event_name": "purchase",
    "currency": "EUR",
    "value": `}
              <span className="text-[#ff7a8a]">"49.99"</span>
              {`,
    "items": [{ "item_id": "SKU_123" }]
} }`}
            </code>
          </ExampleStep>
          <ExampleStep n="2" title="You get a verdict" badge="400">
            <code className="block">{`{
  "status": "validation_failed",
  "message": "Validation errors occurred",
  "errorsLogged": 1
}`}</code>
          </ExampleStep>
          <ExampleStep n="3" title="The failure lands in BigQuery">
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
              {[
                ['event_name', 'purchase'],
                ['field', 'value'],
                ['error_type', 'type'],
                ['expected', 'number'],
                ['actual', 'string'],
              ].map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-slate-400">{k}</dt>
                  <dd className="font-mono text-slate-100">{v}</dd>
                </div>
              ))}
            </dl>
          </ExampleStep>
        </div>
      </div>
    </Section>
  );
}
