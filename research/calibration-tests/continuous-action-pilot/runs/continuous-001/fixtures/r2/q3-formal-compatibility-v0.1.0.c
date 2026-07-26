/*
 * GAME PRIMITIVES CA-R2 -- MSVC x64 COMPATIBILITY LAYER
 *
 * Scope is deliberately narrower than historical Quake III execution:
 *   - official source commit dbe4ddb10315479fc00086f08e25d968b4b43c49;
 *   - MSVC x64, /fp:precise, nearest-even SSE SnapVector;
 *   - project-owned empty collision world and event/debug sentinels.
 *
 * This is not evidence of x87/x64 bit equivalence. If the formal claim ever
 * requires historical x87 coordinates with zero tolerance, execution stops.
 */

#include <float.h>
#include <stddef.h>
#include <string.h>
#include <xmmintrin.h>

#include "q3-compatibility-mode-v0.1.0.h"
#include "q3-formal-fixture-v0.1.0.h"

#if !defined(Q3GP_MSVC_X64_COMPATIBILITY) \
	|| Q3GP_MSVC_X64_COMPATIBILITY != 1
#error The frozen MSVC x64 compatibility patch has not been applied.
#endif

#if !defined(WIN32)
#error WIN32 must be explicitly defined.
#endif

#if !defined(_WIN64) || !defined(_M_X64)
#error CA-R2 formal fixture is limited to MSVC x64.
#endif

#if defined(Q3_VM)
#error Q3_VM changes the ABI and is forbidden.
#endif

#if defined(MISSIONPACK)
#error MISSIONPACK changes layouts and paths and is forbidden.
#endif

#if !defined(GAME_PRIMITIVES_OBSERVATION)
#error The frozen observation patch must be enabled.
#endif

#define Q3GP_STATIC_ASSERT(name, expression) \
	typedef char q3gp_static_assert_##name[(expression) ? 1 : -1]

Q3GP_STATIC_ASSERT(byte_width, sizeof(byte) == 1);
Q3GP_STATIC_ASSERT(int_width, sizeof(int) == 4);
Q3GP_STATIC_ASSERT(float_width, sizeof(float) == 4);
Q3GP_STATIC_ASSERT(pointer_width, sizeof(void *) == 8);
Q3GP_STATIC_ASSERT(vec3_size, sizeof(vec3_t) == 12);
Q3GP_STATIC_ASSERT(cplane_size, sizeof(cplane_t) == 20);
Q3GP_STATIC_ASSERT(trace_size, sizeof(trace_t) == 56);
Q3GP_STATIC_ASSERT(usercmd_size, sizeof(usercmd_t) == 24);
Q3GP_STATIC_ASSERT(usercmd_weapon_offset, offsetof(usercmd_t, weapon) == 20);
Q3GP_STATIC_ASSERT(usercmd_forward_offset, offsetof(usercmd_t, forwardmove) == 21);
Q3GP_STATIC_ASSERT(playerstate_size, sizeof(playerState_t) == 468);
Q3GP_STATIC_ASSERT(playerstate_origin_offset, offsetof(playerState_t, origin) == 20);
Q3GP_STATIC_ASSERT(playerstate_velocity_offset, offsetof(playerState_t, velocity) == 32);
Q3GP_STATIC_ASSERT(playerstate_events_offset, offsetof(playerState_t, events) == 112);
Q3GP_STATIC_ASSERT(playerstate_viewangles_offset, offsetof(playerState_t, viewangles) == 152);
Q3GP_STATIC_ASSERT(playerstate_stats_offset, offsetof(playerState_t, stats) == 184);
Q3GP_STATIC_ASSERT(pmove_size, sizeof(pmove_t) == 248);
Q3GP_STATIC_ASSERT(pmove_cmd_offset, offsetof(pmove_t, cmd) == 8);
Q3GP_STATIC_ASSERT(pmove_touchents_offset, offsetof(pmove_t, touchents) == 56);
Q3GP_STATIC_ASSERT(pmove_trace_offset, offsetof(pmove_t, trace) == 232);
Q3GP_STATIC_ASSERT(pmove_pointcontents_offset, offsetof(pmove_t, pointcontents) == 240);

