export interface CapxUiVersionRoute {
  label: string;
  href: string;
}

export interface CapxUiVersionVariant {
  id: "design-a" | "design-b" | "design-c";
  shortName: string;
  name: string;
  subtitle: string;
  sourcePack: string;
  frameSrc: string;
  comparisonSrc: string;
  detailSrc: string;
  detailLabel: string;
  builtRoute?: string;
  builtLabel?: string;
  buildStatus?: string;
  sourceRoutes: CapxUiVersionRoute[];
}

const abcBase = "/capx-ui-versions/abc-selection";

export const capxUiVersionVariants: CapxUiVersionVariant[] = [
  {
    id: "design-a",
    shortName: "A",
    name: "Governed Workbench",
    subtitle: "Dense project workbench with queues, registers, evidence, and approval lanes.",
    sourcePack: "03 Design A + 05 A/B/C comparison",
    frameSrc: `${abcBase}/screens/design_a_workbench.html`,
    comparisonSrc: `${abcBase}/screens/design_a_workbench.html`,
    detailSrc: "/capx-ui-versions/design-a-final/prototype/final_clickable_blueprint_index.html",
    detailLabel: "Open full A blueprint",
    builtRoute: "/demo/capx/ui-versions/design-a",
    builtLabel: "Open completed A build",
    buildStatus: "React build ready for first-round user testing",
    sourceRoutes: [
      { label: "A test route", href: `${abcBase}/screens/design_a_workbench.html` },
      { label: "A 31-page blueprint", href: "/capx-ui-versions/design-a-final/prototype/final_clickable_blueprint_index.html" },
      { label: "A/B/C index", href: `${abcBase}/pass3_abc_comparison_index.html` }
    ]
  },
  {
    id: "design-b",
    shortName: "B",
    name: "State Atlas",
    subtitle: "Map-first project state, timeline replay, risk branching, and decision rooms.",
    sourcePack: "04 Design B + 05 A/B/C comparison",
    frameSrc: `${abcBase}/screens/design_b_state_atlas.html`,
    comparisonSrc: `${abcBase}/screens/design_b_state_atlas.html`,
    detailSrc: "/capx-ui-versions/design-b-state-atlas/prototype/pass3_comparison_prototype_index.html",
    detailLabel: "Open full B prototype",
    sourceRoutes: [
      { label: "B test route", href: `${abcBase}/screens/design_b_state_atlas.html` },
      { label: "B prototype index", href: "/capx-ui-versions/design-b-state-atlas/prototype/pass3_comparison_prototype_index.html" },
      { label: "B decision room", href: "/capx-ui-versions/design-b-state-atlas/prototype/screens/decision_room.html" }
    ]
  },
  {
    id: "design-c",
    shortName: "C",
    name: "Playbook OS",
    subtitle: "Protocol runner with evidence packets, readiness gates, and governed handoffs.",
    sourcePack: "05 Design C A/B/C selection framework",
    frameSrc: `${abcBase}/screens/design_c_playbook_os.html`,
    comparisonSrc: `${abcBase}/screens/design_c_playbook_os.html`,
    detailSrc: `${abcBase}/pass3_abc_comparison_index.html`,
    detailLabel: "Open full C framework",
    sourceRoutes: [
      { label: "C test route", href: `${abcBase}/screens/design_c_playbook_os.html` },
      { label: "C comparison index", href: `${abcBase}/pass3_abc_comparison_index.html` },
      { label: "Hybrid candidate", href: `${abcBase}/screens/hybrid_candidate.html` }
    ]
  }
];

export const capxUiScenarioRoutes: CapxUiVersionRoute[] = Array.from({ length: 12 }, (_, index) => {
  const routeNumber = String(index + 1).padStart(2, "0");
  return {
    label: `S${routeNumber}`,
    href: `${abcBase}/screens/s${routeNumber}.html`
  };
});
