package com.muhammadfaizan.nutrisole

// G9 Stage J7 (cv-gauntlet-device): lets the debug CV screen use ONNX weights bundled in the QA APK.
// prepareBundled(file): copies assets/models/<file> to <filesDir>/models/<file> (ONNX Runtime needs a real file path) and returns
// { path, bytes, sha256 }. describeFile(path): returns the same for an existing file (the adb-push fallback). The JS side
// (src/cv/device/modelSource.ts) accepts a file only when bytes and sha256 equal models.ts. Nothing here decides or fakes a model.
import com.facebook.react.ReactPackage
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.uimanager.ViewManager
import java.io.File
import java.io.FileInputStream
import java.io.FileNotFoundException
import java.io.FileOutputStream
import java.security.MessageDigest
import android.graphics.Bitmap
import android.os.Build
import android.os.Debug
import android.os.PowerManager
import android.util.Base64
import android.util.Log
import java.io.FileWriter

class ModelAssetsModule(context: ReactApplicationContext) : ReactContextBaseJavaModule(context) {
  override fun getName(): String = "NsModelAssets"

  private fun info(f: File): WritableMap {
    val md = MessageDigest.getInstance("SHA-256")
    FileInputStream(f).use { input ->
      val buf = ByteArray(1 shl 16)
      while (true) { val n = input.read(buf); if (n < 0) break; md.update(buf, 0, n) }
    }
    val map = Arguments.createMap()
    map.putString("path", f.absolutePath)
    map.putDouble("bytes", f.length().toDouble())
    map.putString("sha256", md.digest().joinToString("") { "%02x".format(it) })
    return map
  }

  private fun safeName(file: String): Boolean = file.isNotEmpty() && !file.contains('/') && !file.contains('\\') && file != "." && file != ".."

  @ReactMethod
  fun prepareBundled(file: String, promise: Promise) {
    if (!safeName(file)) { promise.reject("bad_name", "invalid model file name"); return }
    Thread {
      try {
        val dir = File(reactApplicationContext.filesDir, "models")
        dir.mkdirs()
        val out = File(dir, file)
        reactApplicationContext.assets.open("models/$file").use { input ->
          FileOutputStream(out).use { output -> input.copyTo(output, 1 shl 16) }
        }
        promise.resolve(info(out))
      } catch (e: FileNotFoundException) {
        promise.reject("asset_missing", "models/$file is not bundled in this APK")
      } catch (e: Exception) {
        promise.reject("asset_copy_failed", e.toString())
      }
    }.start()
  }

  @ReactMethod
  fun describeFile(path: String, promise: Promise) {
    Thread {
      try {
        val f = File(path)
        if (!f.isFile) promise.reject("file_missing", "$path not found") else promise.resolve(info(f))
      } catch (e: Exception) {
        promise.reject("file_read_failed", e.toString())
      }
    }.start()
  }

  // ---- G9 Stage J8 (QA debug layer): see NsCvDiag below.
  @ReactMethod
  fun log(line: String) { Log.i("NutriSoleCV", line) }

  @ReactMethod
  fun runtimeStats(promise: Promise) {
    try {
      val m = Arguments.createMap()
      val pm = reactApplicationContext.getSystemService(android.content.Context.POWER_SERVICE) as PowerManager?
      m.putInt("thermal", if (Build.VERSION.SDK_INT >= 29 && pm != null) pm.currentThermalStatus else -1)
      m.putDouble("nativeHeapMb", Debug.getNativeHeapAllocatedSize() / 1048576.0)
      val rt = Runtime.getRuntime()
      m.putDouble("javaHeapMb", (rt.totalMemory() - rt.freeMemory()) / 1048576.0)
      m.putInt("sdk", Build.VERSION.SDK_INT)
      promise.resolve(m)
    } catch (e: Exception) { promise.reject("stats_failed", e.toString()) }
  }

  @ReactMethod
  fun diagDir(promise: Promise) { promise.resolve(NsCvDiag(reactApplicationContext).dir().absolutePath) }

  @ReactMethod
  fun appendDiag(line: String, promise: Promise) {
    Thread {
      try {
        FileWriter(File(NsCvDiag(reactApplicationContext).dir(), "nscv_diag.jsonl"), true).use { it.write(line); it.write("\n") }
        promise.resolve(true)
      } catch (e: Exception) { promise.reject("diag_write_failed", e.toString()) }
    }.start()
  }

  /** rgbBase64 = tightly packed RGB (w*h*3). Written as JPEG q90 to diag/<name>.jpg. */
  @ReactMethod
  fun saveRgbJpeg(name: String, rgbBase64: String, w: Int, h: Int, promise: Promise) {
    val diag = NsCvDiag(reactApplicationContext)
    if (!diag.safe(name) || w <= 0 || h <= 0 || w * h > 16_000_000) { promise.reject("bad_args", "invalid name or size"); return }
    Thread {
      try {
        val rgb = Base64.decode(rgbBase64, Base64.DEFAULT)
        if (rgb.size != w * h * 3) { promise.reject("bad_size", "${rgb.size} != ${w}x${h}x3"); return@Thread }
        val px = IntArray(w * h)
        for (i in 0 until w * h) {
          px[i] = (0xFF shl 24) or ((rgb[3 * i].toInt() and 0xFF) shl 16) or ((rgb[3 * i + 1].toInt() and 0xFF) shl 8) or (rgb[3 * i + 2].toInt() and 0xFF)
        }
        val bmp = Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888)
        val out = File(diag.dir(), "$name.jpg")
        FileOutputStream(out).use { bmp.compress(Bitmap.CompressFormat.JPEG, 90, it) }
        bmp.recycle()
        promise.resolve(out.absolutePath)
      } catch (e: Exception) { promise.reject("jpeg_failed", e.toString()) }
    }.start()
  }
}

// ---- G9 Stage J8 (QA debug layer only): logcat tag, runtime stats, diagnostic JSONL + frame/crop saves. Files go to the app's
// external files dir (/sdcard/Android/data/<app>/files/diag), which `adb pull` can read without root. Nothing here touches a model.
class NsCvDiag(private val ctx: ReactApplicationContext) {
  fun dir(): File { val d = File(ctx.getExternalFilesDir(null) ?: ctx.filesDir, "diag"); d.mkdirs(); return d }
  fun safe(name: String): Boolean = name.matches(Regex("[A-Za-z0-9_.-]{1,80}")) && name != "." && name != ".."
}

class ModelAssetsPackage : ReactPackage {
  @Deprecated("Same registration path as onnxruntime-react-native's OnnxruntimePackage")
  override fun createNativeModules(reactContext: ReactApplicationContext): List<NativeModule> = listOf(ModelAssetsModule(reactContext))
  override fun createViewManagers(reactContext: ReactApplicationContext): List<ViewManager<in Nothing, in Nothing>> = emptyList()
}
