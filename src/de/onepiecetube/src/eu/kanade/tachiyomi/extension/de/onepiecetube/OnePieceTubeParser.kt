package eu.kanade.tachiyomi.extension.de.onepiecetube

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

object OnePieceTubeParser {

    private val dataRegex = Regex("""(?s)window\.__data\s*=\s*(\{.*?})\s*;?\s*</script>""")

    private val json = Json {
        ignoreUnknownKeys = true
    }

    fun extractData(html: String): String = dataRegex.find(html)?.groupValues?.get(1)
        ?: throw IllegalStateException("window.__data not found")

    fun parseChapterEntries(html: String): List<ChapterEntry> {
        val root = json.parseToJsonElement(extractData(html)).jsonObject
        val entries = root["entries"]?.jsonArray ?: return emptyList()
        return entries.mapNotNull { element ->
            val item = element.jsonObject
            val id = item["id"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null
            val number = item["number"]?.jsonPrimitive?.intOrNull ?: id
            ChapterEntry(
                id = id,
                number = number,
                name = item["name"]?.jsonPrimitive?.content.orEmpty(),
                lang = item["lang"]?.jsonPrimitive?.content.orEmpty(),
                pages = item["pages"]?.jsonPrimitive?.intOrNull ?: 0,
                isAvailable = item["is_available"]?.jsonPrimitive?.booleanOrNull ?: false,
                date = item["date"]?.jsonPrimitive?.content.orEmpty(),
                href = item["href"]?.jsonPrimitive?.content.orEmpty(),
            )
        }
    }

    fun parsePageUrls(html: String): List<String> {
        val root = json.parseToJsonElement(extractData(html)).jsonObject
        val pages = root["chapter"]
            ?.jsonObject
            ?.get("pages")
            ?.jsonArray
            ?: return emptyList()

        return pages.mapNotNull { element ->
            element.jsonObject["url"]?.jsonPrimitive?.content?.takeIf { it.isNotBlank() }
        }
    }
}

data class ChapterEntry(
    val id: Int,
    val number: Int,
    val name: String,
    val lang: String,
    val pages: Int,
    val isAvailable: Boolean,
    val date: String,
    val href: String,
)
