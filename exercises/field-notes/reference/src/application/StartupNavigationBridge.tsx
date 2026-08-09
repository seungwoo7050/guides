import type { NavigationIntent, NavigationIntentPort } from "@field-notes/shared";
import { usePathname, useRouter } from "expo-router";
import { useEffect, useRef } from "react";
import { ExpoLinkIntentAdapter } from "../adapters/ExpoLinkIntentAdapter";
import { StartupIntentCoordinator } from "../navigation/decision";
import {
  intentKey,
  parseNavigationIntent,
} from "../navigation/stage01";
import { useAppRuntime } from "./AppRuntime";

export function StartupNavigationBridge() {
  const router = useRouter();
  const pathname = usePathname();
  const initialPathname = useRef(pathname).current;
  const { repository } = useAppRuntime();
  const adapter = useRef<NavigationIntentPort>(new ExpoLinkIntentAdapter()).current;
  const coordinator = useRef(
    new StartupIntentCoordinator({
      ready: () => repository.ready(),
      recordExists: async (recordId) => (await repository.get(recordId)) !== null,
    }),
  ).current;
  const bootstrapped = useRef(false);

  useEffect(() => {
    let active = true;

    const deliver = async (intent: NavigationIntent) => {
      const decision = await coordinator.handle(intent, intentKey(intent));
      if (!active || decision.kind === "duplicate") {
        return;
      }
      if (decision.kind === "navigate") {
        router.replace(decision.href);
        return;
      }
      const notice =
        decision.kind === "missing-record"
          ? `missing:${decision.recordId}`
          : `invalid:${decision.reason}`;
      router.replace(`/records?startupNotice=${encodeURIComponent(notice)}`);
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
      bootstrapped.current = true;
    };

    void bootstrap().catch((error: unknown) => {
      if (!active) return;
      const notice = `storage:${String(error)}`;
      router.replace(`/records?startupNotice=${encodeURIComponent(notice)}`);
    });
    const unsubscribe = adapter.subscribe((intent) => {
      if (bootstrapped.current) {
        void deliver(intent).catch((error: unknown) => {
          if (!active) return;
          const notice = `storage:${String(error)}`;
          router.replace(`/records?startupNotice=${encodeURIComponent(notice)}`);
        });
      }
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, [adapter, coordinator, initialPathname, router]);

  return null;
}
