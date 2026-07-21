# Optional C# Scaffold

This scaffold adds one dependency-neutral RimWorld `Mod` entry point and a
persisted settings example. It does not add Harmony or any third-party mod API.

1. Copy `scaffolds/csharp/Source/SmallCELoadingBench` to
   `Source/SmallCELoadingBench`.
2. Keep assembly, namespace, and translation-key identities synchronized with
   the permanent package component in `About/About.xml`.
3. Replace root `LoadFolders.xml` with `scaffolds/csharp/LoadFolders.xml`;
   compiled output is installed under `1.6/Assemblies`.
4. Run `scripts/build.sh`. Set `RIMWORLD_DIR` if RimWorld is not installed in
   the default Linux Steam location.

Add Harmony only when a supported API, XML, inheritance, or composition cannot
implement the behavior. Record the target, patch type, reason, and compatibility
risk before introducing a patch.
