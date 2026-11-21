import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, KeyRound, Workflow } from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api/client";
import { PageMeta } from "../components/PageMeta";
import { useAuth } from "../context/useAuth";

export function Login() {
  const { user, loading } = useAuth();
  const config = useQuery({ queryKey: ["auth-config"], queryFn: api.getAuthConfig, staleTime: 30_000 });
  if (loading) return <main className="public-loading"><div className="loading-line" /></main>;
  if (user) return <Navigate to="/workspace" replace />;
  const callbackError = new URLSearchParams(window.location.search).get("error");
  const callbackMessage = callbackError === "signin_expired"
    ? "This sign-in attempt expired. Start again."
    : callbackError === "account_not_allowed"
      ? "Your identity provider did not return a verified email for this account."
      : callbackError
        ? "Handoff could not validate the sign-in response. Try again; if it repeats, check the OAuth client secret and exact callback URL."
        : null;
  return (
    <main className="login-page">
      <PageMeta title="Sign in" description="Sign in to your private Handoff workspace." />
      <Link to="/" className="brand"><span className="brand-mark"><Workflow size={19} /></span>handoff</Link>
      <section className="login-card">
        <div className="login-icon"><KeyRound size={20} /></div>
        <p className="eyebrow">YOUR PRIVATE WORKSPACE</p>
        <h1>Sign in to continue.</h1>
        <p className="login-description">Use your organization’s identity provider to open your research runs and connected tools.</p>
        {callbackMessage && <div className="inline-error" role="alert">{callbackMessage}</div>}
        {config.data?.oidc_available ? (
          <a className="button button-primary login-button" href="/api/v1/auth/login">Continue with your identity provider <ArrowRight size={16} /></a>
        ) : (
          <div className="setup-notice"><strong>Sign-in is not configured yet.</strong><span>Set the OIDC issuer, client credentials, callback URL, and sign-in access mode in the server environment.</span></div>
        )}
        {config.isError && <div className="inline-error" role="alert">The sign-in service is not reachable. Refresh this page when the API is available.</div>}
        <Link to="/" className="login-back"><ArrowLeft size={14} />Back to Handoff</Link>
      </section>
      <p className="login-footnote">Your runs are visible only to the account that created them.</p>
    </main>
  );
}
