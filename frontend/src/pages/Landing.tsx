import { ArrowRight, BookOpen, LockKeyhole, Search, ShieldCheck, Workflow } from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { PageMeta } from "../components/PageMeta";
import { useAuth } from "../context/useAuth";

export function Landing() {
  const { user, loading } = useAuth();
  if (loading) return <main className="public-loading"><div className="loading-line" /></main>;
  if (user) return <Navigate to="/workspace" replace />;
  return (
    <main className="public-page">
      <PageMeta title="Research workbench" description="Private, source-led research runs with explicit human review." />
      <header className="public-header">
        <Link to="/" className="brand"><span className="brand-mark"><Workflow size={19} /></span>handoff</Link>
        <Link to="/login" className="button button-secondary button-small">Sign in <ArrowRight size={15} /></Link>
      </header>
      <section className="public-hero">
        <div className="public-copy">
          <p className="eyebrow"><span className="eyebrow-dot" /> PRIVATE RESEARCH WORKSPACE</p>
          <h1>Answers that show<br /><em>where they came from.</em></h1>
          <p className="hero-description">Give a research brief. Handoff searches the web, collects readable sources, drafts a cited answer, and brings you in before anything is finalized.</p>
          <div className="hero-actions"><Link className="button button-primary" to="/login">Sign in to Handoff <ArrowRight size={17} /></Link><a className="text-action" href="#how-it-works">How it works <ArrowRight size={15} /></a></div>
          <div className="privacy-line"><LockKeyhole size={15} /><span>Runs stay private to your account</span></div>
        </div>
        <div className="hero-card" aria-label="Research report preview">
          <div className="report-topline"><span className="report-kicker">RESEARCH NOTE</span><span className="report-date">SOURCE LED</span></div>
          <div className="report-rule" />
          <div className="report-lines"><span /><span /><span className="short" /></div>
          <div className="report-source"><span className="source-number">01</span><div><strong>Retrieved source</strong><small>Original page · link preserved</small></div><Search size={16} /></div>
          <div className="report-source"><span className="source-number">02</span><div><strong>Evidence attached</strong><small>Excerpt available for review</small></div><BookOpen size={16} /></div>
          <div className="report-review"><ShieldCheck size={16} /><span>Draft held for your review</span></div>
        </div>
      </section>
      <section id="how-it-works" className="public-features">
        <article><span className="feature-index">01</span><div><h2>Search the question you asked</h2><p>Live discovery and readable page extraction replace canned examples. Source links stay with every run.</p></div></article>
        <article><span className="feature-index">02</span><div><h2>Keep tools inside your rules</h2><p>Connect MCP tools for your account. Calls that can change data wait for your approval.</p></div></article>
        <article><span className="feature-index">03</span><div><h2>Review before completion</h2><p>Inspect the evidence, read the draft, then decide whether it is ready to keep.</p></div></article>
      </section>
      <footer className="public-footer"><Link to="/login">Continue to your workspace <ArrowRight size={15} /></Link><span>Handoff · Private research with a clear audit trail</span></footer>
    </main>
  );
}
