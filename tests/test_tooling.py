"""Exercise generic contracts without requiring RimWorld, .NET, or a network."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from project import ProjectError, load_project  # noqa: E402


def script_module(name: str, filename: str):
    """Load command scripts whose hyphenated filenames are not import names."""

    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = script_module("validate_package", "validate-package.py")
ValidationError = validator.ValidationError
validate = validator.validate
source_validator = script_module("validate_source", "validate-source.py")
SourceError = source_validator.SourceError
mod_validator = script_module("validate_mod", "validate-mod.py")
ModValidationError = mod_validator.ModValidationError
preview_composer = script_module("compose_about_preview", "compose-about-preview.py")


class PackageFixture:
    """Create one minimal package whose mutations isolate validator failures."""

    def __init__(self, root: Path) -> None:
        self.package = root / "FixtureMod"
        (self.package / "About").mkdir(parents=True)
        (self.package / "Defs").mkdir()
        (self.package / "Languages" / "English" / "Keyed").mkdir(parents=True)
        (self.package / "About" / "About.xml").write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<ModMetaData>
  <name>Fixture Mod</name>
  <author>Sanicek</author>
  <packageId>FixtureAuthor.FixtureMod</packageId>
  <modVersion>0.1.0</modVersion>
  <url>https://example.invalid/mod</url>
  <supportedVersions><li>1.6</li></supportedVersions>
  <description>Fixture package.</description>
</ModMetaData>
""",
            encoding="utf-8",
        )
        (self.package / "LoadFolders.xml").write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<loadFolders><v1.6><li>/</li></v1.6></loadFolders>
