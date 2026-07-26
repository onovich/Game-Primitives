using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using Footsies;
using UnityEditor;
using UnityEngine;

namespace GamePrimitives
{
    public static class ContinuousActionR1
    {
        [Serializable]
        private sealed class Scalar
        {
            public string serialized_value;
            public string unit;
            public string value_type;
        }

        [Serializable]
        private sealed class InputField
        {
            public string field_id;
            public Scalar value;
        }

        [Serializable]
        private sealed class InputEvent
        {
            public Scalar at;
            public string event_id;
            public InputField[] fields;
            public int sequence_index;
        }

        [Serializable]
        private sealed class FormalInput
        {
            public string artifact_type;
            public string artifact_version;
            public string case_id;
            public string formal_input_id;
            public InputEvent[] input_events;
            public string run_id;
            public string stop_boundary_id;
        }

        [Serializable]
        private sealed class TraceEntry
        {
            public int after_action_frame;
            public int after_action_id;
            public int after_buffer_action_id;
            public int attack_held;
            public int before_action_frame;
            public int before_action_id;
            public int before_buffer_action_id;
            public int cancel_eligible_before;
            public int contact_count;
            public string event_id;
            public int hit_count;
            public int input_down;
            public int input_value;
            public int sequence_index;
        }

        [Serializable]
        private sealed class TraceBundle
        {
            public string artifact_type;
            public string case_id;
            public string configuration_id;
            public int controlled_value;
            public string execution_permit_sha256;
            public string formal_input_id;
            public string formal_input_sha256;
            public int invariant_first_request_recognized;
            public int invariant_second_request_buffered;
            public int invariant_zero_contacts;
            public int invariant_zero_hits;
            public string prediction_set_digest;
            public string run_id;
            public string stop_boundary_id;
            public TraceEntry[] trace_entries;
        }

        private static readonly BindingFlags PrivateInstance =
            BindingFlags.Instance | BindingFlags.NonPublic;

