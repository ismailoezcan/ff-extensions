# Custom Tachiyomi Extensions

Ein kleines Mihon/Tachiyomi/Suwayomi-kompatibles Extension-Repository fuer eigene
Quellen. Aktuell enthalten:

- `OnePieceTube` (`de`) fuer `https://onepiece.tube`

Das Repository ist bewusst multi-source-ready aufgebaut: neue Extensions koennen
unter `src/<lang>/<source>` ergaenzt werden. Der Gradle-Build laedt alle
Extensions unter `src/`, und der Repo-Generator erzeugt daraus automatisch den
statischen Suwayomi/Mihon-Index.

## GitHub Pages

Der Workflow `.github/workflows/publish.yml` baut bei jedem Push auf `main` alle
Release-APKs, erzeugt `repo/index.min.json` und published den Ordner `repo/` per
GitHub Pages.

Nach dem ersten Push muss in GitHub unter `Settings -> Pages` als Build-Quelle
`GitHub Actions` aktiv sein. Die Extension-Repo-URL fuer Suwayomi ist danach:

```text
https://<github-user>.github.io/<repo>/index.min.json
```

## Lokaler Build

Falls lokal JDK und Android-SDK installiert sind:

```bash
./gradlew --no-daemon -Dorg.gradle.vfs.watch=false assembleRelease
python3 scripts/generate-repo-index.py
```

Ohne lokales Android-SDK geht es per Docker:

```bash
docker run --rm --platform linux/amd64 \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/cirruslabs/android-sdk:35 \
  ./gradlew --no-daemon -Dorg.gradle.vfs.watch=false assembleRelease

python3 scripts/generate-repo-index.py
```

Der generierte statische Repo-Output liegt unter:

```text
repo/
```

`repo/` ist bewusst nicht versioniert, weil GitHub Actions es reproduzierbar neu
erzeugt.

## Updates

Fuer eine neue Extension-Version:

1. Code aendern.
2. `extVersionCode` in der jeweiligen `src/<lang>/<source>/build.gradle`
   erhoehen.
3. Auf `main` pushen.

Die Version im Index kommt automatisch aus Gradles `output-metadata.json`, z.B.
`1.4.2` fuer `extVersionCode = 2`.

## Neue Quelle hinzufuegen

1. Neue Extension unter `src/<lang>/<source>` anlegen.
2. `build.gradle` mit `extName`, `extClass` und `extVersionCode` ergaenzen.
3. Kotlin-Source implementieren.
4. `repo.json` ergaenzen:

```json
{
  "name": "Example",
  "lang": "en",
  "nsfw": 0,
  "sources": [
    {
      "name": "Example",
      "lang": "en",
      "baseUrl": "https://example.test",
      "versionId": 1
    }
  ]
}
```

`versionId` bleibt normalerweise `1`. Der Generator berechnet daraus die
Tachiyomi/Keiyoushi-kompatible Source-ID:

```text
md5("<source-name-lowercase>/<lang>/<versionId>")[0..16] & Long.MAX_VALUE
```

## OnePieceTube

- Package: `eu.kanade.tachiyomi.extension.de.onepiecetube`
- Source: `OnePieceTube`
- Sprache: `de`
- Inhalt: eine feste Serie, `One Piece (Deutsch)`
- Serienseite: `https://onepiece.tube/manga/kapitel-mangaliste`

Die Seite rendert die relevanten Daten in einem JavaScript-Block:

```js
window.__data = {
  "entries": []
};
```

Die Extension liest daraus Kapitel und Page-URLs. Downloads und CBZ-Erstellung
uebernimmt Suwayomi.

## Smoke

1. GitHub-Pages-URL in Suwayomi als Extension-Repo eintragen.
2. Extension installieren.
3. Source `OnePieceTube (DE)` oeffnen.
4. `One Piece` suchen.
5. Kapitel-Liste laden.
6. Ein Kapitel herunterladen.