""",
            encoding="utf-8",
        )
        (self.package / "Defs" / "Example.xml").write_text("<Defs />\n", encoding="utf-8")
        (self.package / "Languages" / "English" / "Keyed" / "Example.xml").write_text(
            "<LanguageData><Example_Key>Hello {0}</Example_Key></LanguageData>\n",
            encoding="utf-8",
        )


class ProjectTests(unittest.TestCase):
    def test_project_metadata_is_valid(self) -> None:
        project = load_project(REPO_ROOT / "About" / "About.xml")
        self.assertEqual(project.package_name, "SmallCELoadingBench")
        self.assertEqual(project.version, "0.1.3")
        self.assertEqual(project.supported_versions, ("1.6",))

    def test_prerelease_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            metadata = Path(temporary) / "About.xml"
            text = (REPO_ROOT / "About" / "About.xml").read_text(encoding="utf-8")
            metadata.write_text(text.replace("0.1.3", "0.1.3-rc.1"), encoding="utf-8")
            with self.assertRaisesRegex(ProjectError, "MAJOR.MINOR.PATCH"):
                load_project(metadata)

    def test_internal_artifact_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            metadata = Path(temporary) / "About.xml"
            text = (REPO_ROOT / "About" / "About.xml").read_text(encoding="utf-8")
            metadata.write_text(text.replace("Sanicek.SmallCELoadingBench", "Sanicek.ReLeAsEs"), encoding="utf-8")
            with self.assertRaisesRegex(ProjectError, "reserved"):
                load_project(metadata)


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = PackageFixture(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_valid_xml_package_without_workshop_id(self) -> None:
        project = validate(self.fixture.package)
        self.assertEqual(project.package_id, "FixtureAuthor.FixtureMod")

    def test_valid_published_workshop_id(self) -> None:
        (self.fixture.package / "About" / "PublishedFileId.txt").write_text("123456789\n", encoding="ascii")
        validate(self.fixture.package)

    def test_invalid_workshop_id_is_rejected(self) -> None:
        (self.fixture.package / "About" / "PublishedFileId.txt").write_text("TEMPLATE\n", encoding="ascii")
        with self.assertRaisesRegex(ValidationError, "positive numeric"):
            validate(self.fixture.package)

    def test_unexpected_package_content_is_rejected(self) -> None:
        (self.fixture.package / "Source").mkdir()
        with self.assertRaisesRegex(ValidationError, "unexpected top-level directory"):
            validate(self.fixture.package)

    def test_symlink_is_rejected(self) -> None:
        (self.fixture.package / "Defs" / "Link.xml").symlink_to(self.fixture.package / "Defs" / "Example.xml")
        with self.assertRaisesRegex(ValidationError, "symlinks"):
            validate(self.fixture.package)

    def test_translation_placeholder_drift_is_rejected(self) -> None:
        french = self.fixture.package / "Languages" / "French" / "Keyed"
        french.mkdir(parents=True)
        (french / "Example.xml").write_text(
            "<LanguageData><Example_Key>Bonjour {1}</Example_Key></LanguageData>\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "placeholders differ"):
            validate(self.fixture.package)

    def test_versioned_assembly_requires_load_mapping(self) -> None:
        assemblies = self.fixture.package / "1.6" / "Assemblies"
        assemblies.mkdir(parents=True)
        (assemblies / "FixtureMod.dll").write_bytes(b"fixture")
        with self.assertRaisesRegex(ValidationError, "must load '1.6'"):
            validate(self.fixture.package)

    def test_windows_style_load_folder_traversal_is_rejected(self) -> None:
        (self.fixture.package / "LoadFolders.xml").write_text(
            "<loadFolders><v1.6><li>/</li><li>1.6\\..\\..\\OtherMod</li></v1.6></loadFolders>\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "unsafe load folder"):
            validate(self.fixture.package)

    def test_duplicate_key_across_catalogs_is_rejected(self) -> None:
        (self.fixture.package / "Languages" / "English" / "Keyed" / "Other.xml").write_text(
            "<LanguageData><Example_Key>Again {0}</Example_Key></LanguageData>\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "across catalogs"):
            validate(self.fixture.package)

    def test_uppercase_xml_extension_is_parsed(self) -> None:
        (self.fixture.package / "Defs" / "Broken.XML").write_text("<Defs>", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "invalid XML"):
            validate(self.fixture.package)

    def test_uppercase_keyed_catalog_checks_duplicates(self) -> None:
        (self.fixture.package / "Languages" / "English" / "Keyed" / "Other.XML").write_text(
            "<LanguageData><Example_Key>Again {0}</Example_Key></LanguageData>\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "across catalogs"):
            validate(self.fixture.package)


class ModValidatorTests(unittest.TestCase):
    def test_maintained_source_has_fixed_1x1_contract(self) -> None:
        mod_validator.validate_mod(REPO_ROOT)

    def test_missing_southward_alignment_offset_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "Package"
            shutil.copytree(REPO_ROOT / "Patches", package / "Patches")
            texture_source = REPO_ROOT / "Textures" / "Things" / "Building" / "SmallCELoadingBench"
            texture_target = package / "Textures" / "Things" / "Building" / "SmallCELoadingBench"
            shutil.copytree(texture_source, texture_target)
            patch = package / "Patches" / "SmallCELoadingBench" / "AmmoBench.xml"
            patch.write_text(
                patch.read_text(encoding="utf-8").replace("          <drawOffset>(0,0,-0.1)</drawOffset>\n", ""),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ModValidationError, "fixed 1x1 contract"):
                mod_validator.validate_mod(package)

    def test_missing_recolor_mask_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "Package"
            shutil.copytree(REPO_ROOT / "Patches", package / "Patches")
            texture_source = REPO_ROOT / "Textures" / "Things" / "Building" / "SmallCELoadingBench" / "LoadingBench.png"
            texture_target = package / "Textures" / "Things" / "Building" / "SmallCELoadingBench" / "LoadingBench.png"
            texture_target.parent.mkdir(parents=True)
            shutil.copyfile(texture_source, texture_target)
            with self.assertRaisesRegex(ModValidationError, "required texture"):
                mod_validator.validate_mod(package)

    def test_runtime_artwork_byte_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "Package"
            shutil.copytree(REPO_ROOT / "Patches", package / "Patches")
            texture_source = REPO_ROOT / "Textures" / "Things" / "Building" / "SmallCELoadingBench"
            texture_target = package / "Textures" / "Things" / "Building" / "SmallCELoadingBench"
            shutil.copytree(texture_source, texture_target)
            with (texture_target / "LoadingBench.png").open("ab") as texture:
                texture.write(b"drift")
            with self.assertRaisesRegex(ModValidationError, "approved runtime artwork bytes changed"):
                mod_validator.validate_mod(package)


class AboutPreviewArtworkTests(unittest.TestCase):
    def test_preview_uses_the_documented_layout_and_sources(self) -> None:
        texture_path = REPO_ROOT / "Textures/Things/Building/SmallCELoadingBench/LoadingBench.png"
        mask_path = texture_path.with_name("LoadingBench_m.png")
        font_path = preview_composer.default_font()
        preview_composer.require_source(texture_path, preview_composer.TEXTURE_SHA256, "texture")
        preview_composer.require_source(mask_path, preview_composer.MASK_SHA256, "mask")
        preview_composer.require_source(font_path, preview_composer.FONT_SHA256, "font")
        badge = Image.new("RGBA", (300, 100), "white")

        with Image.open(texture_path) as texture, Image.open(mask_path) as mask:
            preview = preview_composer.compose_preview(texture, mask, badge, font_path)

        self.assertEqual((1234, 500), preview.size)
        self.assertEqual("RGB", preview.mode)
        self.assertEqual((0, 0, 0), preview.getpixel((0, 0)))
        self.assertIsNotNone(preview.crop((0, 20, 1234, 120)).getbbox())
        self.assertIsNotNone(preview.crop((489, 205, 745, 461)).getbbox())
        self.assertEqual((255, 255, 255), preview.getpixel((32, 368)))
        self.assertIsNone(preview.crop((0, 160, 400, 350)).getbbox())

    def test_preview_recolor_uses_partial_red_mask_values(self) -> None:
        texture = Image.new("RGBA", (1, 1), (200, 180, 160, 255))
        mask = Image.new("RGBA", (1, 1), (128, 0, 0, 255))

        recolored = preview_composer.recolor(texture, mask, preview_composer.STEEL)

        self.assertEqual((162, 153, 137, 255), recolored.getpixel((0, 0)))


class PrototypeArtworkTests(unittest.TestCase):
    def test_compositor_preserves_base_and_mutes_fixture(self) -> None:
        composer = script_module("compose_loading_bench_prototype", "compose-loading-bench-prototype.py")
        base = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(base).rectangle((21, 13, 107, 110), fill=(210, 210, 210, 255))
        mask = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(mask).rectangle((21, 13, 107, 110), fill=(255, 0, 0, 255))
        source = Image.new("RGB", (50, 50), (220, 220, 220))
        ImageDraw.Draw(source).rectangle((10, 8, 40, 42), fill=(120, 35, 30))

        texture, composed_mask = composer.compose_prototype(
            source,
            base,
            mask,
            crop=(0, 0, 50, 50),
            maximum=(30, 34),
            center_x=64,
            bottom=90,
            detail_scale=0.5,
            blur_radius=0.55,
            noise_amplitude=5,
        )
        repeated_texture, repeated_mask = composer.compose_prototype(
            source,
            base,
            mask,
            crop=(0, 0, 50, 50),
            maximum=(30, 34),
            center_x=64,
            bottom=90,
            detail_scale=0.5,
            blur_radius=0.55,
            noise_amplitude=5,
        )

        self.assertEqual(texture.tobytes(), repeated_texture.tobytes())
        self.assertEqual(composed_mask.tobytes(), repeated_mask.tobytes())
        self.assertEqual(base.getpixel((24, 20)), texture.getpixel((24, 20)))
        self.assertGreater(texture.getpixel((64, 75))[0], texture.getpixel((64, 75))[1])
        self.assertLess(texture.getpixel((64, 75))[0] - texture.getpixel((64, 75))[1], 70)
        self.assertEqual((112, 0, 0), composed_mask.getpixel((64, 75))[:3])
        self.assertEqual((255, 0, 0), composed_mask.getpixel((24, 20))[:3])

    def test_positioned_source_removes_neutral_backing_without_moving_fixture(self) -> None:
        composer = script_module("compose_loading_bench_prototype", "compose-loading-bench-prototype.py")
        base = Image.new("RGBA", (128, 128), (180, 180, 180, 255))
        mask = Image.new("RGBA", (128, 128), (255, 0, 0, 255))
        source = base.copy()
        ImageDraw.Draw(source).rectangle((40, 30, 90, 90), fill=(225, 225, 225, 255))
        ImageDraw.Draw(source).rectangle((55, 45, 75, 80), fill=(80, 75, 70, 255))
        source.putpixel((54, 60), (190, 190, 190, 255))
        source.putpixel((45, 35), (190, 190, 190, 255))

        texture, composed_mask = composer.clean_positioned_fixture(
            source,
            base,
            mask,
            crop=(40, 30, 91, 91),
        )

        self.assertEqual(base.getpixel((45, 35)), texture.getpixel((45, 35)))
        self.assertEqual((80, 75, 70, 255), texture.getpixel((60, 60)))
        self.assertEqual(base.getpixel((54, 60)), texture.getpixel((54, 60)))
        self.assertEqual((112, 0, 0), composed_mask.getpixel((60, 60))[:3])
        self.assertEqual((255, 0, 0), composed_mask.getpixel((45, 35))[:3])


class ReleaseArchiveTests(unittest.TestCase):
    def test_archive_bytes_are_deterministic(self) -> None:
        module = script_module("package_release", "package-release.py")
        with tempfile.TemporaryDirectory() as temporary:
            fixture = PackageFixture(Path(temporary))
            first = Path(temporary) / "first.zip"
            second = Path(temporary) / "second.zip"
            module.write_archive(fixture.package, first)
            module.write_archive(fixture.package, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("FixtureMod/About/About.xml", archive.namelist())

    def test_archive_rejects_symlinks(self) -> None:
        module = script_module("package_release", "package-release.py")
        with tempfile.TemporaryDirectory() as temporary:
            fixture = PackageFixture(Path(temporary))
            (fixture.package / "Defs" / "Link.xml").symlink_to(fixture.package / "Defs" / "Example.xml")
            with self.assertRaises(SystemExit):
                module.write_archive(fixture.package, Path(temporary) / "release.zip")


class ReleaseExtractionTests(unittest.TestCase):
    def test_high_ratio_archive_is_rejected_before_extraction(self) -> None:
        module = __import__("release_archive")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "release.zip"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("FixtureMod/", b"")
                archive.writestr("FixtureMod/large.txt", b"0" * 1024 * 1024)
            destination = root / "destination"
            destination.mkdir()
            with self.assertRaises(module.ArchiveError):
                module.extract_release(archive_path, destination, "FixtureMod")
            self.assertFalse((destination / "FixtureMod").exists())


class ReleaseWorkflowTests(unittest.TestCase):
    def test_clean_customized_template_builds_release_twice_identically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            shutil.copytree(
                REPO_ROOT,
                repo,
                ignore=shutil.ignore_patterns(".git", "artifacts", "__pycache__", "*.pyc"),
            )
            metadata = repo / "About" / "About.xml"
            metadata.write_text(
                metadata.read_text(encoding="utf-8")
                .replace("Small CE Loading Bench", "Fixture Mod")
                .replace("SmallCELoadingBench", "FixtureMod")
                .replace("rw-small-ce-loading-bench", "fixture-mod"),
                encoding="utf-8",
            )
            manifest = repo / "artwork" / "manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8")
                .replace("Small CE Loading Bench", "Fixture Mod")
                .replace("SmallCELoadingBench", "FixtureMod"),
                encoding="utf-8",
            )
            version = load_project(metadata).version
            shutil.copyfile(repo / "docs" / "releases" / "EXAMPLE.md", repo / "docs" / "releases" / f"{version}.md")
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "test fixture"],
                cwd=repo,
                check=True,
            )

            command = [sys.executable, repo / "scripts" / "package-release.py"]
            subprocess.run(command, cwd=repo, check=True, capture_output=True, text=True)
            archive = repo / "artifacts" / "releases" / f"FixtureMod-v{version}.zip"
            first = archive.read_bytes()
            subprocess.run(command, cwd=repo, check=True, capture_output=True, text=True)
            self.assertEqual(first, archive.read_bytes())
            self.assertTrue(archive.with_suffix(".zip.sha256").is_file())


class ScaffoldTests(unittest.TestCase):
    def test_csharp_scaffold_is_complete_and_inactive(self) -> None:
        project = REPO_ROOT / "scaffolds" / "csharp" / "Source" / "SmallCELoadingBench" / "SmallCELoadingBench.csproj"
        lockfile = project.with_name("packages.lock.json")
        self.assertTrue(project.is_file())
        self.assertTrue(lockfile.is_file())
        source = REPO_ROOT / "Source"
        if source.exists():
            projects = list(source.glob("*/*.csproj"))
            self.assertEqual(len(projects), 1)
            self.assertTrue(projects[0].with_name("packages.lock.json").is_file())


class SourceTests(unittest.TestCase):
    def copy_repository(self, destination: Path) -> Path:
        repo = destination / "repo"
        shutil.copytree(
            REPO_ROOT,
            repo,
            ignore=shutil.ignore_patterns(".git", "artifacts", "__pycache__", "*.pyc"),
        )
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        return repo

    def test_symlinked_artifacts_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = self.copy_repository(root)
            external = root / "external"
            external.mkdir()
            (repo / "artifacts").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(SourceError, "artifacts must not be a symlink"):
                source_validator.validate_source(repo)

    def test_package_source_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = self.copy_repository(root)
            external = root / "private.txt"
            external.write_text("private", encoding="utf-8")
            (repo / "LICENSE").unlink()
            (repo / "LICENSE").symlink_to(external)
            with self.assertRaisesRegex(SourceError, "package source may not contain symlinks"):
                source_validator.validate_source(repo)

    def test_ignored_runtime_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = self.copy_repository(Path(temporary))
            ignored = repo / "Textures" / "bin" / "private.dat"
            ignored.parent.mkdir(parents=True)
            ignored.write_text("private", encoding="utf-8")
            with self.assertRaisesRegex(SourceError, "ignored file or directory"):
                source_validator.validate_source(repo)

    def test_ignored_csharp_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = self.copy_repository(Path(temporary))
            source = repo / "Source" / "FixtureMod"
            source.mkdir(parents=True)
            hidden_code = source / "LocalOnly.cs"
            hidden_code.write_text("internal class LocalOnly {}\n", encoding="utf-8")
            (repo / ".git" / "info" / "exclude").write_text("Source/**/*.cs\n", encoding="utf-8")
            with self.assertRaisesRegex(SourceError, "ignored C# build input"):
                source_validator.validate_source(repo)

    def test_symlinked_csharp_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = self.copy_repository(root)
            external = root / "external-source"
            external.mkdir()
            (repo / "Source").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(SourceError, "Source must be a real directory"):
                source_validator.validate_source(repo)

    def test_release_requires_a_version_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = self.copy_repository(Path(temporary))
            version = load_project(repo / "About" / "About.xml").version
            (repo / "docs" / "releases" / f"{version}.md").unlink()
            with self.assertRaisesRegex(SourceError, "release record is required"):
                source_validator.validate_source(repo, release=True)

    def test_release_record_must_be_tracked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = self.copy_repository(Path(temporary))
            with self.assertRaisesRegex(SourceError, "release record must be tracked"):
                source_validator.validate_source(repo, release=True)


class InstallTests(unittest.TestCase):
    def test_installer_stages_a_correctly_named_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            shutil.copytree(
                REPO_ROOT,
                repo,
                ignore=shutil.ignore_patterns(".git", "artifacts", "__pycache__", "*.pyc"),
            )
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            rimworld = root / "RimWorld"
            (rimworld / "Mods").mkdir(parents=True)
            (rimworld / "Version.txt").write_text("1.6.4871 rev598\n", encoding="utf-8")

            subprocess.run(
                [repo / "scripts" / "install-local.sh"],
                cwd=repo,
                env={**__import__("os").environ, "RIMWORLD_DIR": str(rimworld)},
                check=True,
                capture_output=True,
                text=True,
            )

            installed = rimworld / "Mods" / "SmallCELoadingBench"
            self.assertTrue((installed / "About" / "About.xml").is_file())
            self.assertFalse(any((rimworld / "Mods").glob(".SmallCELoadingBench.stage.*")))

    def test_installer_refuses_unrelated_existing_mod(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            rimworld = Path(temporary) / "RimWorld"
            target = rimworld / "Mods" / "SmallCELoadingBench"
            (target / "About").mkdir(parents=True)
            metadata = (REPO_ROOT / "About" / "About.xml").read_text(encoding="utf-8")
            (target / "About" / "About.xml").write_text(
                metadata.replace("Sanicek.SmallCELoadingBench", "AnotherAuthor.SmallCELoadingBench"),
                encoding="utf-8",
            )
            sentinel = target / "sentinel.txt"
            sentinel.write_text("untouched", encoding="utf-8")
            result = subprocess.run(
                [REPO_ROOT / "scripts" / "install-local.sh"],
                cwd=REPO_ROOT,
                env={**__import__("os").environ, "RIMWORLD_DIR": str(rimworld)},
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("install target belongs to", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "untouched")


if __name__ == "__main__":
    unittest.main()
