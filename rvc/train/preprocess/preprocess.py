from multiprocessing import cpu_count
import os
import sys
import traceback

from scipy import signal
from scipy.io import wavfile
import librosa
import numpy as np

now_directory = os.getcwd()
sys.path.append(now_directory)

from rvc.lib.utils import load_audio
from rvc.train.slicer import Slicer

experiment_directory = sys.argv[1]
input_root = sys.argv[2]
sampling_rate = int(sys.argv[3])
percentage = float(sys.argv[4])
num_processes = cpu_count()

no_parallel = "True"
import multiprocessing


class PreProcess:
    def __init__(self, sr, exp_dir, per=3.0):
        self.slicer = Slicer(
            sr=sr,
            threshold=-42,
            min_length=1500,
            min_interval=400,
            hop_size=15,
            max_sil_kept=500,
        )
        self.sr = sr
        self.b_high, self.a_high = signal.butter(N=5, Wn=48, btype="high", fs=self.sr)
        self.per = per
        self.overlap = 0.3
        self.tail = self.per + self.overlap
        self.max_amplitude = 0.9
        self.alpha = 0.75
        self.exp_dir = exp_dir
        self.gt_wavs_dir = "%s/0_gt_wavs" % exp_dir
        self.wavs16k_dir = "%s/1_16k_wavs" % exp_dir
        os.makedirs(self.exp_dir, exist_ok=True)
        os.makedirs(self.gt_wavs_dir, exist_ok=True)
        os.makedirs(self.wavs16k_dir, exist_ok=True)

    def normalize_and_write(self, tmp_audio, idx0, idx1):
        tmp_max = np.abs(tmp_audio).max()
        if tmp_max > 2.5:
            print("%s-%s-%s-filtered" % (idx0, idx1, tmp_max))
            return
        tmp_audio = (tmp_audio / tmp_max * (self.max_amplitude * self.alpha)) + (
            1 - self.alpha
        ) * tmp_audio
        wavfile.write(
            "%s/%s_%s.wav" % (self.gt_wavs_dir, idx0, idx1),
            self.sr,
            tmp_audio.astype(np.float32),
        )
        tmp_audio = librosa.resample(
            tmp_audio, orig_sr=self.sr, target_sr=16000
        )  # , res_type="soxr_vhq"
        wavfile.write(
            "%s/%s_%s.wav" % (self.wavs16k_dir, idx0, idx1),
            16000,
            tmp_audio.astype(np.float32),
        )

    def process_audio(self, path, idx0):
        try:
            audio = load_audio(path, self.sr)
            audio = signal.lfilter(self.b_high, self.a_high, audio)

            idx1 = 0
            for audio_segment in self.slicer.slice(audio):
                i = 0
                while 1:
                    start = int(self.sr * (self.per - self.overlap) * i)
                    i += 1
                    if len(audio_segment[start:]) > self.tail * self.sr:
                        tmp_audio = audio_segment[
                            start : start + int(self.per * self.sr)
                        ]
                        self.normalize_and_write(tmp_audio, idx0, idx1)
                        idx1 += 1
                    else:
                        tmp_audio = audio_segment[start:]
                        idx1 += 1
                        break
                self.normalize_and_write(tmp_audio, idx0, idx1)
        except:
            print("%s->%s" % (path, traceback.format_exc()))

    def process_audio_multiprocessing(self, infos):
        for path, idx0 in infos:
            self.process_audio(path, idx0)

    def process_audio_multiprocessing_input_directory(self, input_root, num_processes):
        try:
            infos = [
                ("%s/%s" % (input_root, name), idx)
                for idx, name in enumerate(sorted(list(os.listdir(input_root))))
            ]
            if no_parallel:
                for i in range(num_processes):
                    self.process_audio_multiprocessing(infos[i::num_processes])
            else:
                processes = []
                for i in range(num_processes):
                    p = multiprocessing.Process(
                        target=self.process_audio_multiprocessing,
                        args=(infos[i::num_processes],),
                    )
                    processes.append(p)
                    p.start()
                for i in range(num_processes):
                    processes[i].join()
        except:
            print("Fail. %s" % traceback.format_exc())


def preprocess_training_set(input_root, sr, num_processes, exp_dir, per):
    pp = PreProcess(sr, exp_dir, per)
    print("Starting preprocessing...")
    pp.process_audio_multiprocessing_input_directory(input_root, num_processes)
    print("Preprocessing completed!")


if __name__ == "__main__":
    preprocess_training_set(
        input_root, sampling_rate, num_processes, experiment_directory, percentage
    )