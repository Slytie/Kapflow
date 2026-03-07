export interface ActorProfile {
  key: string;
  label: string;
  actorId: string;
  actorType: string;
  actorRoles: string;
}

export const ACTOR_PROFILES: ActorProfile[] = [
  {
    key: "frontend-operator",
    label: "Frontend Operator",
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  },
  {
    key: "dispatch-supervisor",
    label: "Dispatch Supervisor",
    actorId: "human:dispatch-supervisor-1",
    actorType: "human",
    actorRoles: "dispatch_supervisor"
  },
  {
    key: "operations-manager",
    label: "Operations Manager",
    actorId: "human:ops-manager-1",
    actorType: "human",
    actorRoles: "operations_manager"
  },
  {
    key: "fleet-coordinator",
    label: "Fleet Coordinator",
    actorId: "human:fleet-coordinator-1",
    actorType: "human",
    actorRoles: "fleet_coordinator"
  },
  {
    key: "schedule-planner",
    label: "Schedule Planner",
    actorId: "human:schedule-planner-1",
    actorType: "human",
    actorRoles: "schedule_planner"
  }
];

const UTILITY_PROFILE_KEYS = new Set(["frontend-operator"]);

export function actorLabelForActorId(actorId: string | null | undefined): string {
  if (!actorId) {
    return "Unassigned";
  }
  return ACTOR_PROFILES.find((profile) => profile.actorId === actorId)?.label ?? actorId;
}

export function candidateActorLabelsForRoles(
  roles: string[],
  includeUtilityProfiles = false
): string[] {
  const normalizedRoles = new Set(roles.map((role) => role.trim()).filter(Boolean));
  if (normalizedRoles.size === 0) {
    return [];
  }

  const labels = ACTOR_PROFILES.filter((profile) => {
    if (!includeUtilityProfiles && UTILITY_PROFILE_KEYS.has(profile.key)) {
      return false;
    }
    const actorRoles = profile.actorRoles
      .split(",")
      .map((role) => role.trim())
      .filter(Boolean);
    return actorRoles.some((role) => normalizedRoles.has(role));
  }).map((profile) => profile.label);

  if (labels.length > 0) {
    return labels;
  }

  return ACTOR_PROFILES.filter((profile) => {
    const actorRoles = profile.actorRoles
      .split(",")
      .map((role) => role.trim())
      .filter(Boolean);
    return actorRoles.some((role) => normalizedRoles.has(role));
  }).map((profile) => profile.label);
}
