import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate-repo-index.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_repo_index", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_extension_fixture(
    root: Path,
    *,
    lang: str,
    module: str,
    app_id: str,
    apk_name: str,
    version_code: int,
    version_name: str,
    name: str,
    source_name: str,
    source_lang: str,
    base_url: str,
) -> None:
    extension_dir = root / "src" / lang / module
    apk_dir = extension_dir / "build" / "outputs" / "apk" / "release"
    apk_dir.mkdir(parents=True)
    (apk_dir / apk_name).write_bytes(b"fake apk")
    (apk_dir / "output-metadata.json").write_text(
        json.dumps(
            {
                "applicationId": app_id,
                "elements": [
                    {
                        "versionCode": version_code,
                        "versionName": version_name,
                        "outputFile": apk_name,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (extension_dir / "repo.json").write_text(
        json.dumps(
            {
                "name": name,
                "lang": lang,
                "nsfw": 0,
                "sources": [
                    {
                        "name": source_name,
                        "lang": source_lang,
                        "baseUrl": base_url,
                        "versionId": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


class GenerateRepoIndexTest(unittest.TestCase):
    def test_source_id_matches_keiyoushi_examples(self):
        generator = load_generator()

        self.assertEqual(generator.source_id("Webtoons.com", "en", 1), "2522335540328470744")
        self.assertEqual(generator.source_id("Asura Scans", "en", 1), "6247824327199706550")
        self.assertEqual(generator.source_id("Manga Tube", "de", 1), "6851437974515624757")

    def test_generates_index_for_all_built_extensions(self):
        generator = load_generator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_extension_fixture(
                root,
                lang="de",
                module="onepiecetube",
                app_id="eu.kanade.tachiyomi.extension.de.onepiecetube",
                apk_name="tachiyomi-de.onepiecetube-v1.4.1-release.apk",
                version_code=1,
                version_name="1.4.1",
                name="OnePieceTube",
                source_name="OnePieceTube",
                source_lang="de",
                base_url="https://onepiece.tube",
            )
            write_extension_fixture(
                root,
                lang="en",
                module="example",
                app_id="eu.kanade.tachiyomi.extension.en.example",
                apk_name="tachiyomi-en.example-v1.4.7-release.apk",
                version_code=7,
                version_name="1.4.7",
                name="Example",
                source_name="Example Source",
                source_lang="en",
                base_url="https://example.test",
            )
            (root / "repo").mkdir()
            (root / "repo" / "icon.png").write_bytes(b"icon")

            index = generator.generate_repository(root)

            self.assertEqual([item["pkg"] for item in index], [
                "eu.kanade.tachiyomi.extension.de.onepiecetube",
                "eu.kanade.tachiyomi.extension.en.example",
            ])
            self.assertEqual(index[0]["version"], "1.4.1")
            self.assertEqual(index[1]["code"], 7)
            self.assertEqual(index[0]["sources"][0]["id"], generator.source_id("OnePieceTube", "de", 1))
            self.assertTrue((root / "repo" / "apk" / "tachiyomi-de.onepiecetube-v1.4.1-release.apk").exists())
            self.assertTrue((root / "repo" / "apk" / "tachiyomi-en.example-v1.4.7-release.apk").exists())
            written = json.loads((root / "repo" / "index.min.json").read_text(encoding="utf-8"))
            self.assertEqual(written, index)


if __name__ == "__main__":
    unittest.main()
