declare module 'plotly.js-basic-dist-min' {
  const Plotly: {
    newPlot(target: HTMLElement, data: unknown[], layout: Record<string, unknown>, config?: Record<string, unknown>): Promise<unknown>;
    react(target: HTMLElement, data: unknown[], layout: Record<string, unknown>, config?: Record<string, unknown>): Promise<unknown>;
    purge(target: HTMLElement): void;
  };
  export default Plotly;
}

declare module 'aladin-lite' {
  const AladinLite: unknown;
  export default AladinLite;
}
