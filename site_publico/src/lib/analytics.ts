import { captureAttribution } from "./attribution";

export type AnalyticsEvent =
  | "page_view"
  | "pricing_view"
  | "plan_select"
  | "lead_submit"
  | "demo_request"
  | "checkout_start"
  | "checkout_success"
  | "checkout_failure"
  | "login_click";

declare global {
  interface Window {
    dataLayer?: Record<string, unknown>[];
    plausible?: (event: string, options?: Record<string, unknown>) => void;
  }
}

export function track(
  eventName: AnalyticsEvent,
  properties: Record<string, unknown> = {},
): void {
  const attribution = captureAttribution();
  const event = {
    event: eventName,
    event_name: eventName,
    page_path: window.location.pathname,
    timestamp: new Date().toISOString(),
    utm_source: attribution.utm_source,
    utm_medium: attribution.utm_medium,
    utm_campaign: attribution.utm_campaign,
    ...properties,
  };
  window.dataLayer?.push(event);
  window.plausible?.(eventName, { props: event });
  window.dispatchEvent(new CustomEvent("vurix:analytics", { detail: event }));
}
