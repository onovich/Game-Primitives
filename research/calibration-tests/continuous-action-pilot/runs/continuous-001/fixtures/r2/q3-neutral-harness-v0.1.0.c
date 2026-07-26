/*
 * THROWAWAY NEUTRAL COMPATIBILITY PROBE
 *
 * Question: can the unmodified movement units from official Quake III Arena
 * commit dbe4ddb10315479fc00086f08e25d968b4b43c49 be built by MSVC x64 with
 * ABI-stable neutral callbacks and nearest-even SnapVector compatibility?
 *
 * Scope: one zero-input 8 ms smoke command plus isolated stub sentinels.
 * This program never prints movement coordinates and must not be extended
 * into the formal 25 x 8 ms trajectory or any input-variable matrix.
 */

#include <float.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <xmmintrin.h>

#include "q_shared.h"
#include "bg_public.h"

#if !defined(WIN32)
#error WIN32 must be explicitly defined.
#endif

#if !defined(_WIN64) || !defined(_M_X64)
#error This compatibility probe must target MSVC x64.
#endif

#if defined(Q3_VM)
#error Q3_VM changes the ABI and is forbidden in this probe.
#endif

#if defined(MISSIONPACK)
#error MISSIONPACK changes layouts and paths and is forbidden in this probe.
#endif

#define PROBE_STATIC_ASSERT(name, expression) \
	typedef char probe_static_assert_##name[(expression) ? 1 : -1]

PROBE_STATIC_ASSERT(byte_width, sizeof(byte) == 1);
PROBE_STATIC_ASSERT(int_width, sizeof(int) == 4);
PROBE_STATIC_ASSERT(float_width, sizeof(float) == 4);
PROBE_STATIC_ASSERT(pointer_width, sizeof(void *) == 8);
PROBE_STATIC_ASSERT(vec3_size, sizeof(vec3_t) == 12);
PROBE_STATIC_ASSERT(cplane_size, sizeof(cplane_t) == 20);
PROBE_STATIC_ASSERT(trace_size, sizeof(trace_t) == 56);
PROBE_STATIC_ASSERT(usercmd_size, sizeof(usercmd_t) == 24);
PROBE_STATIC_ASSERT(usercmd_weapon_offset, offsetof(usercmd_t, weapon) == 20);
PROBE_STATIC_ASSERT(usercmd_forward_offset, offsetof(usercmd_t, forwardmove) == 21);
PROBE_STATIC_ASSERT(playerstate_size, sizeof(playerState_t) == 468);
PROBE_STATIC_ASSERT(playerstate_origin_offset, offsetof(playerState_t, origin) == 20);
PROBE_STATIC_ASSERT(playerstate_velocity_offset, offsetof(playerState_t, velocity) == 32);
PROBE_STATIC_ASSERT(playerstate_events_offset, offsetof(playerState_t, events) == 112);
PROBE_STATIC_ASSERT(playerstate_viewangles_offset, offsetof(playerState_t, viewangles) == 152);
PROBE_STATIC_ASSERT(playerstate_stats_offset, offsetof(playerState_t, stats) == 184);
PROBE_STATIC_ASSERT(pmove_size, sizeof(pmove_t) == 248);
PROBE_STATIC_ASSERT(pmove_cmd_offset, offsetof(pmove_t, cmd) == 8);
PROBE_STATIC_ASSERT(pmove_touchents_offset, offsetof(pmove_t, touchents) == 56);
PROBE_STATIC_ASSERT(pmove_trace_offset, offsetof(pmove_t, trace) == 232);
PROBE_STATIC_ASSERT(pmove_pointcontents_offset, offsetof(pmove_t, pointcontents) == 240);

static int probe_trace_calls;
static int probe_pointcontents_calls;
static int probe_event_calls;
static int probe_printf_calls;
static int probe_snap_calls;
static int probe_trace_violation;

gitem_t bg_itemlist[1];

