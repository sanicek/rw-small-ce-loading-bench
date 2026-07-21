using UnityEngine;
using Verse;

namespace SmallCELoadingBench
{
    /// <summary>
    /// Owns the settings lifecycle and the user-facing configuration window.
    /// </summary>
    public sealed class SmallCELoadingBenchMod : Mod
    {
        private readonly SmallCELoadingBenchSettings settings;

        public SmallCELoadingBenchMod(ModContentPack content) : base(content)
        {
            settings = GetSettings<SmallCELoadingBenchSettings>();
        }

        public override string SettingsCategory()
        {
            return "SmallCELoadingBench_SettingsCategory".Translate();
        }

        public override void DoSettingsWindowContents(Rect inRect)
        {
            Listing_Standard listing = new Listing_Standard();
            listing.Begin(inRect);
            listing.CheckboxLabeled("SmallCELoadingBench_EnableExample".Translate(), ref settings.enableExample);
            listing.End();
        }
    }

    /// <summary>
    /// Persists settings under stable keys that must remain compatible with saves.
    /// </summary>
    public sealed class SmallCELoadingBenchSettings : ModSettings
    {
        public bool enableExample = true;

        public override void ExposeData()
        {
            Scribe_Values.Look(ref enableExample, "enableExample", true);
        }
    }
}
