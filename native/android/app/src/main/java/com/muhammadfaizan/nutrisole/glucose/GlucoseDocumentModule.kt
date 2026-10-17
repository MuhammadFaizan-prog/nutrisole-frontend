package com.muhammadfaizan.nutrisole.glucose

import android.app.Activity
import android.content.Intent
import com.facebook.react.bridge.*
import com.google.mlkit.vision.documentscanner.GmsDocumentScannerOptions
import com.google.mlkit.vision.documentscanner.GmsDocumentScanning
import com.google.mlkit.vision.documentscanner.GmsDocumentScanningResult
import java.io.File

/** System document capture lets users crop, straighten and clean a report before OCR. */
class GlucoseDocumentModule(private val context: ReactApplicationContext) : ReactContextBaseJavaModule(context) {
  private var pending: Promise? = null
  private val requestCode = 2948
  private val listener = object : BaseActivityEventListener() {
    override fun onActivityResult(activity: Activity, request: Int, result: Int, data: Intent?) {
      if (request != requestCode) return
      val promise = pending ?: return; pending = null
      if (result != Activity.RESULT_OK) { promise.resolve(null); return }
      try {
        val uri = GmsDocumentScanningResult.fromActivityResultIntent(data)?.pages?.firstOrNull()?.imageUri
          ?: error("No report photo was selected.")
        val file = File.createTempFile("glucose-scan-", ".jpg", context.cacheDir)
        context.contentResolver.openInputStream(uri).use { input -> requireNotNull(input); file.outputStream().use { input.copyTo(it) } }
        promise.resolve(android.net.Uri.fromFile(file).toString())
      } catch (_: Exception) { promise.reject("SCAN_READ", "The report photo could not be opened. Please try again.") }
    }
  }
  init { context.addActivityEventListener(listener) }
  override fun getName() = "NutriSoleDocument"
  @ReactMethod fun scan(promise: Promise) {
    val activity = context.currentActivity
    if (activity == null) { promise.reject("SCAN_UNAVAILABLE", "The camera is not ready."); return }
    if (pending != null) { promise.reject("SCAN_BUSY", "A report is already open."); return }
    pending = promise
    val options = GmsDocumentScannerOptions.Builder().setGalleryImportAllowed(true).setPageLimit(1)
      .setResultFormats(GmsDocumentScannerOptions.RESULT_FORMAT_JPEG)
      .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL).build()
    GmsDocumentScanning.getClient(options).getStartScanIntent(activity)
      .addOnSuccessListener { sender ->
        try { activity.startIntentSenderForResult(sender, requestCode, null, 0, 0, 0) }
        catch (_: Exception) { pending = null; promise.reject("SCAN_UNAVAILABLE", "Document capture is unavailable.") }
      }
      .addOnFailureListener { pending = null; promise.reject("SCAN_UNAVAILABLE", "Document capture is unavailable.") }
  }
  override fun invalidate() { context.removeActivityEventListener(listener); pending?.reject("SCAN_CLOSED", "Report capture was closed."); pending = null; super.invalidate() }
}
