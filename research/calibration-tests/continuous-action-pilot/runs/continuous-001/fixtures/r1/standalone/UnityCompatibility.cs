// License-independent compatibility surface for the frozen Footsies sources.
// This file supplies engine types and inert services only. It does not copy,
// translate, or replace any Fighter.cs rule or transition.

using System;

namespace UnityEngine
{
    [AttributeUsage(AttributeTargets.Class)]
    public sealed class CreateAssetMenuAttribute : Attribute
    {
    }

    [AttributeUsage(AttributeTargets.Field)]
    public sealed class SerializeField : Attribute
    {
    }

    public class ScriptableObject
    {
    }

    public sealed class Sprite
    {
    }

    public sealed class AudioClip
    {
    }

    public struct Vector2
    {
        public float x;
        public float y;

        public Vector2(float xValue, float yValue)
        {
            x = xValue;
            y = yValue;
        }
    }

    public struct Vector2Int
    {
        public int x;
        public int y;

        public Vector2Int(int xValue, int yValue)
        {
            x = xValue;
            y = yValue;
        }
    }

    public struct Rect
    {
        public float x;
        public float y;
        public float width;
        public float height;
    }

    public static class Mathf
    {
        public static int Abs(int value)
        {
            return Math.Abs(value);
        }
    }

    public static class Time
    {
        public static float deltaTime = 0.02f;
    }

    public static class Debug
    {
        public static void LogError(string message)
        {
            Console.Error.WriteLine(message);
        }

        public static void LogWarning(string message)
        {
            Console.Error.WriteLine(message);
        }
    }
}

namespace Footsies
{
    using UnityEngine;

    // Fighter.cs references this service only to play an action sound. The
    // standalone fixture preserves that call boundary but intentionally has no
    // audio device. No transition or cancellation decision lives here.
    public sealed class SoundManager
    {
        private static readonly SoundManager Singleton = new SoundManager();

        public static SoundManager Instance
        {
            get { return Singleton; }
        }

        public void playFighterSE(AudioClip clip, bool isFaceRight, float x)
        {
        }
    }
}