static q3gp_step_observation_t q3gp_observation;

gitem_t bg_itemlist[1];

int Q3GP_ConfigureNearestEven(void) {
	unsigned int controlWord;
	unsigned int mxcsr;

	mxcsr = _mm_getcsr();
	mxcsr &= ~_MM_ROUND_MASK;
	mxcsr |= _MM_ROUND_NEAREST;
	_mm_setcsr(mxcsr);

	if (_controlfp_s(&controlWord, _RC_NEAR, _MCW_RC) != 0) {
		return 0;
	}

	return _MM_GET_ROUNDING_MODE() == _MM_ROUND_NEAREST
		&& (controlWord & _MCW_RC) == _RC_NEAR;
}

int Q3GP_CheckAbi(void) {
	return sizeof(byte) == 1
		&& sizeof(int) == 4
		&& sizeof(float) == 4
		&& sizeof(void *) == 8
		&& sizeof(usercmd_t) == 24
		&& sizeof(playerState_t) == 468
		&& sizeof(pmove_t) == 248
		&& offsetof(pmove_t, trace) == 232;
}

void Q3GP_ResetStepObservation(void) {
	memset(&q3gp_observation, 0, sizeof(q3gp_observation));
}

const q3gp_step_observation_t *Q3GP_GetStepObservation(void) {
	return &q3gp_observation;
}

void Q3GP_ObserveBranch(int branch_id) {
	q3gp_observation.branch_calls++;
	q3gp_observation.branch_id = branch_id;
}

void Q3GP_ObserveAirMove(
	float fmove,
	float smove,
	const vec3_t wishdir,
	float wishspeed
) {
	q3gp_observation.air_move_calls++;
	q3gp_observation.air_fmove = fmove;
	q3gp_observation.air_smove = smove;
	VectorCopy(wishdir, q3gp_observation.wishdir);
	q3gp_observation.wishspeed = wishspeed;
}

void trap_SnapVector(float *v) {
	int i;

	q3gp_observation.snap_calls++;
	for (i = 0; i < 3; i++) {
		__m128 scalar;
		int rounded;

		scalar = _mm_set_ss(v[i]);
		rounded = _mm_cvtss_si32(scalar);
		v[i] = (float)rounded;
	}
}

void BG_AddPredictableEventToPlayerstate(
	int newEvent,
	int eventParm,
	playerState_t *ps
) {
	q3gp_observation.event_calls++;
	ps->events[ps->eventSequence & (MAX_PS_EVENTS - 1)] = newEvent;
	ps->eventParms[ps->eventSequence & (MAX_PS_EVENTS - 1)] = eventParm;
	ps->eventSequence++;
}

void QDECL Com_Printf(const char *format, ...) {
	(void)format;
	q3gp_observation.printf_calls++;
}

void Q3GP_EmptyTrace(
	trace_t *results,
	const vec3_t start,
	const vec3_t mins,
	const vec3_t maxs,
	const vec3_t end,
	int passEntityNum,
	int contentMask
) {
	(void)start;
	(void)mins;
	(void)maxs;
	(void)passEntityNum;
	(void)contentMask;

	q3gp_observation.trace_calls++;
	memset(results, 0, sizeof(*results));
	results->fraction = 1.0f;
	VectorCopy(end, results->endpos);
	results->entityNum = ENTITYNUM_NONE;

	if (results->allsolid || results->startsolid
		|| results->fraction != 1.0f
		|| results->surfaceFlags != 0
		|| results->contents != 0
		|| results->entityNum != ENTITYNUM_NONE) {
		q3gp_observation.trace_violation = 1;
	}
}

int Q3GP_EmptyPointContents(const vec3_t point, int passEntityNum) {
	(void)point;
	(void)passEntityNum;
	q3gp_observation.pointcontents_calls++;
	return 0;
}
