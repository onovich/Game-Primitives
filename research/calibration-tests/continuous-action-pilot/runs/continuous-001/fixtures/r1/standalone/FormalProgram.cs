// Permit-bound formal test body for CA-R1.
//
// This is a separate executable from Program.cs, the synthetic smoke. The
// PowerShell formal runner must verify the execution permit before starting
// this program. This body independently requires all permit-derived bindings,
// verifies the frozen input hash before deserializing it, executes exactly
// seven updates, and emits the existing ca_r1_raw_trace interface.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Footsies;
using UnityEngine;

internal static class FormalProgram
{
    private static readonly BindingFlags PrivateInstance =
        BindingFlags.Instance | BindingFlags.NonPublic;

    private sealed class Options
    {
        internal string SourceRoot;
        internal string Configuration;
        internal string InputPath;
        internal string OutputPath;
    }

    private sealed class TraceEntry
    {
        internal int AfterActionFrame;
        internal int AfterActionId;
        internal int AfterBufferActionId;
        internal int AttackHeld;
        internal int BeforeActionFrame;
        internal int BeforeActionId;
        internal int BeforeBufferActionId;
        internal int CancelEligibleBefore;
        internal int ContactCount;
        internal string EventId;
        internal int HitCount;
        internal int InputDown;
        internal int InputValue;
        internal int SequenceIndex;
    }

