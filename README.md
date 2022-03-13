# 8047-mjr-project
Creating a realtime staganography application using music streaming as the cover.

The system works by livestreaming the audio using a Vorpis encoded OGG file and sending out the data as a pickled nparray.
The data is then decrypted and played through the sounddevice in real time.
While this is happening a string of bytes can be encoded into the data using a nparray diguising it as part of the audio data. This causes the data to become sound fuzzy on some higher quality headphones but can be hidden by changing the key that the data is being disguised with. The drawback of this is that the more common sounds are more likely to be falsly extracted from the audio stream.

