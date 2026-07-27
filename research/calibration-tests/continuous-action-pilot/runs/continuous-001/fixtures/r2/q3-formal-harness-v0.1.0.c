/*
 * GAME PRIMITIVES CA-R2 -- GUARDED FORMAL HARNESS
 *
 * The executable is input-independent and inert unless the post-prediction
 * formal runner supplies all execution-permit guards plus a permit-derived
 * command file. --self-test never calls Pmove or reads a formal step.
 *
 * Baseline and variant source copies differ at exactly one line: the active
 * input policy constant below. Both policies first copy the complete raw
 * usercmd. Entry latch then replaces only forwardmove and rightmove.
 */

#include <ctype.h>
#include <io.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "q3-formal-fixture-v0.1.0.h"

#define Q3GP_SOURCE_COMMIT \
	"dbe4ddb10315479fc00086f08e25d968b4b43c49"
#define Q3GP_RUN_ID "continuous-001"
#define Q3GP_CASE_ID "CA-R2"
#define Q3GP_POLICY_RESAMPLE 0
#define Q3GP_POLICY_ENTRY_LATCH 1
#define Q3GP_ACTIVE_INPUT_POLICY Q3GP_POLICY_RESAMPLE
#define Q3GP_FORMAL_STEP_COUNT 25

typedef struct q3gp_frozen_command_s {
	int server_time;
	int angles[3];
	int buttons;
	int weapon;
	int forwardmove;
	int rightmove;
	int upmove;
} q3gp_frozen_command_t;

static q3gp_frozen_command_t q3gp_frozen_commands[Q3GP_FORMAL_STEP_COUNT];

typedef struct q3gp_policy_state_s {
	int initialized;
	signed char forwardmove;
	signed char rightmove;
} q3gp_policy_state_t;

static int Q3GP_IsLowerNonZeroSha256(const char *value) {
	size_t i;
	int nonzero;

	if (value == NULL || strlen(value) != 64) {
		return 0;
	}
	nonzero = 0;
	for (i = 0; i < 64; i++) {
		if (!((value[i] >= '0' && value[i] <= '9')
			|| (value[i] >= 'a' && value[i] <= 'f'))) {
			return 0;
		}
		if (value[i] != '0') {
			nonzero = 1;
		}
	}
	return nonzero;
}

static int Q3GP_IsAbsoluteWindowsPath(const char *value) {
	if (value == NULL || value[0] == '\0') {
		return 0;
	}
	if (isalpha((unsigned char)value[0])
		&& value[1] == ':'
		&& (value[2] == '\\' || value[2] == '/')) {
		return 1;
	}
	return value[0] == '\\' && value[1] == '\\';
}

static int Q3GP_CopyPreservedFieldsEqual(
	const usercmd_t *raw,
	const usercmd_t *used
) {
	return raw->serverTime == used->serverTime
		&& raw->angles[0] == used->angles[0]
		&& raw->angles[1] == used->angles[1]
		&& raw->angles[2] == used->angles[2]
		&& raw->buttons == used->buttons
		&& raw->weapon == used->weapon
		&& raw->upmove == used->upmove;
}

static void Q3GP_SelectUsedCommand(
	q3gp_policy_state_t *policy,
	const usercmd_t *raw,
	usercmd_t *used
) {
	*used = *raw;

#if Q3GP_ACTIVE_INPUT_POLICY == Q3GP_POLICY_ENTRY_LATCH
	if (!policy->initialized) {
		policy->initialized = 1;
		policy->forwardmove = raw->forwardmove;
		policy->rightmove = raw->rightmove;
	}
	used->forwardmove = policy->forwardmove;
	used->rightmove = policy->rightmove;
#elif Q3GP_ACTIVE_INPUT_POLICY != Q3GP_POLICY_RESAMPLE
#error Unknown CA-R2 input policy.
#else
	(void)policy;
#endif
}

static const char *Q3GP_ConfigurationId(void) {
#if Q3GP_ACTIVE_INPUT_POLICY == Q3GP_POLICY_ENTRY_LATCH
	return "config.variant";
#else
	return "config.baseline";
#endif
}

