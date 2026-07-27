using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;

internal static class FrozenSourceContract
{
    internal const string Commit = "7eaaad799bb7912625c15af9407c2c67e6305d75";
    internal const string BaselineConfiguration = "config.baseline";
    internal const string VariantConfiguration = "config.variant";
    internal const string ControlledAssetPath = "Assets/Fighter/F00/F00.asset";
    internal const string ControlledField = "canCancelOnWhiff";
    internal const string BaselineAssetSha256 =
        "3eb1d810b4070f616dcfe031ccd027604d9a6f799a4fdbc95f1a7e318004702d";
    internal const string VariantAssetSha256 =
        "16230b19cf15d51b93e3c50a7115c39fe9608e4e07e0f98f0b09cbb5691773db";

    internal static readonly IReadOnlyDictionary<string, string> RequiredFileHashes =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["Assets/Script/Fighter.cs"] =
                "ff100562dfb7b330a35d42af51cb21edccb6f118e9b512c3fd0a8e62484d3885",
            ["Assets/Script/FighterData.cs"] =
                "0a46f53828bcc13fece2ddeb2989fbff20cd02900ada6da6406a148f6eea79b8",
            ["Assets/Script/ActionData.cs"] =
                "cec8787a25727007a73359d97f239f726be6b3006162b23bdc8b1eadea7836ed",
            ["Assets/Script/InputData.cs"] =
                "e7468e13c8ddd2d783113b9e7bc1f2ae63fd6970933fd1fbcac2b7ca20836a6b",
            ["Assets/Script/AttackData.cs"] =
                "62d52cd9dc77778f81c46f9890212ec93657ab110b94407662449ec3a68d7a1a",
            ["Assets/Script/ActionDataContainer.cs"] =
                "385380bad8aec0b7996d15dc0cd6eb1f74f243b77d2087b03706111f0940c10a",
            ["Assets/Script/AttackDataContainer.cs"] =
                "d46a0960a612ff2fbcb67595e8645e6a24d7d2d031738466333ee796816b7959",
            ["Assets/Script/MotionDataContainer.cs"] =
                "b6970e204ed6f2f34d5ac2a5ee8153ef2ac8aa93108d17c1d134fb00958c01a1",
            ["Assets/Fighter/F00/Actions/B_ATTACK.asset"] =
                "ac51fdc1f7d97e89d6dd0ad687e31f3fa382f2ba2560ef421a60e9a7d9a18e0c",
            ["Assets/Fighter/F00/Actions/B_SPECIAL.asset"] =
                "e0dd0c3cca3f4f60574ecc5d0f84c8366c037a19c407d7808b62789f892d8e2b",
            ["Assets/Fighter/F00/Actions/BACKWARD.asset"] =
                "b9a18a933abecfce8ed50ee43cb42498aafd1b083c7cc46db78bcdf9d5ba445d",
            ["Assets/Fighter/F00/Actions/DAMAGE.asset"] =
                "bb4a4564156bcef05fcb5200e159fae80afb7c86f25ab139c7d392516e292f5d",
            ["Assets/Fighter/F00/Actions/DASH_BACKWARD.asset"] =
                "b34a13cbd988c0f43141add3f20b9bd8ecbca5339d7d73d151027b833532d26b",
            ["Assets/Fighter/F00/Actions/DASH_FORWARD.asset"] =
                "0eb87d42b3f70923cacf9949d495ffaab384756d964038fe42f5260316127f6b",
            ["Assets/Fighter/F00/Actions/DEAD.asset"] =
                "ac8ce3335ac5d91ce5e6803666b70508471367ef71be7a8ec56ab8e682817306",
            ["Assets/Fighter/F00/Actions/FORWARD.asset"] =
                "f652a62e245fa35672aaddf12576d6eea79ec9a264651132a42d4de5b801221c",
            ["Assets/Fighter/F00/Actions/GUARD_BREAK.asset"] =
                "4f14140a4c6969c1696ea712e437027431537f59707e614cbc8352a6feb8363b",
            ["Assets/Fighter/F00/Actions/GUARD_CROUCH.asset"] =
                "cc8fedc680f17c4396c2f96d707b5db257f6a0821525e0fa47ee8d1742873a88",
            ["Assets/Fighter/F00/Actions/GUARD_M.asset"] =
                "9f56804bc1d7628e808063f894dfffdd6696914657bb4ad6533f14ccb9640191",
            ["Assets/Fighter/F00/Actions/GUARD_PROXIMITY.asset"] =
                "acb469c290f97ebbc0edb61a03c95e69fd11679d65936bacd91e59f4284d2054",
            ["Assets/Fighter/F00/Actions/GUARD_STAND.asset"] =
                "c8f88f6d1410bc8385e14c9a5c6f77325b0879582ebd146357eaab5416c1de24",
            ["Assets/Fighter/F00/Actions/STAND.asset"] =
                "d2731601b6d29196eda063ee341ffd5b6abfe84e85ccb87cd22b7eb27410742b",
            ["Assets/Fighter/F00/Actions/N_ATTACK.asset"] =
                "214ccb908da225afab9d3e98a01866aafa460f4eae262377328ee3b651b87d89",
            ["Assets/Fighter/F00/Actions/N_SPECIAL.asset"] =
                "6f6ec455860147e2915f6e24a74a7aebf07de1086d73f488b88c386c5f254ae8",
            ["Assets/Fighter/F00/Actions/WIN.asset"] =
                "d60a3f9455c69ab230a54c7c1badeed52f1a637bec7dbe9314a0c7c31c6f60eb",
        };

    internal static string Verify(string sourceRoot, string configuration)
    {
        foreach (KeyValuePair<string, string> item in RequiredFileHashes)
        {
            string fullPath = Resolve(sourceRoot, item.Key);
            RequireHash(fullPath, item.Value);
        }

        string controlledAsset = Resolve(sourceRoot, ControlledAssetPath);
        string expectedAssetHash;
        if (StringComparer.Ordinal.Equals(configuration, BaselineConfiguration))
        {
            expectedAssetHash = BaselineAssetSha256;
        }
        else if (StringComparer.Ordinal.Equals(configuration, VariantConfiguration))
        {
            expectedAssetHash = VariantAssetSha256;
        }
        else
        {
            throw new InvalidOperationException("Unknown standalone configuration.");
        }

        RequireHash(controlledAsset, expectedAssetHash);
        return expectedAssetHash;
    }

    internal static string Resolve(string sourceRoot, string relativePath)
    {
        string root = Path.GetFullPath(sourceRoot).TrimEnd(
            Path.DirectorySeparatorChar,
            Path.AltDirectorySeparatorChar);
        string candidate = Path.GetFullPath(
            Path.Combine(root, relativePath.Replace('/', Path.DirectorySeparatorChar)));
        string prefix = root + Path.DirectorySeparatorChar;
        if (!candidate.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("Source artifact escaped the verified root.");
        }

        return candidate;
    }

    internal static string ComputeSha256(string path)
    {
        using FileStream stream = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
    }

    private static void RequireHash(string path, string expected)
    {
        string actual = ComputeSha256(path);
        if (!StringComparer.Ordinal.Equals(actual, expected))
        {
            throw new InvalidOperationException(
                "Frozen artifact SHA-256 mismatch for "
                + path
                + ". Expected "
                + expected
                + ", got "
                + actual
                + ".");
        }
    }
}
