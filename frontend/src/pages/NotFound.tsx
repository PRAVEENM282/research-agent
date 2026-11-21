import { Link } from "react-router-dom";
import { ArrowLeft, SearchX } from "lucide-react";
import { PageMeta } from "../components/PageMeta";

export function NotFound() {
  return <main id="main" className="page-wrap"><PageMeta title="Page not found" description="This page does not exist." /><section className="error-card"><SearchX size={26} /><p className="eyebrow">PAGE NOT FOUND</p><h1>This page isn’t here.</h1><p>Check the address or return to your research workspace.</p><div><Link className="button button-primary" to="/workspace">Open workspace</Link><Link className="button button-quiet" to="/tasks"><ArrowLeft size={15} />Research runs</Link></div></section></main>;
}
