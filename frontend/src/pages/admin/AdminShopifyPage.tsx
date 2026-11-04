import { useQuery } from "@tanstack/react-query";
import { Search, Store } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Card, CardBody } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { useStaffCan } from "@/features/admin/staffAccess";
import { ShopifyCard } from "@/features/integrations/ShopifyCard";
import { useT } from "@/i18n";
import { ApiError } from "@/services/api/client";
import { adminApi } from "@/services/api/endpoints";
import { queryKeys } from "@/services/api/queryKeys";
import { cn } from "@/utils/cn";

/**
 * Connect a shop's own Shopify store on its behalf (the owners' decision,
 * 4 Nov 2026): owners never see Shopify in their dashboard, so this page is
 * the only way in. Pick an approved shop on the left, manage its store on the
 * right. The chosen shop lives in `?business=`, which is also where Shopify's
 * approval screen sends the administrator back to.
 *
 * Hidden behind a 404 while the connector is not configured on the server.
 */
export function AdminShopifyPage() {
  const t = useT();
  const canManage = useStaffCan("manage");
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const selected = params.get("business");

  const shops = useQuery({
    queryKey: queryKeys.adminShopifyShops,
    queryFn: adminApi.shopifyShops,
    retry: false,
  });

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const list = shops.data ?? [];
    return needle
      ? list.filter((shop) => shop.name.toLowerCase().includes(needle))
      : list;
  }, [shops.data, query]);

  const choose = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("business", id);
    setParams(next, { replace: true });
  };

  const unavailable =
    shops.error instanceof ApiError && shops.error.status === 404;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl">{t("admin.shopifyHeading")}</h1>
        <p className="mt-1 text-sm text-ink-500">
          {t("admin.shopifySubtitle")}
        </p>
      </header>

      {unavailable ? (
        <EmptyState title={t("shopify.unavailable")} />
      ) : shops.isError ? (
        <ErrorState error={shops.error} onRetry={() => void shops.refetch()} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
          <Card>
            <CardBody className="space-y-3">
              <label className="relative block">
                <span className="sr-only">{t("admin.shopifySearch")}</span>
                <Search
                  className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400"
                  aria-hidden="true"
                />
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={t("admin.shopifySearch")}
                  className="ps-9"
                />
              </label>
              {shops.isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 6 }).map((_, index) => (
                    <Skeleton key={index} className="h-10" />
                  ))}
                </div>
              ) : visible.length === 0 ? (
                <p className="text-sm text-ink-500">
                  {t("admin.shopifyNoShops")}
                </p>
              ) : (
                <ul className="max-h-[32rem] space-y-1 overflow-y-auto">
                  {visible.map((shop) => (
                    <li key={shop.id}>
                      <button
                        type="button"
                        onClick={() => choose(shop.id)}
                        aria-current={shop.id === selected ? "true" : undefined}
                        className={cn(
                          "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-start text-sm",
                          shop.id === selected
                            ? "bg-brand-50 font-semibold text-brand-800"
                            : "hover:bg-sand-50",
                        )}
                      >
                        <span className="truncate">{shop.name}</span>
                        {shop.status === "CONNECTED" ? (
                          <span className="shrink-0 rounded-full bg-brand-100 px-2 py-0.5 text-xs text-brand-800">
                            {t("admin.shopifyConnectedBadge")}
                          </span>
                        ) : null}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          <div>
            {selected ? (
              <ShopifyCard
                key={selected}
                businessId={selected}
                canManage={canManage}
              />
            ) : (
              <Card>
                <CardBody className="flex items-center gap-3 text-ink-500">
                  <Store className="h-5 w-5" aria-hidden="true" />
                  {t("admin.shopifyPick")}
                </CardBody>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
