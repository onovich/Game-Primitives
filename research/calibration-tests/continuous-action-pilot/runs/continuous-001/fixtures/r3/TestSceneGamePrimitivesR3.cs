// Copyright (c) ppy Pty Ltd <contact@ppy.sh>. Licensed under the MIT Licence.
// See the LICENCE file in the ppy/osu repository root for full licence text.
//
// Additive observation patch for Game Primitives continuous-001 / CA-R3.
// This test body must not run without a verified post-prediction permit.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text.Json;
using NUnit.Framework;
using osu.Framework.Graphics;
using osu.Framework.Input.Events;
using osu.Framework.Timing;
using osu.Game.Beatmaps;
using osu.Game.Beatmaps.ControlPoints;
using osu.Game.Rulesets.Judgements;
using osu.Game.Rulesets.Osu.Configuration;
using osu.Game.Rulesets.Osu.Objects;
using osu.Game.Rulesets.Osu.Objects.Drawables;
using osu.Game.Rulesets.Scoring;
using osu.Game.Skinning;
using osu.Game.Tests.Visual;
using osuTK;

namespace osu.Game.Rulesets.Osu.Tests
{
    public partial class TestSceneGamePrimitivesR3 : OsuManualInputManagerTestScene
    {
        private const double object_start_time = 1000;

        private static readonly JsonSerializerOptions json_options = new JsonSerializerOptions
        {
            WriteIndented = true
        };

        private readonly List<SortedDictionary<string, object?>> eventTrace = new List<SortedDictionary<string, object?>>();

        private ManualClock manualClock = null!;
        private HitCircle hitCircle = null!;
        private DrawableHitCircle drawableHitCircle = null!;
        private DrawableHitCircle.HitReceptor hitArea = null!;
        private ScoreProcessor scoreProcessor = null!;
        private Action productionHit = null!;
        private Func<bool> productionCanBeHit = null!;
        private Action? pendingAdjudication;

        private string configurationId = string.Empty;
        private string outputPath = string.Empty;
        private string executionPermitSha256 = string.Empty;
        private string formalInputSha256 = string.Empty;
        private string predictionSetDigest = string.Empty;
        private int adjudicationDelayMs;
        private bool hitAnimations;

        private bool candidateAccepted;
        private bool reentryAllowedAfterCandidate;
        private bool reentryAllowedAtNotification;
        private double candidateTime;
        private double adjudicationTime;
        private double notificationTime;
        private double scoringNotificationTime;
        private double? rawTime;
        private double? reentryClosedTime;
        private string result = string.Empty;
        private int notificationCount;
        private int scoringNotificationCount;

        [Test]
        public void TestFormalAdjudicationSchedule()
        {
            readAndValidateEnvironment();

            AddStep("create deterministic single-circle fixture", createFixture);
            AddStep("move pointer to the candidate centre", () => InputManager.MoveMouseTo(hitArea.ScreenSpaceDrawQuad.Centre));
            AddStep("submit exactly one candidate at T", submitCandidate);
            AddStep("advance deterministic clock and adjudicate", advanceAndAdjudicate);
            AddUntilStep("wait for one result notification", () => notificationCount == 1 && scoringNotificationCount == 1);
            AddStep("write one machine-readable trace", writeTrace);
        }

        private void readAndValidateEnvironment()
        {
            string runId = requireEnvironment("GAME_PRIMITIVES_RUN_ID");
            string caseId = requireEnvironment("GAME_PRIMITIVES_CASE_ID");
            if (!string.Equals(runId, "continuous-001", StringComparison.Ordinal)
                || !string.Equals(caseId, "CA-R3", StringComparison.Ordinal))
            {
                throw new InvalidOperationException("CA-R3 formal test body received the wrong run or case id.");
            }

            executionPermitSha256 = requireEnvironment("GAME_PRIMITIVES_EXECUTION_PERMIT_SHA256");
            formalInputSha256 = requireEnvironment("GAME_PRIMITIVES_FORMAL_INPUT_SHA256");
            predictionSetDigest = requireEnvironment("GAME_PRIMITIVES_PREDICTION_SET_DIGEST");
            if (!isLowerNonZeroSha256(executionPermitSha256)
                || !isLowerNonZeroSha256(formalInputSha256)
                || !isLowerNonZeroSha256(predictionSetDigest))
            {
                throw new InvalidOperationException("CA-R3 formal test body requires three lowercase, non-zero SHA-256 digests.");
            }

            configurationId = requireEnvironment("GAME_PRIMITIVES_R3_CONFIGURATION_ID");
            outputPath = Path.GetFullPath(requireEnvironment("GAME_PRIMITIVES_R3_OUTPUT_PATH"));

            if (File.Exists(outputPath))
                throw new InvalidOperationException($"Refusing to overwrite an existing trace: {outputPath}");

            string delayText = requireEnvironment("GAME_PRIMITIVES_R3_ADJUDICATION_DELAY_MS");
            if (!int.TryParse(delayText, NumberStyles.None, CultureInfo.InvariantCulture, out adjudicationDelayMs)
                || (adjudicationDelayMs != 0 && adjudicationDelayMs != 75))
            {
                throw new InvalidOperationException("Adjudication delay must be exactly 0 or 75 ms.");
            }

            string animationText = requireEnvironment("GAME_PRIMITIVES_R3_HIT_ANIMATIONS");
            if (!bool.TryParse(animationText, out hitAnimations))
                throw new InvalidOperationException("HitAnimations must be exactly true or false.");

            bool validConfiguration = configurationId switch
            {
                "config.baseline" => adjudicationDelayMs == 0 && hitAnimations,
                "config.variant" => adjudicationDelayMs == 75 && hitAnimations,
                "negative_control_a" => adjudicationDelayMs == 0 && hitAnimations,
                "negative_control_b" => adjudicationDelayMs == 0 && !hitAnimations,
                _ => false
            };

            if (!validConfiguration)
                throw new InvalidOperationException("Configuration id, adjudication delay, and HitAnimations do not form an allowed locked tuple.");
        }

