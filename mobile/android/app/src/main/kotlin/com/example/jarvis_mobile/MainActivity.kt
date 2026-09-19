package com.example.jarvis_mobile

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.ToneGenerator
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.util.Base64
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.util.Locale

class MainActivity : FlutterActivity(), TextToSpeech.OnInitListener {
    private val channelName = "jarvis_mobile/voice"
    private val audioPermissionRequest = 9917
    private val speechIntentRequestCode = 9918

    private var speechRecognizer: SpeechRecognizer? = null
    private var pendingSpeechResult: MethodChannel.Result? = null
    private var textToSpeech: TextToSpeech? = null
    private var ttsReady = false

    private var mediaPlayer: MediaPlayer? = null
    private var toneGen: ToneGenerator? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        try {
            textToSpeech = TextToSpeech(this, this)
            toneGen = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 85)
        } catch (e: Exception) {
            // Tone generator or TTS init failure fallback
        }

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).setMethodCallHandler { call, result ->
            when (call.method) {
                "listen" -> {
                    startListening(result)
                }
                "stopListening" -> {
                    stopListening(result)
                }
                "playAudio" -> {
                    val base64Data = call.argument<String>("base64")
                    if (!base64Data.isNullOrBlank()) {
                        playBase64Audio(base64Data, result)
                    } else {
                        result.error("invalid_arg", "Audio base64 string is required.", null)
                    }
                }
                "stopAudio" -> {
                    stopAudio(result)
                }
                "playChime" -> {
                    val chimeType = call.argument<String>("type") ?: "listen"
                    playChimeEffect(chimeType)
                    result.success(true)
                }
                "speak" -> {
                    val text = call.argument<String>("text").orEmpty()
                    speakText(text, result)
                }
                "stopSpeaking" -> {
                    stopSpeaking(result)
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onInit(status: Int) {
        ttsReady = status == TextToSpeech.SUCCESS
        if (ttsReady) {
            try {
                textToSpeech?.language = Locale.UK
            } catch (_: Exception) {
                textToSpeech?.language = Locale.getDefault()
            }
        }
    }

    private fun playChimeEffect(type: String) {
        try {
            when (type) {
                "listen" -> toneGen?.startTone(ToneGenerator.TONE_PROP_BEEP, 120)
                "ack" -> toneGen?.startTone(ToneGenerator.TONE_PROP_ACK, 160)
                "error" -> toneGen?.startTone(ToneGenerator.TONE_PROP_NACK, 200)
                else -> toneGen?.startTone(ToneGenerator.TONE_PROP_BEEP, 100)
            }
        } catch (_: Exception) {}
    }

    private fun startListening(result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED
        ) {
            pendingSpeechResult = result
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), audioPermissionRequest)
            return
        }

        beginSpeechRecognition(result)
    }

    private fun stopListening(result: MethodChannel.Result) {
        mainHandler.post {
            try {
                speechRecognizer?.stopListening()
            } catch (_: Exception) {}
            result.success(true)
        }
    }

    private fun beginSpeechRecognition(result: MethodChannel.Result) {
        // Cancel any pending result cleanly
        pendingSpeechResult?.error("cancelled", "A new listening session was initiated.", null)
        pendingSpeechResult = result

        mainHandler.post {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                // Fallback directly to Google Speech Recognizer Activity
                launchSpeechRecognizerIntent()
                return@post
            }

            try {
                speechRecognizer?.destroy()
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                    override fun onReadyForSpeech(params: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(rmsdB: Float) {}
                    override fun onBufferReceived(buffer: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onPartialResults(partialResults: Bundle?) {}
                    override fun onEvent(eventType: Int, params: Bundle?) {}

                    override fun onError(error: Int) {
                        // On recognition errors (e.g. no match, client error, busy), fall back to intent if not yet returned
                        if (error == SpeechRecognizer.ERROR_NO_MATCH ||
                            error == SpeechRecognizer.ERROR_CLIENT ||
                            error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY ||
                            error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                        ) {
                            launchSpeechRecognizerIntent()
                            return
                        }

                        val message = when (error) {
                            SpeechRecognizer.ERROR_AUDIO -> "Audio recording error."
                            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission denied."
                            SpeechRecognizer.ERROR_NETWORK -> "Network error during speech recognition."
                            SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Speech recognition network timeout."
                            SpeechRecognizer.ERROR_SERVER -> "Speech server error."
                            else -> "Speech recognition error ($error)."
                        }
                        pendingSpeechResult?.error("speech_error", message, error)
                        pendingSpeechResult = null
                    }

                    override fun onResults(results: Bundle?) {
                        val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                        val spokenText = matches?.firstOrNull().orEmpty()
                        if (spokenText.isNotBlank()) {
                            pendingSpeechResult?.success(spokenText)
                            pendingSpeechResult = null
                        } else {
                            launchSpeechRecognizerIntent()
                        }
                    }
                })

                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
                    putExtra(RecognizerIntent.EXTRA_PROMPT, "Command JARVIS...")
                }
                speechRecognizer?.startListening(intent)
            } catch (e: Exception) {
                // If createSpeechRecognizer threw exception on this device, use Intent fallback
                launchSpeechRecognizerIntent()
            }
        }
    }

    private fun launchSpeechRecognizerIntent() {
        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to JARVIS...")
            }
            startActivityForResult(intent, speechIntentRequestCode)
        } catch (e: Exception) {
            pendingSpeechResult?.error("speech_unavailable", "Voice recognition dialog unavailable: ${e.message}", null)
            pendingSpeechResult = null
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == speechIntentRequestCode) {
            val res = pendingSpeechResult ?: return
            if (resultCode == Activity.RESULT_OK && data != null) {
                val matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                val spokenText = matches?.firstOrNull().orEmpty()
                res.success(spokenText)
            } else {
                res.error("speech_cancelled", "Voice recognition cancelled or no speech detected.", null)
            }
            pendingSpeechResult = null
        }
    }

    private fun playBase64Audio(base64Data: String, result: MethodChannel.Result) {
        try {
            val decodedBytes = Base64.decode(base64Data, Base64.DEFAULT)
            val tempFile = File(cacheDir, "jarvis_voice_${System.currentTimeMillis()}.mp3")
            FileOutputStream(tempFile).use { it.write(decodedBytes) }

            mainHandler.post {
                try {
                    mediaPlayer?.stop()
                    mediaPlayer?.release()
                } catch (_: Exception) {}

                mediaPlayer = MediaPlayer().apply {
                    setDataSource(tempFile.absolutePath)
                    setOnPreparedListener { mp ->
                        mp.start()
                        result.success(true)
                    }
                    setOnCompletionListener { mp ->
                        mp.release()
                        mediaPlayer = null
                        try {
                            tempFile.delete()
                        } catch (_: Exception) {}
                    }
                    setOnErrorListener { mp, _, _ ->
                        mp.release()
                        mediaPlayer = null
                        try {
                            tempFile.delete()
                        } catch (_: Exception) {}
                        false
                    }
                    prepareAsync()
                }
            }
        } catch (e: Exception) {
            result.error("audio_play_error", "Failed to play neural speech audio: ${e.message}", null)
        }
    }

    private fun stopAudio(result: MethodChannel.Result) {
        mainHandler.post {
            try {
                mediaPlayer?.stop()
                mediaPlayer?.release()
                mediaPlayer = null
            } catch (_: Exception) {}
            result.success(true)
        }
    }

    private fun speakText(text: String, result: MethodChannel.Result) {
        if (text.isBlank()) {
            result.success(false)
            return
        }
        if (!ttsReady) {
            result.error("tts_unavailable", "Text to speech engine not initialized.", null)
            return
        }
        textToSpeech?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis-tts")
        result.success(true)
    }

    private fun stopSpeaking(result: MethodChannel.Result) {
        mainHandler.post {
            try {
                textToSpeech?.stop()
            } catch (_: Exception) {}
            result.success(true)
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == audioPermissionRequest) {
            val result = pendingSpeechResult ?: return
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                beginSpeechRecognition(result)
            } else {
                result.error("permission_denied", "Microphone permission is required for voice commanding.", null)
                pendingSpeechResult = null
            }
        }
    }

    override fun onDestroy() {
        mainHandler.post {
            try {
                speechRecognizer?.destroy()
                mediaPlayer?.release()
                textToSpeech?.stop()
                textToSpeech?.shutdown()
                toneGen?.release()
            } catch (_: Exception) {}
        }
        super.onDestroy()
    }
}
