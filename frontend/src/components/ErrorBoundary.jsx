import { Component } from 'react';

// Catches render-time errors, including a lazy route chunk that fails to load
// after a new deploy, so one broken page shows a friendly message instead of
// white-screening the whole app. Pass a resetKey (the route path) so navigating
// to another page clears a caught error automatically.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, resetKey: props.resetKey };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  static getDerivedStateFromProps(props, state) {
    if (props.resetKey !== state.resetKey) {
      return { hasError: false, resetKey: props.resetKey };
    }
    return null;
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="container-page flex min-h-[60vh] flex-col items-center justify-center text-center">
        <h1 className="text-2xl font-bold tracking-tight text-ink-900">
          Something went wrong on this page.
        </h1>
        <p className="mt-3 max-w-md text-ink-500">
          This is on our side, not yours. Reloading usually clears it, and your answers are kept for
          this session, so you will not lose your place.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
          >
            Reload the page
          </button>
          <a
            href="/"
            className="rounded-xl border border-ink-200 px-5 py-2.5 text-sm font-semibold text-ink-700 transition-colors hover:border-brand-300"
          >
            Go home
          </a>
        </div>
      </div>
    );
  }
}
