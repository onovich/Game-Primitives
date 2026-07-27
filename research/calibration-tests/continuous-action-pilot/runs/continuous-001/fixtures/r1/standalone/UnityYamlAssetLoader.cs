// A deliberately narrow loader for the frozen Unity text assets used by CA-R1.
// It reconstructs data objects; transition semantics remain exclusively in the
// byte-identical frozen Fighter.cs and ActionData.cs compiled by the project.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using Footsies;
using UnityEngine;

internal static class UnityYamlAssetLoader
{
    private static readonly Regex RangePattern = new Regex(
        @"\{x: (?<x>-?[0-9]+), y: (?<y>-?[0-9]+)\}",
        RegexOptions.CultureInvariant);

    internal static FighterData LoadFighterData(string sourceRoot)
    {
        string fighterPath = FrozenSourceContract.Resolve(
            sourceRoot,
            FrozenSourceContract.ControlledAssetPath);
        string text = ReadNormalized(fighterPath);

        FighterData data = new FighterData
        {
            startGuardHealth = ReadInt(text, "startGuardHealth"),
            forwardMoveSpeed = ReadFloat(text, "forwardMoveSpeed"),
            backwardMoveSpeed = ReadFloat(text, "backwardMoveSpeed"),
            dashAllowFrame = ReadInt(text, "dashAllowFrame"),
            specialAttackHoldFrame = ReadInt(text, "specialAttackHoldFrame"),
            canCancelOnWhiff = ReadBool(text, FrozenSourceContract.ControlledField),
            baseHurtBoxRect = ReadTopLevelRect(text, "baseHurtBoxRect"),
            basePushBoxRect = ReadTopLevelRect(text, "basePushBoxRect"),
        };

        ActionData[] actions = Enum.GetValues(typeof(CommonActionID))
            .Cast<CommonActionID>()
            .Select(id => LoadAction(sourceRoot, id.ToString()))
            .ToArray();

        SetPrivateField(
            data,
            "actionDataContainer",
            new ActionDataContainer { actions = actions });
        SetPrivateField(
            data,
            "attackDataContainer",
            new AttackDataContainer { attackDataList = Array.Empty<AttackData>() });
        SetPrivateField(
            data,
            "motionDataContainer",
            new MotionDataContainer { motionDataList = Array.Empty<MotionData>() });
        data.setupDictionary();

        foreach (CommonActionID id in Enum.GetValues(typeof(CommonActionID)))
        {
            RequireAction(data, id, id.ToString());
        }
        return data;
    }

    private static ActionData LoadAction(string sourceRoot, string name)
    {
        string relativePath = "Assets/Fighter/F00/Actions/" + name + ".asset";
        string text = ReadNormalized(FrozenSourceContract.Resolve(sourceRoot, relativePath));
        ActionData result = new ActionData
        {
            actionID = ReadInt(text, "actionID"),
            actionName = ReadString(text, "actionName"),
            Type = (ActionType)ReadInt(text, "Type"),
            frameCount = ReadInt(text, "frameCount"),
            isLoop = ReadOptionalBool(text, "isLoop", false),
            loopFromFrame = ReadOptionalInt(text, "loopFromFrame", 0),
            motions = ReadItems(text, "motions").Select(ReadMotion).ToArray(),
            status = ReadItems(text, "status").Select(ReadStatus).ToArray(),
            hitboxes = ReadItems(text, "hitboxes").Select(ReadHitbox).ToArray(),
            hurtboxes = ReadItems(text, "hurtboxes").Select(ReadHurtbox).ToArray(),
            pushboxes = ReadItems(text, "pushboxes").Select(ReadPushbox).ToArray(),
            movements = ReadItems(text, "movements").Select(ReadMovement).ToArray(),
            cancels = ReadItems(text, "cancels").Select(ReadCancel).ToArray(),
            alwaysCancelable = ReadBool(text, "alwaysCancelable"),
            audioClip = HasNonNullObjectReference(text, "audioClip")
                ? new AudioClip()
                : null,
        };

        if (!StringComparer.Ordinal.Equals(result.actionName, name))
        {
            throw new InvalidDataException("Action asset name does not match its frozen path.");
        }

        return result;
    }

    private static MotionFrameData ReadMotion(IReadOnlyList<string> item)
    {
        return new MotionFrameData
        {
            startEndFrame = ReadRange(item[0]),
            motionID = ReadItemInt(item, "motionID"),
        };
    }

    private static StatusData ReadStatus(IReadOnlyList<string> item)
    {
        return new StatusData
        {
            startEndFrame = ReadRange(item[0]),
            counterHit = ReadItemBool(item, "counterHit"),
        };
    }

    private static HitboxData ReadHitbox(IReadOnlyList<string> item)
    {
        return new HitboxData
        {
            startEndFrame = ReadRange(item[0]),
            rect = ReadItemRect(item),
            attackID = ReadItemInt(item, "attackID"),
            proximity = ReadItemBool(item, "proximity"),
        };
    }

    private static HurtboxData ReadHurtbox(IReadOnlyList<string> item)
    {
        return new HurtboxData
        {
            startEndFrame = ReadRange(item[0]),
            rect = ReadItemRect(item),
            useBaseRect = ReadItemBool(item, "useBaseRect"),
        };
    }