        public static void Run()
        {
            var createdObjects = new List<GameObject>();
            try
            {
                var runId = RequireEnvironment("GAME_PRIMITIVES_RUN_ID");
                var caseId = RequireEnvironment("GAME_PRIMITIVES_CASE_ID");
                var executionPermitSha = RequireLowercaseNonzeroSha256(
                    "GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256"
                );
                var predictionSetDigest = RequireLowercaseNonzeroSha256(
                    "GAME_PRIMITIVES_PREDICTION_SET_DIGEST"
                );
                var expectedInputSha = RequireLowercaseNonzeroSha256(
                    "GAME_PRIMITIVES_FORMAL_INPUT_SHA256"
                );
                Require(runId == "continuous-001", "execution permit has an unexpected run_id");
                Require(caseId == "CA-R1", "execution permit has an unexpected case_id");

                var inputPath = RequireEnvironment("GP_R1_INPUT_PATH");
                var outputPath = RequireEnvironment("GP_R1_OUTPUT_PATH");
                var configurationId = RequireEnvironment("GP_R1_CONFIGURATION_ID");

                var inputBytes = File.ReadAllBytes(inputPath);
                var actualInputSha = Sha256(inputBytes);
                Require(
                    actualInputSha == expectedInputSha,
                    "formal input SHA-256 does not match the frozen execution plan"
                );

                var formalInput = JsonUtility.FromJson<FormalInput>(Encoding.UTF8.GetString(inputBytes));
                Require(formalInput != null, "formal input did not deserialize");
                Require(formalInput.artifact_type == "formal_input_trace", "unexpected input artifact_type");
                Require(formalInput.artifact_version == "0.1.0", "unexpected input artifact_version");
                Require(formalInput.case_id == caseId, "formal input case_id does not match the execution permit");
                Require(formalInput.run_id == runId, "formal input run_id does not match the execution permit");
                Require(formalInput.input_events != null && formalInput.input_events.Length == 7, "expected seven fixture updates");

                CreateSilentSoundManager(createdObjects);

                var fighterData = AssetDatabase.LoadAssetAtPath<FighterData>(
                    "Assets/Fighter/F00/F00.asset"
                );
                Require(fighterData != null, "could not load frozen F00 asset");
                fighterData.setupDictionary();

                var expectedControlledValue = configurationId == "config.baseline" ? 0 :
                    configurationId == "config.variant" ? 1 : -1;
                Require(expectedControlledValue >= 0, "unknown configuration_id");
                Require(
                    (fighterData.canCancelOnWhiff ? 1 : 0) == expectedControlledValue,
                    "controlled asset value does not match configuration_id"
                );

                var fighter = new Fighter();
                var opponent = new Fighter();
                fighter.SetupBattleStart(fighterData, new Vector2(0f, 0f), true);
                opponent.SetupBattleStart(fighterData, new Vector2(1000f, 0f), false);

                var entries = new List<TraceEntry>();
                for (var index = 0; index < formalInput.input_events.Length; index++)
                {
                    var inputEvent = formalInput.input_events[index];
                    Require(inputEvent.sequence_index == index, "input sequence_index is not contiguous");
                    Require(ParseInteger(inputEvent.at) == index, "input time does not match sequence_index");

                    var attackHeld = ParseBoolean(FindField(inputEvent, "input.attack-held"));
                    var horizontal = ParseInteger(FindField(inputEvent, "input.horizontal"));
                    Require(horizontal >= -1 && horizontal <= 1, "horizontal input is outside the digital range");

                    var inputValue = attackHeld ? (int)InputDefine.Attack : (int)InputDefine.None;
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

                    var entry = new TraceEntry();
                    entry.attack_held = attackHeld ? 1 : 0;
                    entry.before_action_frame = fighter.currentActionFrame;
                    entry.before_action_id = fighter.currentActionID;
                    entry.before_buffer_action_id = ReadPrivateInt(fighter, "bufferActionID");
                    entry.cancel_eligible_before = InvokePrivateBool(fighter, "canCancelAttack") ? 1 : 0;
                    entry.event_id = inputEvent.event_id;
                    entry.input_down = ReadInputDown(fighter);
                    entry.input_value = inputValue;
                    entry.sequence_index = index;

                    fighter.UpdateActionRequest();
                    opponent.UpdateActionRequest();
                    fighter.UpdateMovement();
                    opponent.UpdateMovement();
                    fighter.UpdateBoxes();
                    opponent.UpdateBoxes();

                    entry.after_action_frame = fighter.currentActionFrame;
                    entry.after_action_id = fighter.currentActionID;
                    entry.after_buffer_action_id = ReadPrivateInt(fighter, "bufferActionID");
                    entry.contact_count = CountContacts(fighter, opponent);
                    entry.hit_count = fighter.currentActionHitCount;
                    entries.Add(entry);
                }

                var zeroContacts = AllEqual(entries, "contact_count", 0);
                var zeroHits = AllEqual(entries, "hit_count", 0);
                var firstRecognized = entries[0].after_action_id == (int)CommonActionID.N_ATTACK;
                var secondBuffered = entries[2].after_buffer_action_id == (int)CommonActionID.N_SPECIAL;

                Require(zeroContacts, "contact invariant failed");
                Require(zeroHits, "hit-count invariant failed");
                Require(firstRecognized, "first request recognition invariant failed");
                Require(secondBuffered, "second request buffering invariant failed");

                var bundle = new TraceBundle();
                bundle.artifact_type = "ca_r1_raw_trace";
                bundle.case_id = formalInput.case_id;
                bundle.configuration_id = configurationId;
                bundle.controlled_value = expectedControlledValue;
                bundle.execution_permit_sha256 = executionPermitSha;
                bundle.formal_input_id = formalInput.formal_input_id;
                bundle.formal_input_sha256 = actualInputSha;
                bundle.invariant_first_request_recognized = firstRecognized ? 1 : 0;
                bundle.invariant_second_request_buffered = secondBuffered ? 1 : 0;
                bundle.invariant_zero_contacts = zeroContacts ? 1 : 0;
                bundle.invariant_zero_hits = zeroHits ? 1 : 0;
                bundle.prediction_set_digest = predictionSetDigest;
                bundle.run_id = runId;
                bundle.stop_boundary_id = formalInput.stop_boundary_id;
                bundle.trace_entries = entries.ToArray();

                var outputDirectory = Path.GetDirectoryName(outputPath);
                if (!String.IsNullOrEmpty(outputDirectory))
                {
                    Directory.CreateDirectory(outputDirectory);
                }
                File.WriteAllText(
                    outputPath,
                    JsonUtility.ToJson(bundle, false) + "\n",
                    new UTF8Encoding(false)
                );
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine(exception.ToString());
                EditorApplication.Exit(1);
            }
            finally
            {
                for (var index = createdObjects.Count - 1; index >= 0; index--)
                {
                    if (createdObjects[index] != null)
                    {
                        UnityEngine.Object.DestroyImmediate(createdObjects[index]);
                    }
                }
            }
        }

        private static bool AllEqual(List<TraceEntry> entries, string fieldName, int expected)
        {
            var field = typeof(TraceEntry).GetField(fieldName);
            Require(field != null, "unknown trace field");
            for (var index = 0; index < entries.Count; index++)
            {
                if ((int)field.GetValue(entries[index]) != expected)
                {
                    return false;
                }
            }
            return true;
        }

        private static int CountContacts(Fighter fighter, Fighter opponent)
        {
            var count = 0;
            for (var hitIndex = 0; hitIndex < fighter.hitboxes.Count; hitIndex++)
            {
                var hitbox = fighter.hitboxes[hitIndex];
                if (hitbox.proximity)
                {
                    continue;
                }
                for (var hurtIndex = 0; hurtIndex < opponent.hurtboxes.Count; hurtIndex++)
                {
                    if (hitbox.Overlaps(opponent.hurtboxes[hurtIndex]))
                    {
                        count++;
                    }
                }
            }
            return count;
        }

