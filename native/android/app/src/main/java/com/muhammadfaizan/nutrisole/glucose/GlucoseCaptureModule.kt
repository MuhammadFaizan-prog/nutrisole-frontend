package com.muhammadfaizan.nutrisole.glucose

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.ImageDecoder
import android.graphics.Matrix
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.Build
import android.os.SystemClock
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import androidx.exifinterface.media.ExifInterface
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.io.File
import java.security.KeyStore
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlin.math.atan2
import kotlin.math.max
import kotlin.math.min

/** No network OCR. Image decoding, PDF rendering and recognition run away from JS/UI. */
class GlucoseCaptureModule(private val context: ReactApplicationContext) : ReactContextBaseJavaModule(context) {
  private val reader = Executors.newSingleThreadExecutor()
  private val storage = Executors.newSingleThreadExecutor()
  private val cancelled = ConcurrentHashMap.newKeySet<String>()
  private val recognizer by lazy { TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS) }
  private val history get() = AtomicFile(File(context.noBackupFilesDir, "glucose-v1.enc"))
  override fun getName() = "NutriSoleGlucose"

  @ReactMethod fun addListener(event: String) { /* NativeEventEmitter contract. */ }
  @ReactMethod fun removeListeners(count: Double) { /* NativeEventEmitter contract. */ }

  private fun key(): SecretKey {
    val alias = "nutrisole.glucose.v1"
    val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    (store.getKey(alias, null) as? SecretKey)?.let { return it }
    return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
      init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
        .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
        .setKeySize(256).build())
    }.generateKey()
  }

  @ReactMethod fun readHistory(promise: Promise) {
    storage.execute {
      try {
        val file = history
        if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) { promise.resolve(null); return@execute }
        val bytes = file.openRead().use { it.readBytes() }
        require(bytes.size in 30..(25 * 1024 * 1024) && bytes[0].toInt() == 1) { "Invalid encrypted history" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(1, 13)))
        cipher.updateAAD("NutriSole glucose v1".toByteArray(Charsets.UTF_8))
        promise.resolve(String(cipher.doFinal(bytes.copyOfRange(13, bytes.size)), Charsets.UTF_8))
      } catch (e: Exception) { promise.reject("GLUCOSE_STORAGE", "Your encrypted history could not be read. It has not been cleared.", e) }
    }
  }

  @ReactMethod fun writeHistory(value: String, promise: Promise) {
    storage.execute {
      try {
        val plain = value.toByteArray(Charsets.UTF_8)
        require(plain.size <= 24 * 1024 * 1024) { "History exceeds this phone's storage limit" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        cipher.updateAAD("NutriSole glucose v1".toByteArray(Charsets.UTF_8))
        val encrypted = byteArrayOf(1) + cipher.iv + cipher.doFinal(plain)
        val file = history; val output = file.startWrite()
        try { output.write(encrypted); file.finishWrite(output) }
        catch (e: Exception) { file.failWrite(output); throw e }
        promise.resolve(null)
      } catch (e: Exception) { promise.reject("GLUCOSE_STORAGE", "Phone storage failed. Your previous history is unchanged.", e) }
    }
  }

  private fun progress(id: String, message: String) {
    if (context.hasActiveReactInstance()) context.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
      .emit("NutriSoleGlucoseProgress", Arguments.createMap().apply { putString("requestId", id); putString("message", message) })
  }
  @ReactMethod fun cancelRecognition(requestId: String) { cancelled.add(requestId) }
  private fun checkCancelled(id: String) { check(!cancelled.contains(id)) { "Import cancelled. Nothing was saved." } }

  private fun boxes(text: Text): WritableArray = Arguments.createArray().apply {
    for (block in text.textBlocks) for (line in block.lines) {
      val rect = line.boundingBox ?: continue
      val points = line.cornerPoints
      val angle = if (points != null && points.size >= 2) atan2((points[1].y - points[0].y).toDouble(), (points[1].x - points[0].x).toDouble()) else 0.0
      pushMap(Arguments.createMap().apply {
        putString("text", line.text); putDouble("x", rect.left.toDouble()); putDouble("y", rect.top.toDouble())
        putDouble("width", rect.width().toDouble()); putDouble("height", rect.height().toDouble()); putDouble("angle", angle)
        putDouble("confidence", line.confidence.toDouble().coerceIn(0.0, 1.0))
      })
    }
  }
  private fun recognizeBitmap(bitmap: Bitmap): WritableArray = boxes(Tasks.await(recognizer.process(InputImage.fromBitmap(bitmap, 0)), 30, TimeUnit.SECONDS))

  private fun image(uri: Uri): Bitmap {
    if (Build.VERSION.SDK_INT >= 28) {
      return ImageDecoder.decodeBitmap(ImageDecoder.createSource(context.contentResolver, uri)) { decoder, info, _ ->
        val scale = min(1.0, 2400.0 / max(info.size.width, info.size.height))
        decoder.setTargetSize(max(1, (info.size.width * scale).toInt()), max(1, (info.size.height * scale).toInt()))
        decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
      }
    }
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    context.contentResolver.openInputStream(uri).use { BitmapFactory.decodeStream(it, null, bounds) }
    require(bounds.outWidth > 0 && bounds.outHeight > 0) { "The image cannot be decoded. Attach a JPG or PNG." }
    var sample = 1; while (max(bounds.outWidth, bounds.outHeight) / sample > 2400) sample *= 2
    val bitmap = context.contentResolver.openInputStream(uri).use { BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample }) }
      ?: error("The photo could not be read.")
    val orientation = context.contentResolver.openInputStream(uri).use { input -> if (input == null) 1 else ExifInterface(input).getAttributeInt(ExifInterface.TAG_ORIENTATION, 1) }
    val transform = Matrix()
    when (orientation) { 2 -> transform.setScale(-1f, 1f); 3 -> transform.setRotate(180f); 4 -> transform.setScale(1f, -1f); 5 -> { transform.setRotate(90f); transform.postScale(-1f, 1f) }; 6 -> transform.setRotate(90f); 7 -> { transform.setRotate(270f); transform.postScale(-1f, 1f) }; 8 -> transform.setRotate(270f) }
    if (transform.isIdentity) return bitmap
    return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, transform, true).also { if (it !== bitmap) bitmap.recycle() }
  }

  @ReactMethod fun recognize(location: String, pdf: Boolean, requestId: String, promise: Promise) {
    reader.execute {
      val started = SystemClock.elapsedRealtime()
      try {
        checkCancelled(requestId)
        val uri = Uri.parse(location)
        require(uri.scheme == "file" || uri.scheme == "content") { "Only files selected on this phone can be read." }
        val pages = Arguments.createArray(); var textLayerPages = 0
        if (!pdf) {
          progress(requestId, "Reading the photo on this phone…")
          val bitmap = image(uri)
          try { pages.pushMap(Arguments.createMap().apply { putInt("page", 1); putArray("boxes", recognizeBitmap(bitmap)) }) }
          finally { bitmap.recycle() }
        } else {
          context.contentResolver.openFileDescriptor(uri, "r").use { fd ->
            requireNotNull(fd) { "The PDF could not be opened." }
            PdfRenderer(fd).use { document ->
              require(document.pageCount in 1..10) { "Choose a PDF with 1–10 pages. Split a longer report first; no pages have been imported." }
              for (index in 0 until document.pageCount) {
                checkCancelled(requestId); progress(requestId, "Reading PDF page ${index + 1} of ${document.pageCount}…")
                document.openPage(index).use { page ->
                  var content: WritableArray? = null
                  if (Build.VERSION.SDK_INT >= 35) {
                    val texts = page.textContents
                    // Retain geometrical columns for searchable PDFs. Unsupported or
                    // empty text layers fall through to rendered-page OCR below.
                    if (texts.sumOf { it.text.trim().length } >= 40 && texts.all { it.bounds.size == 1 && !it.text.contains('\n') }) {
                      content = Arguments.createArray()
                      for (item in texts) {
                        val bounds = item.bounds
                        if (bounds.isEmpty()) continue
                        val left = bounds.minOf { it.left }; val top = bounds.minOf { it.top }
                        val right = bounds.maxOf { it.right }; val bottom = bounds.maxOf { it.bottom }
                        content.pushMap(Arguments.createMap().apply {
                          putString("text", item.text); putDouble("x", left.toDouble()); putDouble("y", top.toDouble())
                          putDouble("width", (right - left).toDouble()); putDouble("height", (bottom - top).toDouble())
                          putDouble("angle", 0.0); putDouble("confidence", 1.0)
                        })
                      }
                      textLayerPages++
                    }
                  }
                  if (content == null) {
                    val scale = min(3.0, 2400.0 / max(page.width, page.height))
                    val bitmap = Bitmap.createBitmap(max(1, (page.width * scale).toInt()), max(1, (page.height * scale).toInt()), Bitmap.Config.ARGB_8888)
                    try { bitmap.eraseColor(Color.WHITE); page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY); content = recognizeBitmap(bitmap) }
                    finally { bitmap.recycle() }
                  }
                  pages.pushMap(Arguments.createMap().apply { putInt("page", index + 1); putArray("boxes", content) })
                }
              }
            }
          }
        }
        checkCancelled(requestId)
        promise.resolve(Arguments.createMap().apply {
          putString("engine", if (textLayerPages > 0) "Android PDF text + ML Kit (on this phone)" else "ML Kit Latin (on this phone)")
          putDouble("durationMs", (SystemClock.elapsedRealtime() - started).toDouble()); putArray("pages", pages)
        })
      } catch (e: Exception) { promise.reject("GLUCOSE_READER", e.message ?: "The report could not be read. Attach a clearer photo or enter the reading manually.", e) }
      finally { cancelled.remove(requestId) }
    }
  }

  override fun invalidate() { reader.shutdownNow(); storage.shutdownNow(); super.invalidate() }
}