    private static PushboxData ReadPushbox(IReadOnlyList<string> item)
    {
        return new PushboxData
        {
            startEndFrame = ReadRange(item[0]),
            rect = ReadItemRect(item),
            useBaseRect = ReadItemBool(item, "useBaseRect"),
        };
    }

    private static MovementData ReadMovement(IReadOnlyList<string> item)
    {
        return new MovementData
        {
            startEndFrame = ReadRange(item[0]),
            velocity_x = ReadItemFloat(item, "velocity_x"),
        };
    }

    private static CancelData ReadCancel(IReadOnlyList<string> item)
    {
        return new CancelData
        {
            startEndFrame = ReadRange(item[0]),
            buffer = ReadItemBool(item, "buffer"),
            execute = ReadItemBool(item, "execute"),
            actionID = new List<int>
            {
                ReadLittleEndianInt32(ReadItemString(item, "actionID")),
            },
        };
    }

    private static IReadOnlyList<IReadOnlyList<string>> ReadItems(
        string text,
        string sectionName)
    {
        string[] lines = text.Split('\n');
        int start = Array.FindIndex(
            lines,
            line => StringComparer.Ordinal.Equals(line, "  " + sectionName + ":")
                || StringComparer.Ordinal.Equals(line, "  " + sectionName + ": []"));
        if (start < 0)
        {
            throw new InvalidDataException("Missing Unity YAML section: " + sectionName);
        }
        if (lines[start].EndsWith(": []", StringComparison.Ordinal))
        {
            return Array.Empty<IReadOnlyList<string>>();
        }

        int end = start + 1;
        while (end < lines.Length)
        {
            string line = lines[end];
            if (Regex.IsMatch(line, @"^  [A-Za-z_][A-Za-z0-9_]*:"))
            {
                break;
            }
            end++;
        }

        List<IReadOnlyList<string>> items = new List<IReadOnlyList<string>>();
        int cursor = start + 1;
        while (cursor < end)
        {
            if (!lines[cursor].StartsWith("  - startEndFrame:", StringComparison.Ordinal))
            {
                throw new InvalidDataException(
                    "Unexpected Unity YAML list line in " + sectionName + ": " + lines[cursor]);
            }

            int next = cursor + 1;
            while (next < end
                && !lines[next].StartsWith("  - startEndFrame:", StringComparison.Ordinal))
            {
                next++;
            }
            items.Add(lines[cursor..next]);
            cursor = next;
        }

        return items;
    }

    private static Rect ReadTopLevelRect(string text, string property)
    {
        string pattern =
            "^  "
            + Regex.Escape(property)
            + @":\n"
            + @"    serializedVersion: 2\n"
            + @"    x: (?<x>-?[0-9]+(?:\.[0-9]+)?)\n"
            + @"    y: (?<y>-?[0-9]+(?:\.[0-9]+)?)\n"
            + @"    width: (?<width>-?[0-9]+(?:\.[0-9]+)?)\n"
            + @"    height: (?<height>-?[0-9]+(?:\.[0-9]+)?)$";
        Match match = RequireSingleMatch(text, pattern, RegexOptions.Multiline);
        return RectFromMatch(match);
    }

    private static Rect ReadItemRect(IReadOnlyList<string> item)
    {
        string text = String.Join("\n", item);
        string pattern =
            @"^    rect:\n"
            + @"      serializedVersion: 2\n"
            + @"      x: (?<x>-?[0-9]+(?:\.[0-9]+)?)\n"
            + @"      y: (?<y>-?[0-9]+(?:\.[0-9]+)?)\n"
            + @"      width: (?<width>-?[0-9]+(?:\.[0-9]+)?)\n"
            + @"      height: (?<height>-?[0-9]+(?:\.[0-9]+)?)$";
        Match match = RequireSingleMatch(text, pattern, RegexOptions.Multiline);
        return RectFromMatch(match);
    }

    private static Rect RectFromMatch(Match match)
    {
        return new Rect
        {
            x = ParseFloat(match.Groups["x"].Value),
            y = ParseFloat(match.Groups["y"].Value),
            width = ParseFloat(match.Groups["width"].Value),
            height = ParseFloat(match.Groups["height"].Value),
        };
    }

    private static Vector2Int ReadRange(string line)
    {
        Match match = RangePattern.Match(line);
        if (!match.Success)
        {
            throw new InvalidDataException("Invalid start/end frame range: " + line);
        }
        return new Vector2Int(
            Int32.Parse(match.Groups["x"].Value, CultureInfo.InvariantCulture),
            Int32.Parse(match.Groups["y"].Value, CultureInfo.InvariantCulture));
    }

    private static int ReadLittleEndianInt32(string serialized)
    {
        if (!Regex.IsMatch(serialized, "^[0-9a-f]{8}$", RegexOptions.CultureInvariant))
        {
            throw new InvalidDataException(
                "Expected a four-byte lower-case Unity integer encoding.");
        }
        byte[] bytes = Convert.FromHexString(serialized);
        if (!BitConverter.IsLittleEndian)
        {
            Array.Reverse(bytes);
        }
        return BitConverter.ToInt32(bytes, 0);
    }