static void Q3GP_LoadFrozenCommand(int index, usercmd_t *raw) {
	const q3gp_frozen_command_t *frozen;

	frozen = &q3gp_frozen_commands[index];
	memset(raw, 0, sizeof(*raw));
	raw->serverTime = frozen->server_time;
	raw->angles[0] = frozen->angles[0];
	raw->angles[1] = frozen->angles[1];
	raw->angles[2] = frozen->angles[2];
	raw->buttons = frozen->buttons;
	raw->weapon = (byte)frozen->weapon;
	raw->forwardmove = (signed char)frozen->forwardmove;
	raw->rightmove = (signed char)frozen->rightmove;
	raw->upmove = (signed char)frozen->upmove;
}

static int Q3GP_SelfTestPolicy(void) {
	q3gp_policy_state_t policy;
	usercmd_t first;
	usercmd_t second;
	usercmd_t usedFirst;
	usercmd_t usedSecond;

	memset(&policy, 0, sizeof(policy));
	memset(&first, 0, sizeof(first));
	memset(&second, 0, sizeof(second));
	first.serverTime = 13;
	first.angles[0] = 17;
	first.angles[1] = 19;
	first.angles[2] = 23;
	first.buttons = 29;
	first.weapon = 31;
	first.forwardmove = 37;
	first.rightmove = 41;
	first.upmove = 43;
	second.serverTime = 47;
	second.angles[0] = 53;
	second.angles[1] = 59;
	second.angles[2] = 61;
	second.buttons = 67;
	second.weapon = 71;
	second.forwardmove = 73;
	second.rightmove = 79;
	second.upmove = 83;

	Q3GP_SelectUsedCommand(&policy, &first, &usedFirst);
	Q3GP_SelectUsedCommand(&policy, &second, &usedSecond);

	if (!Q3GP_CopyPreservedFieldsEqual(&first, &usedFirst)
		|| !Q3GP_CopyPreservedFieldsEqual(&second, &usedSecond)) {
		return 0;
	}

#if Q3GP_ACTIVE_INPUT_POLICY == Q3GP_POLICY_ENTRY_LATCH
	return usedFirst.forwardmove == first.forwardmove
		&& usedFirst.rightmove == first.rightmove
		&& usedSecond.forwardmove == first.forwardmove
		&& usedSecond.rightmove == first.rightmove;
#else
	return memcmp(&first, &usedFirst, sizeof(first)) == 0
		&& memcmp(&second, &usedSecond, sizeof(second)) == 0;
#endif
}

static int Q3GP_RunSelfTest(void) {
	float first[3] = { 0.5f, 1.5f, 2.5f };
	float second[3] = { -0.5f, -1.5f, -2.5f };

	if (!Q3GP_ConfigureNearestEven() || !Q3GP_CheckAbi()) {
		return 0;
	}
	Q3GP_ResetStepObservation();
	trap_SnapVector(first);
	trap_SnapVector(second);

	return Q3GP_FORMAL_STEP_COUNT == 25
		&& Q3GP_GetStepObservation()->snap_calls == 2
		&& first[0] == 0.0f
		&& first[1] == 2.0f
		&& first[2] == 2.0f
		&& second[0] == 0.0f
		&& second[1] == -2.0f
		&& second[2] == -2.0f
		&& Q3GP_SelfTestPolicy();
}

static int Q3GP_FormalEnvironmentAbsent(void) {
	const char *names[] = {
		"GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256",
		"GAME_PRIMITIVES_PREDICTION_SET_DIGEST",
		"GAME_PRIMITIVES_RUN_ID",
		"GAME_PRIMITIVES_CASE_ID"
	};
	size_t index;

	for (index = 0; index < sizeof(names) / sizeof(names[0]); index++) {
		char *value = NULL;
		size_t length = 0;

		if (_dupenv_s(&value, &length, names[index]) != 0) {
			free(value);
			return 0;
		}
		if (value != NULL && value[0] != '\0') {
			free(value);
			return 0;
		}
		free(value);
	}
	return 1;
}

