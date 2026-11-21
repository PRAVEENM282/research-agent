import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";

export class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Page rendering failed", error.name, info.componentStack?.slice(0, 500));
  }

  render() {
    if (this.state.hasError) {
      return <main className="page-wrap"><div className="error-card"><h1>This page could not be displayed</h1><p>Reload the page or return to your research runs.</p><Link className="button button-primary" to="/tasks">Open research runs</Link></div></main>;
    }
    return this.props.children;
  }
}
