using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using Footsies;
using UnityEngine;

internal static class Program
{
    private static readonly BindingFlags PrivateInstance =
        BindingFlags.Instance | BindingFlags.NonPublic;

    // Six synthetic updates, intentionally distinct from the frozen seven-event
    // formal trace. No formal input path or generic input mode exists here.
    private static readonly int[] SyntheticInputs =
    {
        (int)InputDefine.Attack,
        (int)InputDefine.None,
        (int)InputDefine.None,
        (int)InputDefine.Attack,
        (int)InputDefine.None,
        (int)InputDefine.None,
    };

    private sealed class Options
    {
        internal string SourceRoot;
        internal string Configuration;
    }

    private sealed class Snapshot
    {
        public int tick { get; set; }
        public int input { get; set; }
        public int action_id { get; set; }
        public int action_frame { get; set; }
        public int buffered_action_id { get; set; }
        public bool cancel_eligible { get; set; }
        public float position_x { get; set; }
        public int hitbox_count { get; set; }
        public int hurtbox_count { get; set; }
    }

    private static int Main(string[] args)
    {
        try
        {
            RejectFormalEnvironment();
            Options options = ParseOptions(args);
            string assetHash = FrozenSourceContract.Verify(
                options.SourceRoot,
                options.Configuration);
            FighterData data = UnityYamlAssetLoader.LoadFighterData(options.SourceRoot);

            bool expectedControl = StringComparer.Ordinal.Equals(
                options.Configuration,
                FrozenSourceContract.VariantConfiguration);
            Require(
                data.canCancelOnWhiff == expectedControl,
                "F00.asset controlled value did not match the selected configuration.");

            List<Snapshot> observations = RunSynthetic(data);
            Snapshot final = observations[observations.Count - 1];
            bool passed;
            if (expectedControl)
            {
                passed =
                    final.action_id == (int)CommonActionID.N_SPECIAL
                    && final.buffered_action_id == -1
                    && final.cancel_eligible;
            }
            else
            {
                passed =
                    final.action_id == (int)CommonActionID.N_ATTACK
                    && final.buffered_action_id == (int)CommonActionID.N_SPECIAL
                    && !final.cancel_eligible;
            }
            Require(passed, "Synthetic whiff-cancel branch assertion failed.");

            var output = new
            {
                artifact_type = "continuous_action_r1_synthetic_smoke",
                artifact_version = "0.1.0",
                run_id = "continuous-001",
                case_id = "CA-R1",
                source_commit = FrozenSourceContract.Commit,
                configuration_id = options.Configuration,
                controlled_asset = new
                {
                    path = FrozenSourceContract.ControlledAssetPath,
                    sha256 = assetHash,
                    field = FrozenSourceContract.ControlledField,
                    value = data.canCancelOnWhiff,
                },
                synthetic_sequence = new
                {
                    kind = "synthetic_six_event_nonformal",
                    event_count = SyntheticInputs.Length,
                    inputs = SyntheticInputs,
                    differs_from_formal_event_count = SyntheticInputs.Length != 7,
                },
                observations,
                assertions = new
                {
                    branch_assertion_passed = passed,
                    source_hashes_verified = true,
                    exact_fighter_source_compiled = true,
                },
                formal_execution = new
                {
                    formal_environment_present = false,
                    formal_input_path_accepted = false,
                    formal_input_read = false,
                    formal_input_executed = false,
                    formal_runner_executed = false,
                    comparator_executed = false,
                    formal_result_created = false,
                },
            };

            Console.WriteLine(
                JsonSerializer.Serialize(
                    output,
                    new JsonSerializerOptions { WriteIndented = true }));
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error.GetType().Name + ": " + error.Message);
            return 1;
        }
    }

    private static List<Snapshot> RunSynthetic(FighterData data)
    {
        Fighter fighter = new Fighter();
        fighter.SetupBattleStart(data, new Vector2(0, 0), true);
        List<Snapshot> result = new List<Snapshot>();
        for (int tick = 0; tick < SyntheticInputs.Length; tick++)
        {
            fighter.UpdateInput(
                new InputData { input = SyntheticInputs[tick], time = tick });
            fighter.IncrementActionFrame();
            fighter.UpdateActionRequest();
            fighter.UpdateMovement();
            fighter.UpdateBoxes();
            result.Add(
                new Snapshot
                {
                    tick = tick,
                    input = SyntheticInputs[tick],
                    action_id = fighter.currentActionID,
                    action_frame = fighter.currentActionFrame,
                    buffered_action_id = ReadPrivateInt(fighter, "bufferActionID"),
                    cancel_eligible = InvokePrivateBool(fighter, "canCancelAttack"),
                    position_x = fighter.position.x,
                    hitbox_count = fighter.hitboxes.Count,
                    hurtbox_count = fighter.hurtboxes.Count,
                });
        }
        return result;
    }

    private static Options ParseOptions(string[] args)
    {
        if (args.Length != 5
            || !StringComparer.Ordinal.Equals(args[0], "--synthetic-smoke")
            || !StringComparer.Ordinal.Equals(args[1], "--source-root")
            || !StringComparer.Ordinal.Equals(args[3], "--configuration"))
        {
            throw new ArgumentException(
                "Only --synthetic-smoke --source-root <path> "
                + "--configuration <config.baseline|config.variant> is supported.");
        }
        if (!StringComparer.Ordinal.Equals(
                args[4],
                FrozenSourceContract.BaselineConfiguration)
            && !StringComparer.Ordinal.Equals(
                args[4],
                FrozenSourceContract.VariantConfiguration))
        {
            throw new ArgumentException("Unsupported synthetic configuration.");
        }

        return new Options
        {
            SourceRoot = args[2],
            Configuration = args[4],
        };
    }

    private static void RejectFormalEnvironment()
    {
        string[] names =
        {
            "GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256",
            "GAME_PRIMITIVES_FORMAL_INPUT_SHA256",
            "GAME_PRIMITIVES_PREDICTION_SET_DIGEST",
            "GAME_PRIMITIVES_RUN_ID",
            "GAME_PRIMITIVES_CASE_ID",
        };
        string present = names.FirstOrDefault(
            name => !String.IsNullOrEmpty(
                Environment.GetEnvironmentVariable(name, EnvironmentVariableTarget.Process)));
        if (present != null)
        {
            throw new InvalidOperationException(
                "Formal environment variable is forbidden in synthetic mode: " + present);
        }
    }

    private static int ReadPrivateInt(object target, string fieldName)
    {
        FieldInfo field = target.GetType().GetField(fieldName, PrivateInstance);
        if (field == null)
        {
            throw new MissingFieldException(target.GetType().FullName, fieldName);
        }
        return (int)field.GetValue(target);
    }

    private static bool InvokePrivateBool(object target, string methodName)
    {
        MethodInfo method = target.GetType().GetMethod(methodName, PrivateInstance);
        if (method == null)
        {
            throw new MissingMethodException(target.GetType().FullName, methodName);
        }
        return (bool)method.Invoke(target, null);
    }

    private static void Require(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException(message);
        }
    }
}
