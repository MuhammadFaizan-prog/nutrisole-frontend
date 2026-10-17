package com.muhammadfaizan.nutrisole.glucose

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import com.facebook.react.bridge.*
import java.io.File
import java.security.KeyStore
import java.security.MessageDigest
import java.util.concurrent.Executors
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Tokens never enter AsyncStorage, backup, logs or plaintext files. */
class GlucoseSessionModule(private val context: ReactApplicationContext) : ReactContextBaseJavaModule(context) {
  private val executor = Executors.newSingleThreadExecutor()
  override fun getName() = "NutriSoleSession"
  private fun file(project: String): AtomicFile {
    val hash = MessageDigest.getInstance("SHA-256").digest(project.toByteArray()).joinToString("") { "%02x".format(it) }
    return AtomicFile(File(context.noBackupFilesDir, "account-$hash.enc"))
  }
  private fun key(): SecretKey {
    val alias = "nutrisole.account.v1"
    val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    (store.getKey(alias, null) as? SecretKey)?.let { return it }
    return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
      init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
        .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build())
    }.generateKey()
  }
  @ReactMethod fun readSession(project: String, promise: Promise) { executor.execute {
    try {
      val target = file(project)
      if (!target.baseFile.exists() && !File(target.baseFile.path + ".bak").exists()) { promise.resolve(null); return@execute }
      val bytes = target.openRead().use { it.readBytes() }
      require(bytes.size in 29..65536 && bytes[0].toInt() == 1)
      val cipher = Cipher.getInstance("AES/GCM/NoPadding")
      cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(1,13)))
      cipher.updateAAD(project.toByteArray(Charsets.UTF_8))
      promise.resolve(String(cipher.doFinal(bytes.copyOfRange(13,bytes.size)), Charsets.UTF_8))
    } catch (_: Exception) { promise.reject("SESSION_READ", "Could not restore sign-in. Please sign in again.") }
  } }
  @ReactMethod fun writeSession(project: String, value: String, promise: Promise) { executor.execute {
    try {
      val target = file(project)
      if (value.isEmpty()) { target.delete(); promise.resolve(null); return@execute }
      val bytes = value.toByteArray(Charsets.UTF_8); require(bytes.size <= 60000)
      val cipher = Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE, key())
      cipher.updateAAD(project.toByteArray(Charsets.UTF_8))
      val encrypted = byteArrayOf(1) + cipher.iv + cipher.doFinal(bytes)
      val output = target.startWrite()
      try { output.write(encrypted); target.finishWrite(output) } catch (e: Exception) { target.failWrite(output); throw e }
      promise.resolve(null)
    } catch (_: Exception) { promise.reject("SESSION_WRITE", "Could not keep this sign-in securely. Please retry.") }
  } }
  override fun invalidate() { executor.shutdown(); super.invalidate() }
}
