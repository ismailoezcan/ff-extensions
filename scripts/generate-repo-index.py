#!/usr/bin/env python3
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def source_id(name: str, lang: str, version_id: int = 1) -> str:
    key = f"{name.lower()}/{lang}/{version_id}"
    raw = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:16], 16)
    return str(raw & ((1 << 63) - 1))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extension_dirs(root: Path) -> list[Path]:
    src_dir = root / "src"
    if not src_dir.exists():
        return []

    dirs: list[Path] = []
    for lang_dir in sorted(path for path in src_dir.iterdir() if path.is_dir()):
        dirs.extend(sorted(path for path in lang_dir.iterdir() if path.is_dir()))
    return dirs


def release_metadata(extension_dir: Path) -> tuple[dict[str, Any], Path]:
    metadata_path = extension_dir / "build" / "outputs" / "apk" / "release" / "output-metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing release metadata: {metadata_path}")

    metadata = read_json(metadata_path)
    elements = metadata.get("elements") or []
    if len(elements) != 1:
        raise ValueError(f"Expected exactly one release APK element in {metadata_path}")

    apk_name = elements[0].get("outputFile")
    if not apk_name:
        raise ValueError(f"Missing outputFile in {metadata_path}")

    apk_path = metadata_path.parent / apk_name
    if not apk_path.exists():
        raise FileNotFoundError(f"Missing release APK: {apk_path}")

    return metadata, apk_path


def extension_entry(extension_dir: Path) -> tuple[dict[str, Any], Path]:
    config_path = extension_dir / "repo.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing repo metadata: {config_path}")

    config = read_json(config_path)
    metadata, apk_path = release_metadata(extension_dir)
    element = metadata["elements"][0]

    sources = []
    for source in config.get("sources", []):
        name = source["name"]
        lang = source.get("lang", config["lang"])
        version_id = int(source.get("versionId", 1))
        sources.append(
            {
                "name": name,
                "lang": lang,
                "id": source.get("id") or source_id(name, lang, version_id),
                "baseUrl": source["baseUrl"],
            }
        )

    if not sources:
        raise ValueError(f"Extension has no sources: {config_path}")

    return (
        {
            "name": config["name"],
            "pkg": metadata["applicationId"],
            "apk": apk_path.name,
            "lang": config.get("lang", extension_dir.parent.name),
            "code": int(element["versionCode"]),
            "version": element["versionName"],
            "nsfw": int(config.get("nsfw", 0)),
            "sources": sources,
        },
        apk_path,
    )


def prepare_repo_dir(root: Path) -> Path:
    repo_dir = root / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    for stale in [*repo_dir.glob("*.apk"), repo_dir / "index.min.json"]:
        stale.unlink(missing_ok=True)

    icon = root / "assets" / "icon.png"
    if icon.exists():
        shutil.copy2(icon, repo_dir / "icon.png")

    return repo_dir


def generate_repository(root: Path = ROOT) -> list[dict[str, Any]]:
    repo_dir = prepare_repo_dir(root)

    entries: list[dict[str, Any]] = []
    for extension_dir in extension_dirs(root):
        entry, apk_path = extension_entry(extension_dir)
        shutil.copy2(apk_path, repo_dir / apk_path.name)
        entries.append(entry)

    if not entries:
        raise SystemExit(f"No extensions found in {root / 'src'}")

    entries.sort(key=lambda item: item["pkg"])
    (repo_dir / "index.min.json").write_text(
        json.dumps(entries, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return entries


def main() -> None:
    generate_repository(ROOT)


if __name__ == "__main__":
    main()
