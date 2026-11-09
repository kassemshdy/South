import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Link2 } from "lucide-react";

import { useT, type TranslationKey } from "@/i18n";
import { siteSettingsApi } from "@/services/api/endpoints";
import { queryKeys } from "@/services/api/queryKeys";
import type { JobLink, JobLinkAudience } from "@/types/api";
import { cn } from "@/utils/cn";

/**
 * The starting list, shown until staff save their own at
 * /admin/site-settings (the owners' request, 9 Nov 2026: links useful to
 * both sides, built up together). Titles and notes are catalog keys so the
 * copy stays the owners'; the addresses are the organisations' own.
 */
export const DEFAULT_JOB_LINKS: {
  title: TranslationKey;
  note: TranslationKey;
  url: string;
  audience: JobLinkAudience;
}[] = [
  {
    title: "jobLinks.labourTitle",
    note: "jobLinks.labourNote",
    url: "https://www.labor.gov.lb/",
    audience: "both",
  },
  {
    title: "jobLinks.daleelTitle",
    note: "jobLinks.daleelNote",
    url: "https://www.daleel-madani.org/",
    audience: "both",
  },
  {
    title: "jobLinks.nssfTitle",
    note: "jobLinks.nssfNote",
    url: "https://www.cnss.gov.lb/",
    audience: "both",
  },
];

export function useDefaultJobLinks(): JobLink[] {
  const t = useT();
  return DEFAULT_JOB_LINKS.map((link) => ({
    title: t(link.title),
    note: t(link.note),
    url: link.url,
    audience: link.audience,
  }));
}

/**
 * Useful links beside the candidates (/jobs, read by employers) and the
 * vacancies (/vacancies, read by people looking for work). A link marked
 * for both sides shows on both pages; an empty list saved by staff hides
 * the box altogether.
 */
export function JobLinksSidebar({
  audience,
  className,
}: {
  audience: Exclude<JobLinkAudience, "both">;
  className?: string;
}) {
  const t = useT();
  const fallback = useDefaultJobLinks();
  const saved = useQuery({
    queryKey: queryKeys.jobLinks,
    queryFn: siteSettingsApi.jobLinks,
    staleTime: 5 * 60_000,
  });
  if (!saved.data) return null;
  const links = (saved.data.links ?? fallback).filter(
    (link) => link.audience === "both" || link.audience === audience,
  );
  if (links.length === 0) return null;

  return (
    <aside
      aria-labelledby="job-links-heading"
      className={cn(
        "rounded-2xl border border-ink-100 bg-white p-5 shadow-card",
        className,
      )}
    >
      <h2
        id="job-links-heading"
        className="flex items-center gap-2 text-lg font-bold"
      >
        <Link2 className="h-5 w-5 text-brand-700" aria-hidden="true" />
        {t("jobLinks.heading")}
      </h2>
      <ul className="mt-4 space-y-3">
        {links.map((link) => (
          <li key={`${link.url}-${link.title}`}>
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group block rounded-xl border border-ink-100 p-3 transition hover:border-brand-300 hover:bg-brand-50"
            >
              <span className="flex items-center justify-between gap-2 font-semibold text-ink-800 group-hover:text-brand-800">
                {link.title}
                <ExternalLink
                  className="h-4 w-4 shrink-0 text-ink-400"
                  aria-hidden="true"
                />
              </span>
              {link.note ? (
                <span className="mt-1 block text-sm text-ink-500">
                  {link.note}
                </span>
              ) : null}
            </a>
          </li>
        ))}
      </ul>
    </aside>
  );
}
