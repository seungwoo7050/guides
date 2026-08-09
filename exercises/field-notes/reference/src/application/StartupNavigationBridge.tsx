import type { NavigationIntent, NavigationIntentPort } from "@field-notes/shared";
import { usePathname, useRouter } from "expo-router";
import { useEffect, useRef } from "react";
import { ExpoLinkIntentAdapter } from "../adapters/ExpoLinkIntentAdapter";
import { applyReservedRoute } from "../navigation/CrossSourceRouteArbiter";
import {
  LatestStartupIntentBuffer,
  StartupIntentCoordinator,
} from "../navigation/decision";
import {
  intentKey,
  parseNavigationIntent,
} from "../navigation/stage01";
import { useAppRuntime } from "./AppRuntime";

export function StartupNavigationBridge() {
  const router = useRouter();
  const pathname = usePathname();
  const initialPathname = useRef(pathname).current;
  const { navigationArbiter, repository } = useAppRuntime();
  const adapter = useRef<NavigationIntentPort>(new ExpoLinkIntentAdapter()).current;
  const coordinator = useRef(
    new StartupIntentCoordinator({
      ready: () => repository.ready(),
      recordExists: async (recordId) => (await repository.get(recordId)) !== null,
    }),
  ).current;
  const bootstrapped = useRef(false);
  const pendingWarm = useRef(new LatestStartupIntentBuffer()).current;

  useEffect(() => {
    let active = true;
    let deliveryTail: Promise<void> = Promise.resolve();

    const reportFailure = (error: unknown) => {
      if (!active) return;
      const notice = `storage:${String(error)}`;
      router.replace(`/records?startupNotice=${encodeURIComponent(notice)}`);
    };

    const deliver = async (intent: NavigationIntent) => {
      const key = intentKey(intent);
      const decision = await coordinator.handle(intent, key);
      if (!active || decision.kind === "duplicate") {
        return;
      }
      const reservation = navigationArbiter.reserveLink(intent);
      if (reservation === null) return;
      try {
        if (decision.kind === "navigate") {
          applyReservedRoute(reservation, () => router.replace(decision.href));
          return;
        }
        const notice =
          decision.kind === "missing-record"
            ? `missing:${decision.recordId}`
            : `invalid:${decision.reason}`;
        applyReservedRoute(
          reservation,
          () => router.replace(`/records?startupNotice=${encodeURIComponent(notice)}`),
        );
      } catch (error) {
        coordinator.release(key);
        throw error;
      }
    };

    const bootstrap = async () => {
      const initial = await adapter.initial();
      if (!active) {
        return;
      }
      if (initial !== null) {
        await deliver(initial);
      } else if (initialPathname !== "/") {
        await deliver(parseNavigationIntent(initialPathname, "restoration"));
      }
      let queued = pendingWarm.take();
      while (queued !== null) {
        await deliver(queued);
        queued = pendingWarm.take();
      }
      bootstrapped.current = true;
    };

    void bootstrap().catch(reportFailure);
    const unsubscribe = adapter.subscribe((intent) => {
      if (!bootstrapped.current) {
        pendingWarm.offer(intent);
        return;
      }
      deliveryTail = deliveryTail.then(() => deliver(intent)).catch(reportFailure);
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, [adapter, coordinator, initialPathname, pendingWarm, router]);

  return null;
}
