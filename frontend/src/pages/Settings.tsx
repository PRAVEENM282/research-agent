import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, KeyRound, Search, Settings2 } from "lucide-react";
import { api } from "../api/client";
import { PageMeta } from "../components/PageMeta";

function ConfigValue({ ok }: { ok: boolean }) {
  return <span className={`config-indicator ${ok ? "config-ok" : "config-missing"}`}>{ok ? <CheckCircle2 size={15} /> : <CircleAlert size={15} />}{ok ? "Connected" : "Not configured"}</span>;
}

export function Settings() {
  const runtime = useQuery({ queryKey: ["runtime-settings"], queryFn: api.getSettings });
  return (
    <main id="main" className="page-wrap">
      <PageMeta title="Settings" description="Review the providers configured for this Handoff deployment." />
      <div className="page-heading"><p className="eyebrow">PREFERENCES</p><h1>Settings</h1><p>Provider credentials are managed by the server environment and never shown in the browser.</p></div>
      <section className="settings-section">
        <div className="settings-section-title"><span className="settings-icon"><Settings2 size={18} /></span><div><h2>Research and writing</h2><p>Runtime configuration for new runs</p></div></div>
        {runtime.isLoading ? <div className="loading-line" /> : runtime.isError ? <div className="inline-error">Could not load deployment settings.</div> : <div className="settings-list">
          <article className="settings-row"><span className="settings-row-icon"><KeyRound size={17} /></span><div className="settings-row-copy"><strong>Language model</strong><p>{runtime.data?.llm_provider} · {runtime.data?.llm_model}</p></div><ConfigValue ok={runtime.data?.llm_configured ?? false} /></article>
          <article className="settings-row"><span className="settings-row-icon"><Search size={17} /></span><div className="settings-row-copy"><strong>Web search</strong><p>{runtime.data?.search_provider} · live result discovery</p></div><ConfigValue ok={runtime.data?.search_configured ?? false} /></article>
        </div>}
      </section>
      <div className="settings-note"><CircleAlert size={17} /><p>To change a provider or add its API key, update <code>LLM_PROVIDER</code>, <code>LLM_MODEL</code>, and the matching key in the server environment, then restart the services.</p></div>
    </main>
  );
}
