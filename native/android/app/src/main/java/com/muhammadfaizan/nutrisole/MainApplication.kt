package com.muhammadfaizan.nutrisole

import android.app.Application
import android.graphics.Typeface
import com.facebook.react.PackageList
import com.facebook.react.ReactApplication
import com.facebook.react.ReactHost
import com.facebook.react.ReactNativeApplicationEntryPoint.loadReactNative
import com.facebook.react.defaults.DefaultReactHost.getDefaultReactHost
import com.facebook.react.common.assets.ReactFontManager

class MainApplication : Application(), ReactApplication {
  override val reactHost: ReactHost by lazy {
    getDefaultReactHost(context = applicationContext, packageList = PackageList(this).packages)
  }
  override fun onCreate() {
    super.onCreate()
    listOf("NutriSans", "NutriSansBold", "NutriSerif", "NutriSerifBold", "NutriSerifText").forEach {
      ReactFontManager.getInstance().addCustomFont(it, Typeface.createFromAsset(assets, "fonts/$it.ttf"))
    }
    loadReactNative(this)
  }
}
