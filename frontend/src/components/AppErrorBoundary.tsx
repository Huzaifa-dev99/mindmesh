import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  error: Error | null;
};

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("MindMesh render failed", error, info);
  }

  resetWorkspace = () => {
    localStorage.removeItem("mindmesh.token");
    localStorage.removeItem("mindmesh.user");
    localStorage.removeItem("mindmesh.sessionLocked");
    window.location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <main className="grid min-h-screen place-items-center bg-app px-5 py-10 text-foreground">
        <section className="w-full max-w-md rounded-2xl border border-border bg-elevated p-6 shadow-panel">
          <h1 className="text-xl font-semibold">MindMesh could not open</h1>
          <p className="mt-3 text-sm leading-6 text-muted">
            The workspace hit a browser-side startup error. Resetting the local session clears stale saved state.
          </p>
          <p className="mt-4 rounded-xl border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">
            {this.state.error.message || "Unknown frontend error"}
          </p>
          <button className="button-primary mt-5 h-11 w-full" onClick={this.resetWorkspace}>
            Reset Local Session
          </button>
        </section>
      </main>
    );
  }
}