        private void createFixture()
        {
            eventTrace.Clear();

            var ruleset = new OsuRuleset();
            var config = RulesetConfigs.GetConfigFor(ruleset) as OsuRulesetConfigManager
                         ?? throw new InvalidOperationException("Expected an osu! ruleset configuration manager.");
            config.SetValue(OsuRulesetSetting.HitAnimations, hitAnimations);

            var difficulty = new BeatmapDifficulty
            {
                OverallDifficulty = 5
            };

            hitCircle = new HitCircle
            {
                Position = new Vector2(256, 192),
                StartTime = object_start_time
            };
            hitCircle.ApplyDefaults(new ControlPointInfo(), difficulty);

            var beatmap = new Beatmap
            {
                Difficulty = difficulty,
                HitObjects = { hitCircle }
            };

            scoreProcessor = new ScoreProcessor(ruleset);
            scoreProcessor.ApplyBeatmap(beatmap);
            scoreProcessor.NewJudgement += _ =>
            {
                scoringNotificationCount++;
                scoringNotificationTime = drawableHitCircle.Time.Current;
                appendEvent("scoring_notification", scoringNotificationTime);
            };

            manualClock = new ManualClock
            {
                CurrentTime = 0,
                Rate = 1
            };

            drawableHitCircle = new DrawableHitCircle(hitCircle)
            {
                Clock = new FramedClock(manualClock)
            };

            Child = new SkinProvidingContainer(new TrianglesSkin(null!))
            {
                RelativeSizeAxes = Axes.Both,
                Child = drawableHitCircle
            };

            drawableHitCircle.UpdateSubTree();
            hitArea = drawableHitCircle.HitArea;
            productionHit = hitArea.Hit;
            productionCanBeHit = hitArea.CanBeHit;

            drawableHitCircle.OnNewResult += (_, judgementResult) =>
            {
                notificationCount++;
                notificationTime = drawableHitCircle.Time.Current;
                rawTime = readRawTime(judgementResult);
                result = judgementResult.Type.ToString();
                reentryAllowedAtNotification = productionCanBeHit();
                appendEvent("result_notification", notificationTime);

                scoreProcessor.ApplyResult(judgementResult);
            };

            hitArea.Hit = () =>
            {
                if (pendingAdjudication != null)
                    throw new InvalidOperationException("The single candidate attempted to schedule adjudication more than once.");

                if (adjudicationDelayMs == 0)
                    performAdjudication();
                else
                    pendingAdjudication = performAdjudication;
            };
        }

        private void submitCandidate()
        {
            manualClock.CurrentTime = object_start_time;
            drawableHitCircle.UpdateSubTree();

            candidateTime = drawableHitCircle.Time.Current;
            appendEvent("candidate", candidateTime);

            candidateAccepted = hitArea.OnPressed(
                new KeyBindingPressEvent<OsuAction>(
                    GetContainingInputManager()!.CurrentState,
                    OsuAction.LeftButton));

            reentryAllowedAfterCandidate = productionCanBeHit();

            if (!candidateAccepted)
                throw new InvalidOperationException("The fixed centre candidate was not accepted.");
        }

        private void advanceAndAdjudicate()
        {
            manualClock.CurrentTime = object_start_time + adjudicationDelayMs;
            drawableHitCircle.UpdateSubTree();

            if (adjudicationDelayMs == 0)
            {
                if (pendingAdjudication != null)
                    throw new InvalidOperationException("Immediate configuration unexpectedly retained pending adjudication.");
                return;
            }

            Action adjudication = pendingAdjudication
                                  ?? throw new InvalidOperationException("Delayed configuration did not retain adjudication.");
            pendingAdjudication = null;
            adjudication();
        }