static int Q3GP_LoadExecutionContext(
	char **executionPermitDigest,
	char **predictionSetDigest,
	char **formalInputDigest
) {
	char *runId = NULL;
	char *caseId = NULL;
	char *permit = NULL;
	char *prediction = NULL;
	char *formalInput = NULL;
	size_t length;
	int result;

	*executionPermitDigest = NULL;
	*predictionSetDigest = NULL;
	*formalInputDigest = NULL;
	if (_dupenv_s(&runId, &length, "GAME_PRIMITIVES_RUN_ID") != 0
		|| _dupenv_s(&caseId, &length, "GAME_PRIMITIVES_CASE_ID") != 0
		|| _dupenv_s(
			&permit,
			&length,
			"GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256"
		) != 0
		|| _dupenv_s(
			&prediction,
			&length,
			"GAME_PRIMITIVES_PREDICTION_SET_DIGEST"
		) != 0
		|| _dupenv_s(
			&formalInput,
			&length,
			"GAME_PRIMITIVES_FORMAL_INPUT_SHA256"
		) != 0) {
		free(runId);
		free(caseId);
		free(permit);
		free(prediction);
		free(formalInput);
		return 0;
	}

	result = runId != NULL && strcmp(runId, Q3GP_RUN_ID) == 0
		&& caseId != NULL && strcmp(caseId, Q3GP_CASE_ID) == 0
		&& Q3GP_IsLowerNonZeroSha256(permit)
		&& Q3GP_IsLowerNonZeroSha256(prediction)
		&& Q3GP_IsLowerNonZeroSha256(formalInput);
	if (result) {
		*executionPermitDigest = permit;
		*predictionSetDigest = prediction;
		*formalInputDigest = formalInput;
		permit = NULL;
		prediction = NULL;
		formalInput = NULL;
	}
	free(runId);
	free(caseId);
	free(permit);
	free(prediction);
	free(formalInput);
	return result;
}

static int Q3GP_LoadCommandFile(const char *inputPath) {
	FILE *stream;
	char line[256];
	int index;

	if (!Q3GP_IsAbsoluteWindowsPath(inputPath)
		|| fopen_s(&stream, inputPath, "rb") != 0
		|| stream == NULL) {
		return 0;
	}
	for (index = 0; index < Q3GP_FORMAL_STEP_COUNT; index++) {
		q3gp_frozen_command_t *command;
		size_t length;
		char extra;
		int parsed;

		if (fgets(line, sizeof(line), stream) == NULL) {
			fclose(stream);
			return 0;
		}
		length = strlen(line);
		while (length > 0
			&& (line[length - 1] == '\n' || line[length - 1] == '\r')) {
			line[--length] = '\0';
		}
		command = &q3gp_frozen_commands[index];
		parsed = sscanf_s(
			line,
			"%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d%c",
			&command->server_time,
			&command->angles[0],
			&command->angles[1],
			&command->angles[2],
			&command->buttons,
			&command->weapon,
			&command->forwardmove,
			&command->rightmove,
			&command->upmove,
			&extra,
			(unsigned int)sizeof(extra)
		);
		if (parsed != 9) {
			fclose(stream);
			return 0;
		}
	}
	if (fgets(line, sizeof(line), stream) != NULL || fclose(stream) != 0) {
		return 0;
	}
	return 1;
}

static int Q3GP_WriteCommand(
	FILE *stream,
	const char *field,
	const usercmd_t *command
) {
	return fprintf(
		stream,
		"\"%s\":{\"serverTime\":%d,\"angles\":[%d,%d,%d],"
		"\"buttons\":%d,\"weapon\":%u,\"forwardmove\":%d,"
		"\"rightmove\":%d,\"upmove\":%d}",
		field,
		command->serverTime,
		command->angles[0],
		command->angles[1],
		command->angles[2],
		command->buttons,
		(unsigned int)command->weapon,
		(int)command->forwardmove,
		(int)command->rightmove,
		(int)command->upmove
	) > 0;
}

