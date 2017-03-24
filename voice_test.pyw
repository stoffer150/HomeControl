import pyaudio
from subprocess import call
import speech_recognition as sr

p = pyaudio.PyAudio()
print(p.get_default_input_device_info())
r = sr.Recognizer()
r.energy_threshold=4000
with sr.Microphone() as source:
    r.adjust_for_ambient_noise(source, duration = 3)
    print(r.energy_threshold)
    #r.energy_threshold = 1
    print('listening..')
    audio = r.listen(source)

print('processing')

try:
    message = (r.recognize_google(audio, language = 'en-us', show_all=False))
    call(["espeak", message])
except:
    call(['espeak', 'Could not understand you'])

