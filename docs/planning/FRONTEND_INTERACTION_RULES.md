# FRONTEND_INTERACTION_RULES.md

## Locked interaction rules for v1

1. Inline actions are required.
- Task and approval actions must be visible on cards/rows.
- No mandatory navigation to detail page for primary state actions.
- Inline actions execute canonical API mutations (`claim`, `complete`, `respond`) through repositories.

2. Descriptions stay hidden on compact surfaces.
- Card/row surfaces show dense metadata and action affordances.
- Full description/details are drawer-first (`DetailDrawer`).

3. Attachment affordances are inline.
- Upload/download controls are visible in both card and row surfaces.
- Attachment actions are not hidden behind deep navigation.
- Upload/download delegates to canonical artifact-backed API endpoints; no client-side shadow attachment store is allowed.

4. Low-click expert flow is mandatory.
- Minimize clicks for claim/complete/review loops.
- Preserve high information density and scanability.

5. No drag-to-transition semantics.
- Transition intent uses explicit controls only.
- Drag-and-drop cannot be a state authority path.

6. Drawer-first detail model.
- Right-side drawer is the default deep-inspection surface.
- Page transitions are for scope/context changes, not every detail lookup.

7. Client does not own workflow semantics.
- Client maps canonical fields for presentation only.
- Any semantic transition meaning belongs to backend contracts/runtime.
- API error responses are surfaced to users; client does not reinterpret forbidden/invalid transitions.

8. Workspace graph/action synchronization is mandatory.
- `/runs/:workflowRunId/workspace` renders graph (top) and actionable work (bottom) from one server workspace projection.
- Graph node/edge status must mirror projection fields; client does not infer true stage state.
- Inline actions refresh the shared workspace query so graph and action panel update together.

9. Workspace actionability is explicit.
- `available_actions` controls whether action controls are enabled.
- `missing_required_inputs` must be visible when `complete` is disabled.
- Stage06 AI review control is visible only when `run_stage06_agent_review` is present.

10. Polling remains the live-update mechanism.
- React Query polling is the first refresh mechanism for workspace graph/action panels.
- Push channels (websocket/SSE) remain out of scope for this slice.
