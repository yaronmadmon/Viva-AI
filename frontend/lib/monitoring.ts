/**
 * Optional Web Vitals and render tracking.
 * Targets: FCP < 1.8s, LCP < 2.5s.
 */

export function reportWebVitals(metric: { name: string; value: number }) {
  if (typeof window === "undefined") return;
  if (metric.name === "FCP" && metric.value > 1800) {
    console.warn("[Vitals] FCP slow:", metric.value, "ms");
  }
  if (metric.name === "LCP" && metric.value > 2500) {
    console.warn("[Vitals] LCP slow:", metric.value, "ms");
  }
}
