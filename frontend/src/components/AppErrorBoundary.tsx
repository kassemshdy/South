import * as Sentry from "@sentry/react";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { ErrorState } from "@/components/ui/States";
import { isChunkLoadError, reloadOnce } from "@/utils/staleBuild";

interface State {
  error: unknown;
}

/**
 * The last line between a rendering error and a white page. A missing chunk
 * after a release is reloaded away (see `utils/staleBuild.ts`); anything else
 * is reported and shown as the site's ordinary error card with a retry.
 */
class Boundary extends Component<
  { children: ReactNode; resetKey: string },
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: unknown): State {
    return { error };
  }

  componentDidUpdate(previous: { resetKey: string }) {
    if (
      this.state.error !== null &&
      previous.resetKey !== this.props.resetKey
    ) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    if (isChunkLoadError(error) && reloadOnce()) return;
    Sentry.captureException(error, {
      extra: { componentStack: info.componentStack },
    });
  }

  render() {
    if (this.state.error !== null) {
      return (
        <div className="container-page py-16">
          <ErrorState
            error={this.state.error}
            onRetry={() => window.location.reload()}
          />
        </div>
      );
    }
    return this.props.children;
  }
}

/** Moving to another page clears an error on this one, without remounting
 * the app on every navigation as a `key` would. */
export function AppErrorBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return <Boundary resetKey={pathname}>{children}</Boundary>;
}
