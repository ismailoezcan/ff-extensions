package eu.kanade.tachiyomi.extension.de.onepiecetube

import eu.kanade.tachiyomi.network.GET
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.online.HttpSource
import keiyoushi.network.rateLimit
import okhttp3.Headers
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Request
import okhttp3.Response
import java.text.SimpleDateFormat
import java.util.Locale

class OnePieceTube : HttpSource() {

    override val name = "OnePieceTube"

    override val baseUrl = "https://onepiece.tube"

    override val lang = "de"

    override val supportsLatest = true

    override val client = network.client.newBuilder()
        .rateLimit(1)
        .build()

    override fun headersBuilder(): Headers.Builder = super.headersBuilder()
        .set("Referer", "$baseUrl/")

    override fun popularMangaRequest(page: Int): Request {
        val url = "$baseUrl/manga/kapitel-mangaliste".toHttpUrl().newBuilder()
            .addQueryParameter("page", page.toString())
            .build()

        return GET(url, headers)
    }

    override fun popularMangaParse(response: Response): MangasPage = MangasPage(if (response.request.url.queryParameter("page") == "2") emptyList() else listOf(staticManga()), false)

    override fun latestUpdatesRequest(page: Int): Request = popularMangaRequest(page)

    override fun latestUpdatesParse(response: Response): MangasPage = popularMangaParse(response)

    override fun searchMangaRequest(page: Int, query: String, filters: eu.kanade.tachiyomi.source.model.FilterList): Request {
        val url = "$baseUrl/manga/kapitel-mangaliste".toHttpUrl().newBuilder()
            .addQueryParameter("page", page.toString())
            .addQueryParameter("q", query)
            .build()

        return GET(url, headers)
    }

    override fun searchMangaParse(response: Response): MangasPage {
        val page = response.request.url.queryParameter("page")?.toIntOrNull() ?: 1
        val query = response.request.url.queryParameter("q").orEmpty()
        if (page > 1 || !matchesStaticSeriesQuery(query)) return MangasPage(emptyList(), false)
        return MangasPage(listOf(staticManga()), false)
    }

    override fun mangaDetailsRequest(manga: SManga): Request = GET("$baseUrl/manga/kapitel-mangaliste", headers)

    override fun mangaDetailsParse(response: Response): SManga = staticManga().apply {
        description = "OnePiece-Tube bietet die neuesten und aktuellsten Manga-Kapitel auf Deutsch."
    }

    override fun chapterListRequest(manga: SManga): Request = GET("$baseUrl/manga/kapitel-mangaliste", headers)

    override fun chapterListParse(response: Response): List<SChapter> = OnePieceTubeParser.parseChapterEntries(response.body.string())
        .filter { it.isAvailable }
        .map { entry ->
            SChapter.create().apply {
                url = entry.href.ifBlank { "$baseUrl/manga/kapitel/${entry.number}/1" }
                name = entry.name
                chapter_number = entry.number.toFloat()
                date_upload = parseDate(entry.date)
            }
        }
        .sortedByDescending { it.chapter_number }

    override fun pageListRequest(chapter: SChapter): Request {
        val url = when {
            chapter.url.startsWith("http") -> chapter.url
            chapter.url.startsWith("/") -> baseUrl + chapter.url
            else -> "$baseUrl/${chapter.url}"
        }
        return GET(url, headers)
    }

    override fun pageListParse(response: Response): List<Page> = OnePieceTubeParser.parsePageUrls(response.body.string())
        .mapIndexed { index, url -> Page(index, imageUrl = url) }

    override fun imageRequest(page: Page): Request = GET(page.imageUrl!!, headers)

    override fun imageUrlParse(response: Response): String = throw UnsupportedOperationException("Not used")

    private fun staticManga(): SManga = SManga.create().apply {
        url = "/manga/kapitel-mangaliste"
        title = "One Piece (Deutsch)"
        author = "Eiichiro Oda"
        status = SManga.ONGOING
        thumbnail_url = COVER_URL
        initialized = true
    }

    private fun matchesStaticSeriesQuery(query: String): Boolean {
        if (query.isBlank()) return true
        val normalized = query.lowercase()
            .replace("-", "")
            .replace(" ", "")
        return normalized in STATIC_SEARCH_TERMS
    }

    private fun parseDate(raw: String): Long {
        if (raw.isBlank()) return 0L
        return runCatching { DATE_FORMAT.parse(raw)?.time ?: 0L }.getOrDefault(0L)
    }

    companion object {
        private const val COVER_URL = "https://cdn.onepiecechapters.com/file/CDN-M-A-N/Screen-Shot-2021-04-23-at-9.31.12-PM-1024x732v3.png"

        private val DATE_FORMAT = SimpleDateFormat("dd.MM.yyyy", Locale.GERMANY)

        private val STATIC_SEARCH_TERMS = setOf(
            "onepiece",
            "onepiecetube",
            "kapitel",
            "onepiecekapitel",
        )
    }
}