static int Q3GP_WriteStep(
	FILE *stream,
	int index,
	const usercmd_t *raw,
	const usercmd_t *used,
	const playerState_t *state,
	const pmove_t *movement,
	const q3gp_step_observation_t *observation
) {
	if (fprintf(
		stream,
		"{\"record_type\":\"step\",\"step_index\":%d,",
		index
	) < 0) {
		return 0;
	}
	if (!Q3GP_WriteCommand(stream, "raw_cmd", raw)
		|| fputc(',', stream) == EOF
		|| !Q3GP_WriteCommand(stream, "used_cmd", used)) {
		return 0;
	}
	return fprintf(
		stream,
		",\"branch_id\":%d,\"branch_calls\":%d,"
		"\"air_move_calls\":%d,\"air_fmove\":%.9g,"
		"\"air_smove\":%.9g,\"wishdir\":[%.9g,%.9g,%.9g],"
		"\"wishspeed\":%.9g,\"trace_calls\":%d,"
		"\"pointcontents_calls\":%d,\"event_calls\":%d,"
		"\"printf_calls\":%d,\"snap_calls\":%d,"
		"\"trace_violation\":%d,\"numtouch\":%d,"
		"\"watertype\":%d,\"waterlevel\":%d,"
		"\"groundEntityNum\":%d,\"commandTime\":%d,"
		"\"origin\":[%.9g,%.9g,%.9g],"
		"\"velocity\":[%.9g,%.9g,%.9g]}\n",
		observation->branch_id,
		observation->branch_calls,
		observation->air_move_calls,
		observation->air_fmove,
		observation->air_smove,
		observation->wishdir[0],
		observation->wishdir[1],
		observation->wishdir[2],
		observation->wishspeed,
		observation->trace_calls,
		observation->pointcontents_calls,
		observation->event_calls,
		observation->printf_calls,
		observation->snap_calls,
		observation->trace_violation,
		movement->numtouch,
		movement->watertype,
		movement->waterlevel,
		state->groundEntityNum,
		state->commandTime,
		state->origin[0],
		state->origin[1],
		state->origin[2],
		state->velocity[0],
		state->velocity[1],
		state->velocity[2]
	) > 0;
}

