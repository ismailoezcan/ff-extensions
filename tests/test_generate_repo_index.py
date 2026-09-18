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


def write_fake_signed_apk(path: Path) -> None:
    """APK-Zip mit echtem PKCS#7-Block (selbstsigniertes Zertifikat) in META-INF."""
    import subprocess
    import zipfile

    work = path.parent
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
            "-subj", "/CN=test", "-keyout", str(work / "key.pem"), "-out", str(work / "cert.pem"),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "openssl", "crl2pkcs7", "-nocrl", "-certfile", str(work / "cert.pem"),
            "-outform", "DER", "-out", str(work / "CERT.RSA"),
        ],
        check=True,
        capture_output=True,
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.write(work / "CERT.RSA", "META-INF/CERT.RSA")
        zf.writestr("classes.dex", b"dex")


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

    def test_writes_legacy_repo_json_for_suwayomi(self):
        # Suwayomi >= 2.3 loeses legacy stores ueber repo.json neben index.min.json auf
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

            generator.generate_repository(root)

            repo_json = json.loads((root / "repo" / "repo.json").read_text(encoding="utf-8"))
            self.assertIsNone(repo_json["index_v2"])
            self.assertEqual(repo_json["meta"]["name"], generator.REPO_NAME)
            self.assertEqual(repo_json["meta"]["shortName"], generator.REPO_SHORT_NAME)
            self.assertEqual(repo_json["meta"]["website"], generator.REPO_WEBSITE)
            # Fake-APK ohne Signatur: Fingerprint bleibt leer statt den Build abzubrechen
            self.assertEqual(repo_json["meta"]["signingKeyFingerprint"], "")

    def test_signing_fingerprint_is_sha256_of_apk_certificate(self):
        generator = load_generator()
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "signed.apk"
            write_fake_signed_apk(apk)

            fingerprint = generator.apk_signing_fingerprint(apk)

            self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
