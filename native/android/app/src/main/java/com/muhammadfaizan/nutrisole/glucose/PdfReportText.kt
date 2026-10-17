package com.muhammadfaizan.nutrisole.glucose

import android.content.Context
import android.net.Uri
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.WritableArray
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.io.MemoryUsageSetting
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import com.tom_roush.pdfbox.text.TextPosition

/** Preserve word coordinates so result columns cannot be confused with reference ranges. */
class PdfReportText(context: Context, uri: Uri) : java.io.Closeable {
  private val document: PDDocument
  init {
    PDFBoxResourceLoader.init(context.applicationContext)
    document = context.contentResolver.openInputStream(uri).use { input ->
      requireNotNull(input)
      PDDocument.load(input, MemoryUsageSetting.setupMixed(8L * 1024 * 1024).setTempDir(context.cacheDir))
    }
    if (document.numberOfPages !in 1..10) { document.close(); error("Choose a PDF with 1–10 pages.") }
  }
  fun page(index: Int, checkCancelled: () -> Unit): WritableArray? {
    val boxes = Arguments.createArray(); var characters = 0
    val stripper = object : PDFTextStripper() {
      override fun writeString(text: String, positions: MutableList<TextPosition>) {
        checkCancelled()
        characters += text.length
        require(characters <= 150000) { "This PDF page contains too much text. Export a shorter report." }
        var word = mutableListOf<TextPosition>()
        fun flush() {
          if (word.isEmpty()) return
          val value = word.joinToString("") { it.unicode }.trim()
          if (value.isNotEmpty()) {
            val x = word.minOf { it.xDirAdj }; val y = word.minOf { it.yDirAdj - it.heightDir }
            boxes.pushMap(Arguments.createMap().apply {
              putString("text", value); putDouble("x", x.toDouble()); putDouble("y", y.toDouble())
              putDouble("width", (word.maxOf { it.xDirAdj + it.widthDirAdj } - x).toDouble())
              putDouble("height", word.maxOf { it.heightDir }.toDouble()); putDouble("angle", 0.0); putDouble("confidence", 1.0)
            })
          }
          word = mutableListOf()
        }
        for (position in positions) {
          val previous = word.lastOrNull()
          if (position.unicode.isBlank()) { flush(); continue }
          if (previous != null && (position.xDirAdj - previous.xDirAdj - previous.widthDirAdj > maxOf(1.5f, previous.widthOfSpace * .6f) || kotlin.math.abs(position.yDirAdj - previous.yDirAdj) > maxOf(2f, previous.heightDir * .5f))) flush()
          word.add(position)
        }
        flush()
      }
    }
    stripper.sortByPosition = true; stripper.startPage = index + 1; stripper.endPage = index + 1
    stripper.getText(document)
    return if (characters >= 20 && boxes.size() > 0) boxes else null
  }
  override fun close() = document.close()
}