        private void performAdjudication()
        {
            adjudicationTime = drawableHitCircle.Time.Current;
            appendEvent("adjudication", adjudicationTime);

            productionHit();

            if (!productionCanBeHit())
            {
                reentryClosedTime = drawableHitCircle.Time.Current;
                appendEvent("reentry_closed", reentryClosedTime.Value);
            }
        }

        private void writeTrace()
        {
            if (notificationCount != 1 || scoringNotificationCount != 1)
                throw new InvalidOperationException("Expected exactly one result notification and one scoring notification.");
            if (!drawableHitCircle.Judged || productionCanBeHit())
                throw new InvalidOperationException("Result commitment did not close re-entry.");
            if (rawTime == null || reentryClosedTime == null)
                throw new InvalidOperationException("RawTime or re-entry closure was not observed.");

            var trace = new SortedDictionary<string, object?>
            {
                ["artifact_type"] = "continuous_action_r3_trace",
                ["artifact_version"] = "0.1.0",
                ["case_id"] = "CA-R3",
                ["configuration_id"] = configurationId,
                ["execution_permit_sha256"] = executionPermitSha256,
                ["formal_input_sha256"] = formalInputSha256,
                ["input"] = new SortedDictionary<string, object?>
                {
                    ["adjudication_delay_ms"] = adjudicationDelayMs,
                    ["candidate_count"] = 1,
                    ["candidate_time_ms"] = object_start_time,
                    ["hit_animations"] = hitAnimations,
                    ["object_start_time_ms"] = object_start_time,
                    ["overall_difficulty"] = 5
                },
                ["observation"] = new SortedDictionary<string, object?>
                {
                    ["adjudication_time_ms"] = adjudicationTime,
                    ["candidate_accepted"] = candidateAccepted,
                    ["candidate_time_ms"] = candidateTime,
                    ["event_trace"] = eventTrace,
                    ["hit_action"] = hitArea.HitAction?.ToString(),
                    ["judged"] = drawableHitCircle.Judged,
                    ["notification_count"] = notificationCount,
                    ["notification_time_ms"] = notificationTime,
                    ["production_can_be_hit_after_result"] = productionCanBeHit(),
                    ["production_delegate_method"] = $"{productionHit.Method.DeclaringType?.FullName}.{productionHit.Method.Name}",
                    ["production_delegate_target_type"] = productionHit.Target?.GetType().FullName,
                    ["raw_time_ms"] = rawTime,
                    ["reentry_allowed_after_candidate"] = reentryAllowedAfterCandidate,
                    ["reentry_allowed_at_notification"] = reentryAllowedAtNotification,
                    ["reentry_closed_time_ms"] = reentryClosedTime,
                    ["result"] = result,
                    ["score_combo"] = scoreProcessor.Combo.Value,
                    ["score_judged_hits"] = scoreProcessor.JudgedHits,
                    ["score_notification_count"] = scoringNotificationCount,
                    ["score_notification_time_ms"] = scoringNotificationTime,
                    ["score_total"] = scoreProcessor.TotalScore.Value,
                    ["time_offset_ms"] = drawableHitCircle.Result.TimeOffset
                },
                ["prediction_set_digest"] = predictionSetDigest,
                ["run_id"] = "continuous-001",
                ["window_snapshot_ms"] = new SortedDictionary<string, object?>
                {
                    ["great"] = hitCircle.HitWindows.WindowFor(HitResult.Great),
                    ["meh"] = hitCircle.HitWindows.WindowFor(HitResult.Meh),
                    ["ok"] = hitCircle.HitWindows.WindowFor(HitResult.Ok)
                }
            };

            string? directory = Path.GetDirectoryName(outputPath);
            if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
                throw new InvalidOperationException($"Trace output directory does not exist: {directory}");

            File.WriteAllText(
                outputPath,
                JsonSerializer.Serialize(trace, json_options) + "\n");
        }

        private void appendEvent(string eventName, double time)
        {
            eventTrace.Add(new SortedDictionary<string, object?>
            {
                ["event"] = eventName,
                ["ordinal"] = eventTrace.Count,
                ["time_ms"] = time
            });
        }

        private static double? readRawTime(JudgementResult result)
        {
            PropertyInfo property = typeof(JudgementResult).GetProperty(
                                        "RawTime",
                                        BindingFlags.Instance | BindingFlags.NonPublic)
                                    ?? throw new InvalidOperationException("JudgementResult.RawTime was not found.");

            return (double?)property.GetValue(result);
        }

        private static bool isLowerNonZeroSha256(string value)
        {
            if (value.Length != 64)
                return false;

            bool nonZero = false;
            foreach (char character in value)
            {
                if (!((character >= '0' && character <= '9')
                      || (character >= 'a' && character <= 'f')))
                {
                    return false;
                }

                if (character != '0')
                    nonZero = true;
            }

            return nonZero;
        }

        private static string requireEnvironment(string name)
            => Environment.GetEnvironmentVariable(name)
               ?? throw new InvalidOperationException($"Required environment variable is missing: {name}");
    }
}
