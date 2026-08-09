import * as Linking from "expo-linking";
import Constants from "expo-constants";
import type {
  NavigationIntent,
  NavigationIntentPort,
} from "@field-notes/shared";
import { parseNavigationIntent } from "../navigation/stage01";

type LinkSource = {
  getInitialURL(): Promise<string | null>;
  addEventListener(
    eventName: "url",
    listener: (event: { url: string }) => void,
  ): { remove(): void };
};

export function resolvedAppScheme(
  configured: string | string[] | undefined = Constants.expoConfig?.scheme,
): string {
  if (typeof configured !== "string" || configured.length === 0) {
    throw new Error("resolved Expo app config must contain exactly one non-empty scheme");
  }
  return configured;
}

export class ExpoLinkIntentAdapter implements NavigationIntentPort {
  public constructor(
    private readonly expectedScheme = resolvedAppScheme(),
    private readonly source: LinkSource = Linking,
  ) {}

  public async initial(): Promise<NavigationIntent | null> {
    const url = await this.source.getInitialURL();
    return url === null
      ? null
      : parseNavigationIntent(url, "link", this.expectedScheme);
  }

  public subscribe(listener: (intent: NavigationIntent) => void): () => void {
    const subscription = this.source.addEventListener("url", ({ url }) => {
      listener(parseNavigationIntent(url, "link", this.expectedScheme));
    });
    return () => subscription.remove();
  }
}

/**
 * Notification envelopes keep their own durable claim/state owner and are not
 * parsed here. The application composes both sources only at a bounded route
 * arbiter, after each source has independently validated its input.
 */
