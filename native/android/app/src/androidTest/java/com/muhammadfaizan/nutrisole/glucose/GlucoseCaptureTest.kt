package com.muhammadfaizan.nutrisole.glucose

import android.os.Bundle
import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.facebook.react.bridge.Callback
import com.facebook.react.bridge.PromiseImpl
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.WritableMap
import org.json.JSONArray
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
  private val context get() = instrumentation.context
  private fun call(work: (PromiseImpl) -> Unit): Any? {
    val latch = CountDownLatch(1); var result: Any? = null; var failure: Any? = null
    work(PromiseImpl(Callback { args -> result = args.firstOrNull(); latch.countDown() }, Callback { args -> failure = args.firstOrNull(); latch.countDown() }))
    assertTrue("Native operation timed out", latch.await(45, TimeUnit.SECONDS))
    if (failure != null) throw AssertionError("Native operation failed: $failure")
    return result
  }
  @Test fun encryptedHistoryIsDurableAndNotPlaintext() {
    val first = GlucoseCaptureModule(ReactApplicationContext(context))
    val text = "{\"version\":1,\"readings\":[{\"note\":\"top-secret-test-reading\"}]}"
    val times = mutableListOf<Long>()
    repeat(10) { val start = SystemClock.elapsedRealtime(); call { first.writeHistory(text, it) }; times.add(SystemClock.elapsedRealtime() - start) }
    first.invalidate()
    val restarted = GlucoseCaptureModule(ReactApplicationContext(context))
    try {
      assertEquals(text, call { restarted.readHistory(it) })
      val encrypted = File(context.noBackupFilesDir, "glucose-v1.enc").readBytes()
      assertFalse(String(encrypted, Charsets.ISO_8859_1).contains("top-secret-test-reading"))
      instrumentation.sendStatus(0, Bundle().apply { putString("stream", "GLUCOSE encrypted write milliseconds: $times\n") })
    } finally { restarted.invalidate() }
  }
  @Test fun realReaderProcessesImagesAndScannedPdf() {
    val module = GlucoseCaptureModule(ReactApplicationContext(context))
    val output = JSONObject()
    try {
      val images = context.assets.list("")!!.filter { it.endsWith(".jpg") || it.endsWith(".png") || it.endsWith(".pdf") }
      for (name in images.sorted()) {
        val file = File(context.cacheDir, name)
        context.assets.open(name).use { src -> file.outputStream().use { src.copyTo(it) } }
        val result = call { module.recognize(file.toURI().toString(), name.endsWith(".pdf"), name, it) } as WritableMap
        val data = JSONObject(result.toHashMap() as Map<*, *>)
        assertTrue("No text on $name", data.getJSONArray("pages").length() > 0)
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
