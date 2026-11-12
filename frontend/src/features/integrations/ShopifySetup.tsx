import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Truck } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import { ApiError } from "@/services/api/client";
import { adminApi } from "@/services/api/endpoints";
import { queryKeys } from "@/services/api/queryKeys";
import type { ShopifySetup } from "@/types/api";
import { formatDateTime } from "@/utils/format";

/**
 * Prepare a connected store for Yalla Pay's checkout: Lebanon in an active
 * USD market and a delivery rate there, with the price and delivery time the
 * manager types here. The connector only adds what is missing and never
 * deletes what the shop set up in Shopify; its report shows below.
 */
export function ShopifySetupPanel({
  businessId,
  setup,
  canManage,
}: {
  businessId: string;
  setup: ShopifySetup | null;
  canManage: boolean;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [name, setName] = useState(setup?.rate_name ?? "Standard Delivery");
  const [price, setPrice] = useState("");
  const [days, setDays] = useState("");

  const run = useMutation({
    mutationFn: () =>
      adminApi.shopifySetup(businessId, {
        rate_name: name.trim(),
        price,
        description: days.trim() || null,
      }),
    onSuccess: ({ message }) => {
      toast.success(message);
      // The job runs in the background; look again shortly for its report.
      window.setTimeout(
        () =>
          void queryClient.invalidateQueries({
            queryKey: queryKeys.shopify(businessId),
          }),
        8000,
      );
    },
    onError: (error) =>
      toast.error(
        error instanceof ApiError ? error.message : t("states.errorFallback"),
      ),
  });

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (name.trim() && price !== "") run.mutate();
  };

  return (
    <div className="space-y-3 border-t border-ink-100 pt-4">
      <div>
        <h3 className="text-sm font-semibold text-ink-900">
          {t("shopify.setupTitle")}
        </h3>
        <p className="text-sm text-ink-500">{t("shopify.setupHint")}</p>
      </div>

      {setup ? (
        <ul className="space-y-1 rounded-xl bg-sand-50 p-3 text-sm text-ink-700">
          <li className="text-ink-500">
            {t("shopify.setupLast", {
              when: formatDateTime(setup.at, locale),
            })}
          </li>
          {setup.missing_scopes.length > 0 ? (
            <li className="text-red-700">{t("shopify.setupMissingScopes")}</li>
          ) : null}
          {!setup.currency_ok ? (
            <li className="text-red-700">
              {t("shopify.setupCurrency", {
                currency: setup.store_currency ?? "?",
              })}
            </li>
          ) : null}
          {setup.market_action ? (
            <li>
              {setup.market_active
                ? t(
                    setup.market_action === "created"
                      ? "shopify.setupMarketCreated"
                      : "shopify.setupMarketExisting",
                    { market: setup.market_name ?? "" },
                  )
                : t("shopify.setupMarketDraft", {
                    market: setup.market_name ?? "",
                  })}
            </li>
          ) : null}
          {setup.rate_name &&
          ["created", "added", "updated"].includes(setup.rate_action ?? "") ? (
            <li>{t("shopify.setupRateDone", { rate: setup.rate_name })}</li>
          ) : null}
          {setup.ok ? (
            <li className="font-semibold text-brand-800">
              {t("shopify.setupOk")}
            </li>
          ) : null}
        </ul>
      ) : null}

      {canManage ? (
        <form onSubmit={onSubmit} className="grid gap-2 sm:grid-cols-3">
          <Field label={t("shopify.setupRateName")}>
            {(field) => (
              <Input
                {...field}
                value={name}
                maxLength={60}
                onChange={(event) => setName(event.target.value)}
              />
            )}
          </Field>
          <Field label={t("shopify.setupPrice")}>
            {(field) => (
              <Input
                {...field}
                dir="ltr"
                type="number"
                min={0}
                step="0.01"
                value={price}
                placeholder="4.00"
                onChange={(event) => setPrice(event.target.value)}
              />
            )}
          </Field>
          <Field label={t("shopify.setupDays")}>
            {(field) => (
              <Input
                {...field}
                value={days}
                maxLength={120}
                placeholder={t("shopify.setupDaysPlaceholder")}
                onChange={(event) => setDays(event.target.value)}
              />
            )}
          </Field>
          <div className="sm:col-span-3">
            <Button
              type="submit"
              size="sm"
              disabled={run.isPending || !name.trim() || price === ""}
            >
              <Truck className="h-4 w-4" aria-hidden="true" />
              {t("shopify.setupSubmit")}
            </Button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