        private static void CreateSilentSoundManager(List<GameObject> createdObjects)
        {
            var managerObject = new GameObject("GamePrimitives-R1-SoundManager");
            var sourceObject1 = new GameObject("GamePrimitives-R1-SE1");
            var sourceObject2 = new GameObject("GamePrimitives-R1-SE2");
            var bgmObject = new GameObject("GamePrimitives-R1-BGM");
            createdObjects.Add(managerObject);
            createdObjects.Add(sourceObject1);
            createdObjects.Add(sourceObject2);
            createdObjects.Add(bgmObject);

            var manager = managerObject.AddComponent<SoundManager>();
            var source1 = sourceObject1.AddComponent<AudioSource>();
            var source2 = sourceObject2.AddComponent<AudioSource>();
            var bgm = bgmObject.AddComponent<AudioSource>();
            manager.seSourceObject1 = sourceObject1;
            manager.seSourceObject2 = sourceObject2;
            manager.bgmSourceObject = bgmObject;
            WritePrivateField(manager, "seSource1", source1);
            WritePrivateField(manager, "seSource2", source2);
            WritePrivateField(manager, "bgmSource", bgm);
        }

        private static Scalar FindField(InputEvent inputEvent, string fieldId)
        {
            Require(inputEvent.fields != null, "input event has no fields");
            for (var index = 0; index < inputEvent.fields.Length; index++)
            {
                if (inputEvent.fields[index].field_id == fieldId)
                {
                    return inputEvent.fields[index].value;
                }
            }
            throw new InvalidOperationException("missing input field: " + fieldId);
        }

        private static bool InvokePrivateBool(object target, string methodName)
        {
            var method = target.GetType().GetMethod(methodName, PrivateInstance);
            Require(method != null, "missing private method: " + methodName);
            return (bool)method.Invoke(target, null);
        }

        private static bool ParseBoolean(Scalar scalar)
        {
            Require(scalar != null && scalar.value_type == "boolean", "expected boolean scalar");
            bool value;
            Require(Boolean.TryParse(scalar.serialized_value, out value), "invalid boolean scalar");
            return value;
        }

        private static int ParseInteger(Scalar scalar)
        {
            Require(scalar != null && scalar.value_type == "integer", "expected integer scalar");
            int value;
            Require(Int32.TryParse(scalar.serialized_value, out value), "invalid integer scalar");
            return value;
        }

        private static int ReadInputDown(Fighter fighter)
        {
            var field = typeof(Fighter).GetField("inputDown", PrivateInstance);
            Require(field != null, "missing inputDown field");
            var values = (int[])field.GetValue(fighter);
            Require(values != null && values.Length > 0, "inputDown is empty");
            return values[0];
        }

        private static int ReadPrivateInt(object target, string fieldName)
        {
            var field = target.GetType().GetField(fieldName, PrivateInstance);
            Require(field != null, "missing private field: " + fieldName);
            return (int)field.GetValue(target);
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
            {
                throw new InvalidOperationException(message);
            }
        }

        private static string RequireEnvironment(string name)
        {
            var value = Environment.GetEnvironmentVariable(name);
            Require(!String.IsNullOrEmpty(value), "missing environment variable: " + name);
            return value;
        }

        private static string RequireLowercaseNonzeroSha256(string environmentName)
        {
            var value = RequireEnvironment(environmentName);
            Require(
                value.Length == 64,
                environmentName + " must contain exactly 64 lowercase hexadecimal characters"
            );
            var hasNonzeroDigit = false;
            for (var index = 0; index < value.Length; index++)
            {
                var character = value[index];
                Require(
                    (character >= '0' && character <= '9') ||
                        (character >= 'a' && character <= 'f'),
                    environmentName + " must contain only lowercase hexadecimal characters"
                );
                if (character != '0')
                {
                    hasNonzeroDigit = true;
                }
            }
            Require(hasNonzeroDigit, environmentName + " must not be the all-zero digest");
            return value;
        }

        private static string Sha256(byte[] bytes)
        {
            using (var algorithm = SHA256.Create())
            {
                var hash = algorithm.ComputeHash(bytes);
                var builder = new StringBuilder(hash.Length * 2);
                for (var index = 0; index < hash.Length; index++)
                {
                    builder.Append(hash[index].ToString("x2"));
                }
                return builder.ToString();
            }
        }

        private static void WritePrivateField(object target, string fieldName, object value)
        {
            var field = target.GetType().GetField(fieldName, PrivateInstance);
            Require(field != null, "missing private field: " + fieldName);
            field.SetValue(target, value);
        }
    }
}
