import argparse as ap
import sounddevice as sd
from time import time
from scipy.io.wavfile import write
import numpy as np
import tensorflow as tf
import tensorflow_io as tfio


# From input data (audio recorded), tensorflow conversion and squeeze
def get_audio_from_numpy(indata):
    indata = tf.convert_to_tensor(indata,dtype=tf.float32)
    indata = 2 * ((indata + 32768) / (32767 + 32768)) - 1
    indata = tf.squeeze(indata)

    return indata


# Creates the spectrogram from the given input data, giving the optimal parameters obtained from ex. 1.1
def get_spectrogram(indata, downsampling_rate, frame_length_in_s, frame_step_in_s):
    
    audio_padded = get_audio_from_numpy(indata)
    global samplingrate
    
    if downsampling_rate != samplingrate:
        sampling_rate_int64 = tf.cast(samplingrate, tf.int64)
        audio_padded = tfio.audio.resample(indata, sampling_rate_int64, downsampling_rate)

    sampling_rate_float32 = tf.cast(downsampling_rate, tf.float32)
    frame_length = int(frame_length_in_s * sampling_rate_float32)
    frame_step = int(frame_step_in_s * sampling_rate_float32)

    spectrogram = stft = tf.signal.stft(
        audio_padded, 
        frame_length=frame_length,
        frame_step=frame_step,
        fft_length=frame_length
    )
    spectrogram = tf.abs(stft)

    return spectrogram, downsampling_rate


def is_silence(indata, downsampling_rate, frame_length_in_s, dbFSthres, duration_thres):
    spectrogram, sampling_rate = get_spectrogram(
        indata,
        downsampling_rate,
        frame_length_in_s,
        frame_length_in_s
    )
    dbFS = 20 * tf.math.log(spectrogram + 1.e-6)
    energy = tf.math.reduce_mean(dbFS, axis=1)
    non_silence = energy > dbFSthres
    non_silence_frames = tf.math.reduce_sum(tf.cast(non_silence, tf.float32))
    non_silence_duration = (non_silence_frames + 1) * frame_length_in_s

    if non_silence_duration > duration_thres:
        return 0
    else:
        return 1


def callback(indata, frames, callback_time, status):
    """This is called (from a separate thread) for each audio block."""
    timestamp = time()
    if is_silence(indata,16000,0.008,-135,0.1) == 0:
        write(f'{timestamp}.wav', 16000, indata)
        
    
#parsing input parameter (--device)
parser = ap.ArgumentParser()
parser.add_argument('--device',type=int)
args = parser.parse_args()

samplingrate = 16000
with sd.InputStream(device=args.device, channels=1, dtype='int16', samplerate = samplingrate, blocksize = samplingrate, callback=callback):
    while True:
        key = input()
        if key in ('q', 'Q'):
            print('Stop recording.')
            break