    private static int ReadItemInt(IReadOnlyList<string> item, string property)
    {
        return Int32.Parse(ReadItemString(item, property), CultureInfo.InvariantCulture);
    }

    private static float ReadItemFloat(IReadOnlyList<string> item, string property)
    {
        return ParseFloat(ReadItemString(item, property));
    }

    private static bool ReadItemBool(IReadOnlyList<string> item, string property)
    {
        return ParseBool(ReadItemString(item, property));
    }

    private static string ReadItemString(IReadOnlyList<string> item, string property)
    {
        string prefix = "    " + property + ": ";
        string[] matches = item
            .Where(line => line.StartsWith(prefix, StringComparison.Ordinal))
            .Select(line => line.Substring(prefix.Length))
            .ToArray();
        if (matches.Length != 1)
        {
            throw new InvalidDataException(
                "Expected one item property " + property + ", found " + matches.Length + ".");
        }
        return matches[0];
    }

    private static string ReadString(string text, string property)
    {
        Match match = RequireSingleMatch(
            text,
            "^  " + Regex.Escape(property) + @": (?<value>[^\n]*)$",
            RegexOptions.Multiline);
        return match.Groups["value"].Value;
    }

    private static int ReadInt(string text, string property)
    {
        return Int32.Parse(ReadString(text, property), CultureInfo.InvariantCulture);
    }

    private static int ReadOptionalInt(string text, string property, int fallback)
    {
        MatchCollection matches = Regex.Matches(
            text,
            "^  " + Regex.Escape(property) + @": (?<value>-?[0-9]+)$",
            RegexOptions.Multiline);
        if (matches.Count == 0)
        {
            return fallback;
        }
        if (matches.Count != 1)
        {
            throw new InvalidDataException("Duplicate Unity YAML property: " + property);
        }
        return Int32.Parse(matches[0].Groups["value"].Value, CultureInfo.InvariantCulture);
    }

    private static float ReadFloat(string text, string property)
    {
        return ParseFloat(ReadString(text, property));
    }

    private static bool ReadBool(string text, string property)
    {
        return ParseBool(ReadString(text, property));
    }

    private static bool ReadOptionalBool(string text, string property, bool fallback)
    {
        MatchCollection matches = Regex.Matches(
            text,
            "^  " + Regex.Escape(property) + @": (?<value>[01])$",
            RegexOptions.Multiline);
        if (matches.Count == 0)
        {
            return fallback;
        }
        if (matches.Count != 1)
        {
            throw new InvalidDataException("Duplicate Unity YAML property: " + property);
        }
        return ParseBool(matches[0].Groups["value"].Value);
    }

    private static bool HasNonNullObjectReference(string text, string property)
    {
        Match match = RequireSingleMatch(
            text,
            "^  " + Regex.Escape(property) + @": \{fileID: (?<fileID>-?[0-9]+)[^}]*\}$",
            RegexOptions.Multiline,
            allowMissing: true);
        return match != null
            && !StringComparer.Ordinal.Equals(match.Groups["fileID"].Value, "0");
    }

    private static bool ParseBool(string value)
    {
        if (StringComparer.Ordinal.Equals(value, "0"))
        {
            return false;
        }
        if (StringComparer.Ordinal.Equals(value, "1"))
        {
            return true;
        }
        throw new InvalidDataException("Expected Unity boolean 0 or 1.");
    }

    private static float ParseFloat(string value)
    {
        return Single.Parse(value, NumberStyles.Float, CultureInfo.InvariantCulture);
    }

    private static Match RequireSingleMatch(
        string text,
        string pattern,
        RegexOptions options,
        bool allowMissing = false)
    {
        MatchCollection matches = Regex.Matches(text, pattern, options);
        if (allowMissing && matches.Count == 0)
        {
            return null;
        }
        if (matches.Count != 1)
        {
            throw new InvalidDataException(
                "Expected exactly one frozen asset match, found " + matches.Count + ".");
        }
        return matches[0];
    }

    private static string ReadNormalized(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        string text = System.Text.Encoding.UTF8.GetString(bytes);
        if (text.IndexOf('\0') >= 0)
        {
            throw new InvalidDataException("Unity text asset contained a NUL byte.");
        }
        return text.Replace("\r\n", "\n");
    }

    private static void SetPrivateField(object target, string fieldName, object value)
    {
        FieldInfo field = target.GetType().GetField(
            fieldName,
            BindingFlags.Instance | BindingFlags.NonPublic);
        if (field == null)
        {
            throw new MissingFieldException(target.GetType().FullName, fieldName);
        }
        field.SetValue(target, value);
    }

    private static void RequireAction(
        FighterData data,
        CommonActionID expectedId,
        string expectedName)
    {
        int id = (int)expectedId;
        if (!data.actions.TryGetValue(id, out ActionData action)
            || !StringComparer.Ordinal.Equals(action.actionName, expectedName))
        {
            throw new InvalidDataException(
                "Frozen action projection is missing " + expectedName + ".");
        }
    }
}
