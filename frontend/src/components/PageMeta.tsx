import { useEffect } from "react";

export function PageMeta({ title, description }: { title: string; description: string }) {
  useEffect(() => {
    document.title = `${title} — Handoff`;
    const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (meta) meta.content = description;
    const ogTitle = document.querySelector<HTMLMetaElement>('meta[property="og:title"]');
    if (ogTitle) ogTitle.content = `${title} — Handoff`;
  }, [title, description]);
  return null;
}