static int Q3GP_RunFormal(
	const char *inputPath,
	const char *outputPath
) {
	FILE *stream;
	char *executionPermitDigest = NULL;
	char *predictionSetDigest = NULL;
	char *formalInputDigest = NULL;
	playerState_t state;
	pmove_t movement;
	q3gp_policy_state_t policy;
	int index;

	if (!Q3GP_LoadExecutionContext(
			&executionPermitDigest,
			&predictionSetDigest,
			&formalInputDigest
		)
		|| !Q3GP_LoadCommandFile(inputPath)
		|| !Q3GP_IsAbsoluteWindowsPath(outputPath)
		|| _access(outputPath, 0) == 0) {
		free(executionPermitDigest);
		free(predictionSetDigest);
		free(formalInputDigest);
		return 0;
	}
	if (!Q3GP_ConfigureNearestEven() || !Q3GP_CheckAbi()) {
		free(executionPermitDigest);
		free(predictionSetDigest);
		free(formalInputDigest);
		return 0;
	}
	if (fopen_s(&stream, outputPath, "wb") != 0 || stream == NULL) {
		free(executionPermitDigest);
		free(predictionSetDigest);
		free(formalInputDigest);
		return 0;
	}

	setlocale(LC_NUMERIC, "C");
	memset(&state, 0, sizeof(state));
	memset(&movement, 0, sizeof(movement));
	memset(&policy, 0, sizeof(policy));

	state.pm_type = PM_NORMAL;
	state.origin[0] = 0.0f;
	state.origin[1] = 0.0f;
	state.origin[2] = 4096.0f;
	state.velocity[0] = 0.0f;
	state.velocity[1] = 0.0f;
	state.velocity[2] = 0.0f;
	state.gravity = 800;
	state.speed = 320;
	state.groundEntityNum = ENTITYNUM_NONE;
	state.stats[STAT_HEALTH] = 1;
	state.stats[STAT_MAX_HEALTH] = 100;
	state.persistant[PERS_TEAM] = TEAM_FREE;
	state.weapon = WP_NONE;
	state.weaponstate = WEAPON_READY;

	movement.ps = &state;
	movement.tracemask = MASK_PLAYERSOLID;
	movement.pmove_fixed = qtrue;
	movement.pmove_msec = 8;
	movement.trace = Q3GP_EmptyTrace;
	movement.pointcontents = Q3GP_EmptyPointContents;

	if (fprintf(
		stream,
		"{\"record_type\":\"run_header\",\"run_id\":\"%s\","
		"\"case_id\":\"%s\",\"configuration_id\":\"%s\","
		"\"source_commit\":\"%s\",\"input_sha256\":\"%s\","
		"\"execution_permit_sha256\":\"%s\","
		"\"prediction_set_digest\":\"%s\",\"platform_scope\":"
		"\"MSVC-x64\",\"step_count\":%d,\"step_ms\":8}\n",
		Q3GP_RUN_ID,
		Q3GP_CASE_ID,
		Q3GP_ConfigurationId(),
		Q3GP_SOURCE_COMMIT,
		formalInputDigest,
		executionPermitDigest,
		predictionSetDigest,
		Q3GP_FORMAL_STEP_COUNT
	) < 0) {
		fclose(stream);
		free(executionPermitDigest);
		free(predictionSetDigest);
		free(formalInputDigest);
		return 0;
	}

	for (index = 0; index < Q3GP_FORMAL_STEP_COUNT; index++) {
		usercmd_t raw;
		usercmd_t used;
		const q3gp_step_observation_t *observation;

		Q3GP_LoadFrozenCommand(index, &raw);
		Q3GP_SelectUsedCommand(&policy, &raw, &used);
		if (!Q3GP_CopyPreservedFieldsEqual(&raw, &used)) {
			fclose(stream);
			free(executionPermitDigest);
			free(predictionSetDigest);
			free(formalInputDigest);
			return 0;
		}
		movement.cmd = used;
		Q3GP_ResetStepObservation();
		Pmove(&movement);
		observation = Q3GP_GetStepObservation();

		if (state.commandTime != raw.serverTime
			|| observation->branch_calls != 1
			|| observation->branch_id != Q3GP_BRANCH_AIR
			|| observation->air_move_calls != 1
			|| observation->trace_calls <= 0
			|| observation->pointcontents_calls <= 0
			|| observation->event_calls != 0
			|| observation->printf_calls != 0
			|| observation->snap_calls != 1
			|| observation->trace_violation != 0
			|| movement.numtouch != 0
			|| movement.watertype != 0
			|| movement.waterlevel != 0
			|| state.groundEntityNum != ENTITYNUM_NONE) {
			fclose(stream);
			free(executionPermitDigest);
			free(predictionSetDigest);
			free(formalInputDigest);
			return 0;
		}
		if (!Q3GP_WriteStep(
			stream,
			index,
			&raw,
			&used,
			&state,
			&movement,
			observation
		)) {
			fclose(stream);
			free(executionPermitDigest);
			free(predictionSetDigest);
			free(formalInputDigest);
			return 0;
		}
	}

	if (state.commandTime != 200
		|| fprintf(
			stream,
			"{\"record_type\":\"stop\",\"rule_time_ms\":200,"
			"\"steps_completed\":25,\"invariants_passed\":true}\n"
		) < 0
		|| fclose(stream) != 0) {
		free(executionPermitDigest);
		free(predictionSetDigest);
		free(formalInputDigest);
		return 0;
	}
	free(executionPermitDigest);
	free(predictionSetDigest);
	free(formalInputDigest);
	return 1;
}

int main(int argc, char **argv) {
	if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
		if (!Q3GP_FormalEnvironmentAbsent() || !Q3GP_RunSelfTest()) {
			puts("SELF_TEST_FAIL");
			return 20;
		}
		puts("SELF_TEST_PASS");
		return 0;
	}

	if (argc == 6
		&& strcmp(argv[1], "--formal") == 0
		&& strcmp(argv[2], "--input") == 0
		&& strcmp(argv[4], "--output") == 0
		&& Q3GP_RunFormal(argv[3], argv[5])) {
		puts("FORMAL_EXECUTION_COMPLETE");
		return 0;
	}

	fputs("FORMAL_EXECUTION_REFUSED\n", stderr);
	return 64;
}
