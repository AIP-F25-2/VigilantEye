import numpy as np
import librosa
import tensorflow as tf
import torchaudio
import csv
from yamnet_classmap_dict import CLASS_MAP 


MODEL_PATH = "model"   # folder with saved_model.pb

print(" Loading model from", MODEL_PATH)
classifier = tf.saved_model.load(MODEL_PATH)
print(" Model loaded.")


def extract_features(audio_path: str, sr: int = 16000):
    y, sr = librosa.load(audio_path, sr=sr, mono=True)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    feat = np.mean(mfcc.T, axis=0)
    return feat.reshape(1, -1)

# Function to load MP3 and resample
def load_mp3_for_yamnet(filename):
    """
    Load an MP3 file, convert to 16 kHz mono waveform,
    and return as float32 numpy array for YAMNet.
    """
    # Load MP3 (shape: [channels, samples])
    waveform, sr = torchaudio.load(filename)   
    # Convert to mono if needed
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)    
    # Resample to 16kHz
    if sr != 16000:
        waveform = torchaudio.functional.resample(waveform, orig_freq=sr, new_freq=16000)    
    # Convert to 1D float32 numpy array
    waveform = waveform.squeeze().numpy().astype("float32")
    return waveform

def predict_audio(audio_path: str) -> str:
    features = load_mp3_for_yamnet(audio_path)
    infer = classifier(tf.convert_to_tensor(features))
    outputs = infer(tf.constant(features, dtype=tf.float32))
    probs = list(outputs.values())[0].numpy()
    pred_idx = int(np.argmax(probs, axis=1)[0])
    return CLASS_MAP.get(pred_idx, "UNKNOWN")


def predict_audio_class(audio_path, threshold=0.2):
    """
    Predicts the audio class from YAMNet.
    Returns the class name or 'UNKNOWN' if below threshold.
    """
    # Load audio
    waveform = load_mp3_for_yamnet(audio_path)
    
    # Run YAMNet
    scores, embeddings, spectrogram = classifier(tf.convert_to_tensor(waveform))
    
    # Average scores across frames
    mean_scores = np.mean(scores.numpy(), axis=0)
    
    # Get predicted class index and probability
    pred_idx = int(np.argmax(mean_scores))
    pred_prob = mean_scores[pred_idx]
    
    # Return class if above threshold, else UNKNOWN
    #if pred_prob < threshold:
    #    return "UNKNOWN"
    return CLASS_MAP.get(pred_idx, "UNKNOWN")

# Add this function below your existing code
import matplotlib.pyplot as plt

def show_waveform(audio_path):
    """
    Visualize the waveform for any audio file.
    """
    waveform, sr = torchaudio.load(audio_path)
    waveform = waveform.mean(dim=0).numpy()  # convert stereo → mono
    plt.figure(figsize=(10, 3))
    plt.plot(waveform)
    plt.title(f"Waveform: {audio_path}")
    plt.xlabel("Time (samples)")
    plt.ylabel("Amplitude")
    plt.show()