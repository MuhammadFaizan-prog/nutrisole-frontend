package com.muhammadfaizan.nutrisole.glucose

import android.os.Bundle
import android.os.SystemClock
import android.content.Context
import android.content.ContextWrapper
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.facebook.react.bridge.Callback
import com.facebook.react.bridge.PromiseImpl
import com.facebook.react.bridge.BridgeReactContext
import com.facebook.react.bridge.WritableMap
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Runs the real bundled reader and Android Keystore, with synthetic files only. */
@RunWith(AndroidJUnit4::class)
class GlucoseCaptureTest {
  private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
  // Instrumentation runs under the target UID. Use its writable directories,
  // isolate test history from actual readings, and load fixtures from the test APK.
  private val context by lazy {
    object : ContextWrapper(instrumentation.targetContext) {
      override fun getApplicationContext(): Context = this
      override fun getNoBackupFilesDir(): File = File(baseContext.noBackupFilesDir, "glucose-native-qa").apply { mkdirs() }
      override fun getCacheDir(): File = File(baseContext.cacheDir, "glucose-native-qa").apply { mkdirs() }
      override fun getAssets() = baseContext.assets
    }
  }
  @Suppress("DEPRECATION")
  private fun module() = GlucoseCaptureModule(BridgeReactContext(context))
  private fun call(work: (PromiseImpl) -> Unit): Any? {
    val latch = CountDownLatch(1); var result: Any? = null; var failure: Any? = null
    work(PromiseImpl(Callback { args -> result = args.firstOrNull(); latch.countDown() }, Callback { args -> failure = args.firstOrNull(); latch.countDown() }))
    assertTrue("Native operation timed out", latch.await(45, TimeUnit.SECONDS))
    if (failure != null) throw AssertionError("Native operation failed: $failure")
    return result
  }
  @Test fun encryptedHistoryIsDurableAndNotPlaintext() {
    val first = module()
    val text = "{\"version\":1,\"readings\":[{\"note\":\"top-secret-test-reading\"}]}"
    val times = mutableListOf<Long>()
    repeat(10) { val start = SystemClock.elapsedRealtime(); call { first.writeHistory(text, it) }; times.add(SystemClock.elapsedRealtime() - start) }
    first.invalidate()
    val restarted = module()
    try {
      assertEquals(text, call { restarted.readHistory(it) })
      val encrypted = File(context.noBackupFilesDir, "glucose-v1.enc").readBytes()
      assertFalse(String(encrypted, Charsets.ISO_8859_1).contains("top-secret-test-reading"))
      instrumentation.sendStatus(0, Bundle().apply { putString("stream", "GLUCOSE encrypted write milliseconds: $times\n") })
    } finally { restarted.invalidate() }
    val project = "https://qa.supabase.co"
    val account = GlucoseSessionModule(BridgeReactContext(context))
    call { account.writeSession(project, "private-session-test-token", it) }; account.invalidate()
    val restored = GlucoseSessionModule(BridgeReactContext(context))
    try {
      assertEquals("private-session-test-token", call { restored.readSession(project, it) })
      val encrypted = context.noBackupFilesDir.listFiles()!!.first { it.name.startsWith("account-") }.readBytes()
      assertFalse(String(encrypted, Charsets.ISO_8859_1).contains("private-session-test-token"))
      call { restored.writeSession(project, "", it) }
      assertNull(call { restored.readSession(project, it) })
    } finally { restored.invalidate() }
  }
  @Test fun realReaderProcessesImagesAndScannedPdf() {
    val module = module()
    val output = JSONObject()
    try {
      val images = instrumentation.context.assets.list("")!!.filter { it.endsWith(".jpg") || it.endsWith(".png") || it.endsWith(".pdf") }
      for (name in images.sorted()) {
        val file = File(context.cacheDir, name)
        instrumentation.context.assets.open(name).use { src -> file.outputStream().use { src.copyTo(it) } }
        val result = call { module.recognize(file.toURI().toString(), name.endsWith(".pdf"), name, it) } as WritableMap
        val data = JSONObject(result.toHashMap() as Map<*, *>)
        val pages = data.getJSONArray("pages")
        if (name == "chughtai-style.pdf") assertTrue("Digital PDF must use its text on API 34", data.getString("engine").contains("PDF text"))
        assertTrue("No page on $name", pages.length() > 0)
        if (name == "heldout2-00-lab-report-clean.jpg") {
          assertTrue("Bundled OCR returned no text for the clean baseline", (0 until pages.length()).any { pages.getJSONObject(it).getJSONArray("boxes").length() > 0 })
        }
        output.put(name, data)
        file.delete()
        instrumentation.sendStatus(0, Bundle().apply { putString("stream", "GLUCOSE reader $name: ${data.getDouble("durationMs")} ms\n") })
      }
      assertTrue(images.any { it.endsWith(".pdf") })
      val destination = File(context.getExternalFilesDir(null), "native-reader-results.json")
      destination.writeText(output.toString())
      instrumentation.sendStatus(0, Bundle().apply { putString("stream", "GLUCOSE results: ${destination.path}\n") })
    } finally { module.invalidate() }
  }
}
