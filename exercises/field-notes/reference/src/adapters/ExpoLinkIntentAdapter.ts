import * as Linking from "expo-linking";
import type {
  NavigationIntent,
  NavigationIntentPort,
} from "@field-notes/shared";
import { parseNavigationIntent } from "../navigation/stage01";

export class ExpoLinkIntentAdapter implements NavigationIntentPort {
  public async initial(): Promise<NavigationIntent | null> {
    const url = await Linking.getInitialURL();
    return url === null ? null : parseNavigationIntent(url, "link");
  }

  public subscribe(listener: (intent: NavigationIntent) => void): () => void {
    const subscription = Linking.addEventListener("url", ({ url }) => {
      listener(parseNavigationIntent(url, "link"));
    });
    return () => subscription.remove();
  }
}

/**
 * Stage 05 will compose a notification adapter with this link adapter. Keeping
 * that input absent is intentional: a placeholder notification payload must
 * never be treated as authoritative record data in Stage 01.
 */

