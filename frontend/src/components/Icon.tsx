import type { SVGProps } from "react";

export type IconName = "pin" | "paw" | "home" | "chart" | "shield" | "flask" | "rotate" | "calendar" | "clock" | "database" | "arrow" | "check" | "alert" | "external";

const paths: Record<IconName, string> = {
  pin: "M12 21s7-5.2 7-12a7 7 0 1 0-14 0c0 6.8 7 12 7 12Z M12 9a2.2 2.2 0 1 0 0-4.4A2.2 2.2 0 0 0 12 9Z",
  paw: "M7.5 10a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z M16.5 10a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z M4.5 14a1.8 1.8 0 1 1 0-3.6 1.8 1.8 0 0 1 0 3.6Z M19.5 14a1.8 1.8 0 1 1 0-3.6 1.8 1.8 0 0 1 0 3.6Z M12 12c-3.1 0-6.2 2.8-6.2 5.2 0 2.1 1.9 2.9 3.9 2 1.5-.7 3.1-.7 4.6 0 2 .9 3.9.1 3.9-2 0-2.4-3.1-5.2-6.2-5.2Z",
  home: "m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z",
  chart: "M4 19V5 M4 19h17 M8 15l3-4 3 2 5-7",
  shield: "M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z M9 12l2 2 4-4",
  flask: "M9 3h6 M10 3v6l-5.5 9.2A2 2 0 0 0 6.2 21h11.6a2 2 0 0 0 1.7-2.8L14 9V3 M8 15h8",
  rotate: "M20 7v5h-5 M4 17v-5h5 M6 9a7 7 0 0 1 12-2l2 2 M4 15l2 2a7 7 0 0 0 12-2",
  calendar: "M7 2v4 M17 2v4 M3 9h18 M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z M8 13h3 M8 17h3",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z M12 6v6l4 2",
  database: "M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3Z M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6 M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6",
  arrow: "M5 12h14 M13 6l6 6-6 6",
  check: "m5 12 4 4L19 6",
  alert: "M12 3 2.8 19a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L12 3Z M12 9v5 M12 18h.01",
  external: "M14 3h7v7 M10 14 21 3 M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",
};

export function Icon({ name, ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name]} /></svg>;
}