    private static int Main(string[] args)
    {
        try
        {
            string runId = RequireEnvironment("GAME_PRIMITIVES_RUN_ID");
            string caseId = RequireEnvironment("GAME_PRIMITIVES_CASE_ID");
            string executionPermitSha = RequireLowercaseNonzeroSha256(
                "GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256");
            string predictionSetDigest = RequireLowercaseNonzeroSha256(
                "GAME_PRIMITIVES_PREDICTION_SET_DIGEST");
            string expectedInputSha = RequireLowercaseNonzeroSha256(
                "GAME_PRIMITIVES_FORMAL_INPUT_SHA256");
            Require(
                StringComparer.Ordinal.Equals(runId, "continuous-001"),
                "Execution permit has an unexpected run_id.");
            Require(
                StringComparer.Ordinal.Equals(caseId, "CA-R1"),
                "Execution permit has an unexpected case_id.");

            Options options = ParseOptions(args);
            Require(
                !File.Exists(options.OutputPath),
                "Formal raw output path already exists.");
            string controlledAssetSha = FrozenSourceContract.Verify(
                options.SourceRoot,
                options.Configuration);
            FighterData fighterData = UnityYamlAssetLoader.LoadFighterData(
                options.SourceRoot);

            int expectedControlledValue = StringComparer.Ordinal.Equals(
                options.Configuration,
                FrozenSourceContract.BaselineConfiguration)
                ? 0
                : 1;
            Require(
                (fighterData.canCancelOnWhiff ? 1 : 0) == expectedControlledValue,
                "Controlled asset value does not match configuration_id.");
            Require(
                StringComparer.Ordinal.Equals(
                    controlledAssetSha,
                    expectedControlledValue == 0
                        ? FrozenSourceContract.BaselineAssetSha256
                        : FrozenSourceContract.VariantAssetSha256),
                "Controlled asset hash is inconsistent with its value.");

            byte[] inputBytes = File.ReadAllBytes(options.InputPath);
            string actualInputSha = Sha256(inputBytes);
            Require(
                StringComparer.Ordinal.Equals(actualInputSha, expectedInputSha),
                "Formal input SHA-256 does not match the execution permit.");

            using JsonDocument inputDocument = JsonDocument.Parse(
                inputBytes,
                new JsonDocumentOptions
                {
                    AllowTrailingCommas = false,
                    CommentHandling = JsonCommentHandling.Disallow,
                    MaxDepth = 32,
                });
            RequireUniqueProperties(inputDocument.RootElement);
            JsonElement root = inputDocument.RootElement;
            Require(root.ValueKind == JsonValueKind.Object, "Formal input must be an object.");
            RequireString(root, "artifact_type", "formal_input_trace");
            RequireString(root, "artifact_version", "0.1.0");
            RequireString(root, "case_id", caseId);
            RequireString(root, "run_id", runId);
            string formalInputId = RequiredString(root, "formal_input_id");
            string stopBoundaryId = RequiredString(root, "stop_boundary_id");
            Require(
                StringComparer.Ordinal.Equals(formalInputId, "o.a.0002"),
                "Unexpected formal_input_id.");
            Require(
                StringComparer.Ordinal.Equals(stopBoundaryId, "o.a.0042"),
                "Unexpected stop_boundary_id.");

            JsonElement events = RequiredProperty(root, "input_events");
            Require(events.ValueKind == JsonValueKind.Array, "input_events must be an array.");
            Require(events.GetArrayLength() == 7, "Expected exactly seven formal updates.");

            Fighter fighter = new Fighter();
            Fighter opponent = new Fighter();
            fighter.SetupBattleStart(fighterData, new Vector2(0f, 0f), true);
            opponent.SetupBattleStart(fighterData, new Vector2(1000f, 0f), false);

            List<TraceEntry> entries = new List<TraceEntry>();
            int index = 0;
            foreach (JsonElement inputEvent in events.EnumerateArray())
            {
                Require(
                    RequiredInt32(inputEvent, "sequence_index") == index,
                    "Formal input sequence_index is not contiguous.");
                Require(
                    ParseInteger(RequiredProperty(inputEvent, "at")) == index,
                    "Formal input time does not match sequence_index.");
                string eventId = RequiredString(inputEvent, "event_id");
                Require(
                    StringComparer.Ordinal.Equals(
                        eventId,
                        "event.ca-r1.update-" + index.ToString(CultureInfo.InvariantCulture)),
                    "Formal event_id is outside the frozen CA-R1 sequence.");

                bool attackHeld = ParseBoolean(
                    FindField(inputEvent, "input.attack-held"));
                int horizontal = ParseInteger(
                    FindField(inputEvent, "input.horizontal"));
                Require(
                    horizontal >= -1 && horizontal <= 1,
                    "Horizontal input is outside the digital range.");

                int inputValue = attackHeld
                    ? (int)InputDefine.Attack
                    : (int)InputDefine.None;
                if (horizontal < 0)
                {
                    inputValue |= (int)InputDefine.Left;
                }
                else if (horizontal > 0)
                {
                    inputValue |= (int)InputDefine.Right;
                }

                fighter.UpdateInput(new InputData { input = inputValue, time = index });
                opponent.UpdateInput(new InputData { input = 0, time = index });
                fighter.IncrementActionFrame();
                opponent.IncrementActionFrame();

                TraceEntry entry = new TraceEntry
                {
                    AttackHeld = attackHeld ? 1 : 0,
                    BeforeActionFrame = fighter.currentActionFrame,
                    BeforeActionId = fighter.currentActionID,
                    BeforeBufferActionId = ReadPrivateInt(fighter, "bufferActionID"),
                    CancelEligibleBefore = InvokePrivateBool(fighter, "canCancelAttack")
                        ? 1
                        : 0,
                    EventId = eventId,
                    InputDown = ReadInputDown(fighter),
                    InputValue = inputValue,
                    SequenceIndex = index,
                };

                fighter.UpdateActionRequest();
                opponent.UpdateActionRequest();
                fighter.UpdateMovement();
                opponent.UpdateMovement();
                fighter.UpdateBoxes();
                opponent.UpdateBoxes();

                entry.AfterActionFrame = fighter.currentActionFrame;
                entry.AfterActionId = fighter.currentActionID;
                entry.AfterBufferActionId = ReadPrivateInt(fighter, "bufferActionID");
                entry.ContactCount = CountContacts(fighter, opponent);
                entry.HitCount = fighter.currentActionHitCount;
                entries.Add(entry);
                index++;
            }

            bool zeroContacts = entries.All(entry => entry.ContactCount == 0);
            bool zeroHits = entries.All(entry => entry.HitCount == 0);
            bool firstRecognized =
                entries[0].AfterActionId == (int)CommonActionID.N_ATTACK;
            bool secondBuffered =
                entries[2].AfterBufferActionId == (int)CommonActionID.N_SPECIAL;
            Require(zeroContacts, "Contact invariant failed.");
            Require(zeroHits, "Hit-count invariant failed.");
            Require(firstRecognized, "First request recognition invariant failed.");
            Require(secondBuffered, "Second request buffering invariant failed.");

            byte[] traceBytes = BuildCanonicalTrace(
                caseId,
                options.Configuration,
                expectedControlledValue,
                executionPermitSha,
                formalInputId,
                actualInputSha,
                firstRecognized,
                secondBuffered,
                zeroContacts,
                zeroHits,
                predictionSetDigest,
                runId,
                stopBoundaryId,
                entries);
            WriteNewAtomically(options.OutputPath, traceBytes);
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error.ToString());
            return 1;
        }
    }

    private static byte[] BuildCanonicalTrace(
        string caseId,
        string configurationId,
        int controlledValue,
        string executionPermitSha,
        string formalInputId,
        string formalInputSha,
        bool firstRecognized,
        bool secondBuffered,
        bool zeroContacts,
        bool zeroHits,
        string predictionSetDigest,
        string runId,
        string stopBoundaryId,
        IReadOnlyList<TraceEntry> entries)
    {
        using MemoryStream stream = new MemoryStream();
        using (Utf8JsonWriter writer = new Utf8JsonWriter(
            stream,
            new JsonWriterOptions
            {
                Indented = false,
                SkipValidation = false,
            }))
        {
            writer.WriteStartObject();
            writer.WriteString("artifact_type", "ca_r1_raw_trace");
            writer.WriteString("case_id", caseId);
            writer.WriteString("configuration_id", configurationId);
            writer.WriteNumber("controlled_value", controlledValue);
            writer.WriteString("execution_permit_sha256", executionPermitSha);
            writer.WriteString("formal_input_id", formalInputId);
            writer.WriteString("formal_input_sha256", formalInputSha);
            writer.WriteNumber("invariant_first_request_recognized", firstRecognized ? 1 : 0);
            writer.WriteNumber("invariant_second_request_buffered", secondBuffered ? 1 : 0);
            writer.WriteNumber("invariant_zero_contacts", zeroContacts ? 1 : 0);
            writer.WriteNumber("invariant_zero_hits", zeroHits ? 1 : 0);
            writer.WriteString("prediction_set_digest", predictionSetDigest);
            writer.WriteString("run_id", runId);
            writer.WriteString("stop_boundary_id", stopBoundaryId);
            writer.WritePropertyName("trace_entries");
            writer.WriteStartArray();
            foreach (TraceEntry entry in entries)
            {
                writer.WriteStartObject();
                writer.WriteNumber("after_action_frame", entry.AfterActionFrame);
                writer.WriteNumber("after_action_id", entry.AfterActionId);
                writer.WriteNumber("after_buffer_action_id", entry.AfterBufferActionId);
                writer.WriteNumber("attack_held", entry.AttackHeld);
                writer.WriteNumber("before_action_frame", entry.BeforeActionFrame);
                writer.WriteNumber("before_action_id", entry.BeforeActionId);
                writer.WriteNumber("before_buffer_action_id", entry.BeforeBufferActionId);
                writer.WriteNumber("cancel_eligible_before", entry.CancelEligibleBefore);
                writer.WriteNumber("contact_count", entry.ContactCount);
                writer.WriteString("event_id", entry.EventId);
                writer.WriteNumber("hit_count", entry.HitCount);
                writer.WriteNumber("input_down", entry.InputDown);
                writer.WriteNumber("input_value", entry.InputValue);
                writer.WriteNumber("sequence_index", entry.SequenceIndex);
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }

        byte[] json = stream.ToArray();
        byte[] result = new byte[json.Length + 1];
        Buffer.BlockCopy(json, 0, result, 0, json.Length);
        result[result.Length - 1] = (byte)'\n';
        return result;
    }

    private static Options ParseOptions(string[] args)
    {
        if (args.Length != 1
            || !StringComparer.Ordinal.Equals(args[0], "--formal"))
        {
            throw new ArgumentException(
                "The permit-bound formal body accepts only the --formal mode token.");
        }
        string sourceRoot = RequireEnvironment("GP_R1_SOURCE_ROOT");
        string configuration = RequireEnvironment("GP_R1_CONFIGURATION_ID");
        string inputPath = RequireEnvironment("GP_R1_INPUT_PATH");
        string outputPath = RequireEnvironment("GP_R1_OUTPUT_PATH");
        if (!StringComparer.Ordinal.Equals(
                configuration,
                FrozenSourceContract.BaselineConfiguration)
            && !StringComparer.Ordinal.Equals(
                configuration,
                FrozenSourceContract.VariantConfiguration))
        {
            throw new ArgumentException("Unsupported formal configuration.");
        }
        if (!Path.IsPathRooted(sourceRoot)
            || !Path.IsPathRooted(inputPath)
            || !Path.IsPathRooted(outputPath))
        {
            throw new ArgumentException("Formal source, input, and output paths must be absolute.");
        }

        return new Options
        {
            SourceRoot = Path.GetFullPath(sourceRoot),
            Configuration = configuration,
            InputPath = Path.GetFullPath(inputPath),
            OutputPath = Path.GetFullPath(outputPath),
        };
    }

    private static JsonElement FindField(JsonElement inputEvent, string fieldId)
    {
        JsonElement fields = RequiredProperty(inputEvent, "fields");
        Require(fields.ValueKind == JsonValueKind.Array, "Event fields must be an array.");
        JsonElement? found = null;
        foreach (JsonElement field in fields.EnumerateArray())
        {
            if (StringComparer.Ordinal.Equals(RequiredString(field, "field_id"), fieldId))
            {
                Require(found == null, "Duplicate formal input field: " + fieldId);
                found = RequiredProperty(field, "value");
            }
        }
        Require(found != null, "Missing formal input field: " + fieldId);
        return found.Value;
    }

    private static bool ParseBoolean(JsonElement scalar)
    {
        RequireString(scalar, "value_type", "boolean");
        string serialized = RequiredString(scalar, "serialized_value");
        Require(
            Boolean.TryParse(serialized, out bool value),
            "Invalid boolean scalar.");
        return value;
    }

    private static int ParseInteger(JsonElement scalar)
    {
        RequireString(scalar, "value_type", "integer");
        string serialized = RequiredString(scalar, "serialized_value");
        Require(
            Int32.TryParse(
                serialized,
                NumberStyles.Integer,
                CultureInfo.InvariantCulture,
                out int value),
            "Invalid integer scalar.");
        return value;
    }

    private static JsonElement RequiredProperty(JsonElement value, string property)
    {
        Require(value.ValueKind == JsonValueKind.Object, "Expected a JSON object.");
        Require(value.TryGetProperty(property, out JsonElement result), "Missing " + property + ".");
        return result;
    }

    private static string RequiredString(JsonElement value, string property)
    {
        JsonElement result = RequiredProperty(value, property);
        Require(result.ValueKind == JsonValueKind.String, property + " must be a string.");
        return result.GetString();
    }

    private static int RequiredInt32(JsonElement value, string property)
    {
        JsonElement result = RequiredProperty(value, property);
        int parsed = 0;
        Require(
            result.ValueKind == JsonValueKind.Number && result.TryGetInt32(out parsed),
            property + " must be an Int32.");
        return parsed;
    }

    private static void RequireString(
        JsonElement value,
        string property,
        string expected)
    {
        Require(
            StringComparer.Ordinal.Equals(RequiredString(value, property), expected),
            "Unexpected " + property + ".");
    }

    private static void RequireUniqueProperties(JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            HashSet<string> names = new HashSet<string>(StringComparer.Ordinal);
            foreach (JsonProperty property in value.EnumerateObject())
            {
                Require(names.Add(property.Name), "Duplicate JSON property: " + property.Name);
                RequireUniqueProperties(property.Value);
            }
        }
        else if (value.ValueKind == JsonValueKind.Array)
        {
            foreach (JsonElement item in value.EnumerateArray())
            {
                RequireUniqueProperties(item);
            }
        }
    }

    private static int CountContacts(Fighter fighter, Fighter opponent)
    {
        int count = 0;
        foreach (Hitbox hitbox in fighter.hitboxes)
        {
            if (hitbox.proximity)
            {
                continue;
            }
            foreach (Hurtbox hurtbox in opponent.hurtboxes)
            {
                if (hitbox.Overlaps(hurtbox))
                {
                    count++;
                }
            }
        }
        return count;
    }

    private static bool InvokePrivateBool(object target, string methodName)
    {
        MethodInfo method = target.GetType().GetMethod(methodName, PrivateInstance);
        Require(method != null, "Missing private method: " + methodName);
        return (bool)method.Invoke(target, null);
    }

    private static int ReadInputDown(Fighter fighter)
    {
        FieldInfo field = typeof(Fighter).GetField("inputDown", PrivateInstance);
        Require(field != null, "Missing inputDown field.");
        int[] values = (int[])field.GetValue(fighter);
        Require(values != null && values.Length > 0, "inputDown is empty.");
        return values[0];
    }

    private static int ReadPrivateInt(object target, string fieldName)
    {
        FieldInfo field = target.GetType().GetField(fieldName, PrivateInstance);
        Require(field != null, "Missing private field: " + fieldName);
        return (int)field.GetValue(target);
    }

    private static string RequireEnvironment(string name)
    {
        string value = Environment.GetEnvironmentVariable(
            name,
            EnvironmentVariableTarget.Process);
        Require(!String.IsNullOrEmpty(value), "Missing environment variable: " + name);
        return value;
    }

    private static string RequireLowercaseNonzeroSha256(string name)
    {
        string value = RequireEnvironment(name);
        Require(
            value.Length == 64
                && value.Any(character => character != '0')
                && value.All(character =>
                    (character >= '0' && character <= '9')
                    || (character >= 'a' && character <= 'f')),
            name + " must be a nonzero lowercase SHA-256.");
        return value;
    }

    private static string Sha256(byte[] bytes)
    {
        return Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    }

    private static void WriteNewAtomically(string outputPath, byte[] bytes)
    {
        string directory = Path.GetDirectoryName(outputPath);
        if (!String.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }
        string partial = outputPath + ".partial." + Guid.NewGuid().ToString("N");
        try
        {
            using (FileStream stream = new FileStream(
                partial,
                FileMode.CreateNew,
                FileAccess.Write,
                FileShare.None))
            {
                stream.Write(bytes, 0, bytes.Length);
                stream.Flush(true);
            }
            File.Move(partial, outputPath);
        }
        finally
        {
            if (File.Exists(partial))
            {
                File.Delete(partial);
            }
        }
    }

    private static void Require(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException(message);
        }
    }
}
