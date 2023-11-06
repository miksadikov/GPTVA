import openai
import sounddevice as sd
import vosk, queue, json
import pyaudio
import time
from speechkit import Session, SpeechSynthesis

openai.api_key = 'YOUR_OPENAI_API_KEY'
oauth_token = "YOUR_YANDEX_OAUTH_TOKEN"
catalog_id = "YOUR_YANDEX_CATALOG_ID"

# ============================= vosk ===============================
q = queue.Queue()

devices = sd.query_devices()
print("Select device id: \n", devices)

dev_id = 0 # default

try:
    dev_id = int(input())
except ValueError:
    print("Using default value: 0")

samplerate = int(sd.query_devices(dev_id, 'input')['default_samplerate'])
# ===================================================================

# ============================= chatgpt =============================
messages = [ {"role": "system", "content":
              "You are a intelligent assistant."} ]
# ===================================================================

# ============================ speechkit ============================
session = Session.from_yandex_passport_oauth_token(oauth_token, catalog_id)

# Создаем экземляр класса `SpeechSynthesis`, передавая `session`,
# который уже содержит нужный нам IAM-токен
# и другие необходимые для API реквизиты для входа
synthesizeAudio = SpeechSynthesis(session)

def pyaudio_play_audio_function(audio_data, num_channels=1,
                                sample_rate=16000, chunk_size=4000) -> None:
    """
    Воспроизводит бинарный объект с аудио данными в формате lpcm (WAV)
    :param bytes audio_data: данные сгенерированные спичкитом
    :param integer num_channels: количество каналов, спичкит генерирует
        моно дорожку, поэтому стоит оставить значение `1`
    :param integer sample_rate: частота дискретизации, такая же
        какую вы указали в параметре sampleRateHertz
    :param integer chunk_size: размер семпла воспроизведения,
        можно отрегулировать если появится потрескивание
    """
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=num_channels,
        rate=sample_rate,
        output=True,
        frames_per_buffer=chunk_size
    )

    try:
        for i in range(0, len(audio_data), chunk_size):
            stream.write(audio_data[i:i + chunk_size])
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

sample_rate = 16000
chat = False
start_chat_msgs = ['поговорим на английском', 'говорим на английском', 'английском', 'поговорим на русском', 'говорим на русском', 'русском',]
russian = 'русском'
english = 'английском'
in_english = False
russian_voice = 'zahar'
english_voice = 'john'
# ===================================================================

try:
    model = vosk.Model(r"C:\Users\user\Downloads\model_ru")
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=dev_id, dtype='int16', channels=1, callback=(lambda i, f, t, s: q.put(bytes(i)))):
        rec = vosk.KaldiRecognizer(model, samplerate)

        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                data = json.loads(rec.Result())["text"]
                print("Recognized: " + data)
                if data:
                    if chat == False:
                        if any(start in data for start in start_chat_msgs):
                            # start new chat
                            chat = True
                            if english in data:
                                voice = english_voice
                                model = vosk.Model(r"C:\Users\user\Downloads\model_en")
                                with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=dev_id, dtype='int16', channels=1, callback=(lambda i, f, t, s: q.put(bytes(i)))):
                                    rec = vosk.KaldiRecognizer(model, samplerate)
                                audio_data = synthesizeAudio.synthesize_stream(
                                    text = "sure, let's talk",
                                    voice = voice, format = 'lpcm', sampleRateHertz = sample_rate)
                                pyaudio_play_audio_function(audio_data, sample_rate = sample_rate)
                                q.queue.clear()
                                start = time.time()
                            else:
                                voice = russian_voice
                                audio_data = synthesizeAudio.synthesize_stream(
                                    text = 'хорошо, давайте попробуем',
                                    voice = voice, format = 'lpcm', sampleRateHertz = sample_rate)
                                pyaudio_play_audio_function(audio_data, sample_rate = sample_rate)
                                q.queue.clear()
                                start = time.time()
                    else:
                        messages.append({"role": "user", "content": data},)
                        openai_chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
                        reply = openai_chat.choices[0].message.content
                        print(f"ChatGPT: {reply}")
                        messages.append({"role": "assistant", "content": reply})

                        audio_data = synthesizeAudio.synthesize_stream(
                            text = reply, voice = voice, format = 'lpcm', sampleRateHertz = sample_rate)
                        pyaudio_play_audio_function(audio_data, sample_rate = sample_rate)
                        q.queue.clear()
                        start = time.time()

            else:
                data = json.loads(rec.PartialResult())["partial"]
                if chat == True:
                    end = time.time()
                    print(end - start)
                    if end - start > 10:
                        if in_english:
                            text = 'New chat'
                        else:
                            text = 'Новый чат'
                        audio_data = synthesizeAudio.synthesize_stream(
                                text = text, voice = voice, format = 'lpcm', sampleRateHertz = sample_rate)
                        pyaudio_play_audio_function(audio_data, sample_rate = sample_rate)
                        q.queue.clear()
                        chat = False


except KeyboardInterrupt:
    print('\nDone')