static int ProbeConfigureNearestEven(void) {
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

void trap_SnapVector(float *v) {
	int i;

	probe_snap_calls++;
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
	probe_event_calls++;
	ps->events[ps->eventSequence & (MAX_PS_EVENTS - 1)] = newEvent;
	ps->eventParms[ps->eventSequence & (MAX_PS_EVENTS - 1)] = eventParm;
	ps->eventSequence++;
}

void QDECL Com_Printf(const char *format, ...) {
	(void)format;
	probe_printf_calls++;
}

static void ProbeEmptyTrace(
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

	probe_trace_calls++;
	memset(results, 0, sizeof(*results));
	results->fraction = 1.0f;
	VectorCopy(end, results->endpos);
	results->entityNum = ENTITYNUM_NONE;

	if (results->allsolid || results->startsolid
		|| results->fraction != 1.0f
		|| results->surfaceFlags != 0
		|| results->contents != 0
		|| results->entityNum != ENTITYNUM_NONE) {
		probe_trace_violation = 1;
	}
}

static int ProbeEmptyPointContents(
	const vec3_t point,
	int passEntityNum
) {
	(void)point;
	(void)passEntityNum;
	probe_pointcontents_calls++;
	return 0;
}

static int ProbeAbi(void) {
	return sizeof(byte) == 1
		&& sizeof(int) == 4
		&& sizeof(float) == 4
		&& sizeof(void *) == 8
		&& sizeof(usercmd_t) == 24
		&& sizeof(playerState_t) == 468
		&& sizeof(pmove_t) == 248
		&& offsetof(pmove_t, trace) == 232;
}

static int ProbeSnapVector(void) {
	float first[3] = { 0.5f, 1.5f, 2.5f };
	float second[3] = { -0.5f, -1.5f, -2.5f };
	float third[3] = { 3.5f, -3.5f, 0.49f };

	probe_snap_calls = 0;
	trap_SnapVector(first);
	trap_SnapVector(second);
	trap_SnapVector(third);

	return probe_snap_calls == 3
		&& first[0] == 0.0f
		&& first[1] == 2.0f
		&& first[2] == 2.0f
		&& second[0] == 0.0f
		&& second[1] == -2.0f
		&& second[2] == -2.0f
		&& third[0] == 4.0f
		&& third[1] == -4.0f
		&& third[2] == 0.0f;
}

static int ProbeEventStub(void) {
	playerState_t state;

	memset(&state, 0, sizeof(state));
	probe_event_calls = 0;
	BG_AddPredictableEventToPlayerstate(17, 23, &state);
	BG_AddPredictableEventToPlayerstate(19, 29, &state);
	BG_AddPredictableEventToPlayerstate(31, 37, &state);

	return probe_event_calls == 3
		&& state.eventSequence == 3
		&& state.events[0] == 31
		&& state.eventParms[0] == 37
		&& state.events[1] == 19
		&& state.eventParms[1] == 29;
}

static int ProbeCallbacks(void) {
	trace_t result;
	vec3_t start = { 1.0f, 2.0f, 3.0f };
	vec3_t end = { 4.0f, 5.0f, 6.0f };
	vec3_t bounds = { 0.0f, 0.0f, 0.0f };

	memset(&result, 0xa5, sizeof(result));
	probe_trace_calls = 0;
	probe_pointcontents_calls = 0;
	probe_trace_violation = 0;

	ProbeEmptyTrace(
		&result,
		start,
		bounds,
		bounds,
		end,
		ENTITYNUM_NONE,
		0
	);

	return probe_trace_calls == 1
		&& probe_trace_violation == 0
		&& result.fraction == 1.0f
		&& result.endpos[0] == end[0]
		&& result.endpos[1] == end[1]
		&& result.endpos[2] == end[2]
		&& result.entityNum == ENTITYNUM_NONE
		&& ProbeEmptyPointContents(start, ENTITYNUM_NONE) == 0
		&& probe_pointcontents_calls == 1;
}

static int ProbeNeutralPmove(void) {
	playerState_t state;
	pmove_t movement;

	memset(&state, 0, sizeof(state));
	memset(&movement, 0, sizeof(movement));

	state.pm_type = PM_NORMAL;
	state.gravity = 800;
	state.speed = 320;
	state.groundEntityNum = ENTITYNUM_NONE;
	state.stats[STAT_HEALTH] = 1;
	state.stats[STAT_MAX_HEALTH] = 100;
	state.persistant[PERS_TEAM] = TEAM_FREE;
	state.weapon = WP_NONE;
	state.weaponstate = WEAPON_READY;

	movement.ps = &state;
	movement.cmd.serverTime = 8;
	movement.cmd.weapon = WP_NONE;
	movement.tracemask = MASK_PLAYERSOLID;
	movement.pmove_fixed = qtrue;
	movement.pmove_msec = 8;
	movement.trace = ProbeEmptyTrace;
	movement.pointcontents = ProbeEmptyPointContents;

	probe_trace_calls = 0;
	probe_pointcontents_calls = 0;
	probe_event_calls = 0;
	probe_printf_calls = 0;
	probe_snap_calls = 0;
	probe_trace_violation = 0;

	Pmove(&movement);

	return state.commandTime == 8
		&& movement.cmd.serverTime == 8
		&& movement.cmd.buttons == 0
		&& movement.cmd.forwardmove == 0
		&& movement.cmd.rightmove == 0
		&& movement.cmd.upmove == 0
		&& movement.cmd.weapon == WP_NONE
		&& state.weapon == WP_NONE
		&& state.weaponstate == WEAPON_READY
		&& state.stats[STAT_HOLDABLE_ITEM] == 0
		&& !(state.pm_flags & PMF_USE_ITEM_HELD)
		&& state.groundEntityNum == ENTITYNUM_NONE
		&& movement.numtouch == 0
		&& movement.watertype == 0
		&& movement.waterlevel == 0
		&& probe_trace_calls > 0
		&& probe_pointcontents_calls > 0
		&& probe_trace_violation == 0
		&& probe_event_calls == 0
		&& probe_printf_calls == 0
		&& probe_snap_calls == 1;
}

static int ProbeStage(const char *passMarker, int result) {
	if (!result) {
		puts("SMOKE_FAIL");
		return 0;
	}
	puts(passMarker);
	return 1;
}

int main(void) {
	if (!ProbeStage("FP_ENV_PASS", ProbeConfigureNearestEven())) {
		return 10;
	}
	if (!ProbeStage("ABI_PACKING_PASS", ProbeAbi())) {
		return 11;
	}
	if (!ProbeStage("SNAPVECTOR_PASS", ProbeSnapVector())) {
		return 12;
	}
	if (!ProbeStage("EVENT_STUB_PASS", ProbeEventStub())) {
		return 13;
	}
	if (!ProbeStage("EMPTY_WORLD_PASS", ProbeCallbacks())) {
		return 14;
	}
	if (!ProbeStage("NEUTRAL_PMOVE_PASS", ProbeNeutralPmove())) {
		return 15;
	}

	puts("SMOKE_PASS");
	return 0;
}
