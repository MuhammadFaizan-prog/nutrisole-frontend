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
}

class ModelAssetsPackage : ReactPackage {
  @Deprecated("Same registration path as onnxruntime-react-native's OnnxruntimePackage")
  override fun createNativeModules(reactContext: ReactApplicationContext): List<NativeModule> = listOf(ModelAssetsModule(reactContext))
  override fun createViewManagers(reactContext: ReactApplicationContext): List<ViewManager<in Nothing, in Nothing>> = emptyList()
}
