#ifndef GAME_PRIMITIVES_Q3_FORMAL_FIXTURE_V0_1_0_H
#define GAME_PRIMITIVES_Q3_FORMAL_FIXTURE_V0_1_0_H

#include "q_shared.h"
#include "bg_public.h"

/*
 * This header is part of the project-owned compatibility and observation
 * boundary. It does not replace or rename any id Software movement rule.
 */

enum q3gp_branch_id {
	Q3GP_BRANCH_NONE = 0,
	Q3GP_BRANCH_FLIGHT = 1,
	Q3GP_BRANCH_GRAPPLE_AIR = 2,
	Q3GP_BRANCH_WATER_JUMP = 3,
	Q3GP_BRANCH_WATER = 4,
	Q3GP_BRANCH_WALK = 5,
	Q3GP_BRANCH_AIR = 6
};

typedef struct q3gp_step_observation_s {
	int branch_calls;
	int branch_id;
	int air_move_calls;
	float air_fmove;
	float air_smove;
	vec3_t wishdir;
	float wishspeed;
	int trace_calls;
	int pointcontents_calls;
	int event_calls;
	int printf_calls;
	int snap_calls;
	int trace_violation;
} q3gp_step_observation_t;

int Q3GP_ConfigureNearestEven(void);
int Q3GP_CheckAbi(void);
void Q3GP_ResetStepObservation(void);
const q3gp_step_observation_t *Q3GP_GetStepObservation(void);
void trap_SnapVector(float *v);

void Q3GP_EmptyTrace(
	trace_t *results,
	const vec3_t start,
	const vec3_t mins,
	const vec3_t maxs,
	const vec3_t end,
	int passEntityNum,
	int contentMask
);
int Q3GP_EmptyPointContents(const vec3_t point, int passEntityNum);

/*
 * These two callbacks are introduced by the separate observation patch.
 * They copy already-computed values and must never write movement state.
 */
void Q3GP_ObserveBranch(int branch_id);
void Q3GP_ObserveAirMove(
	float fmove,
	float smove,
	const vec3_t wishdir,
	float wishspeed
);

#endif
