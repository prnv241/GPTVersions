import tkinter as tk
import threading
import pyaudio
import wave
import speech_recognition as sr
import openai
import pyttsx3
import re
import subprocess


openai.api_key = ""
# Change this to the GPT-3.5 Turbo model you want to use
model_engine = "gpt-3.5-turbo"


class GUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Speech to Text")
        self.root.geometry("800x400")

        self.recording = False
        self.frames = []
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.filename = "recording.wav"

        self.button = tk.Button(self.root, text="Record",
                                command=self.toggle_recording)
        self.button.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.p = pyaudio.PyAudio()
        self.stream = None
        self.event = threading.Event()
        self.conversation = []

        self.text = tk.Label(self.root, text="")
        self.text.place(relx=0.5, rely=0.3, anchor=tk.CENTER)
        self.next_tts_call = False

        self.root.mainloop()

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.start_recording()
            self.button.config(text="Stop")
        else:
            self.stop_recording()
            self.button.config(text="Record")

    def start_recording(self):
        self.frames = []
        self.stream = self.p.open(format=self.format,
                                  channels=self.channels,
                                  rate=self.rate,
                                  input=True,
                                  frames_per_buffer=self.chunk)
        self.event.clear()
        threading.Thread(target=self.record_frames).start()

    def stop_recording(self):
        self.stream.stop_stream()
        self.event.set()
        self.save_recording()
        threading.Thread(target=self.convert_to_text()).start()

    def record_frames(self):
        while not self.event.is_set():
            data = self.stream.read(self.chunk)
            self.frames.append(data)

    def save_recording(self):
        with wave.open(self.filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))

    def convert_to_text(self):
        r = sr.Recognizer()
        engine = pyttsx3.init()

        with sr.AudioFile(self.filename) as source:
            audio_data = r.record(source)

            try:
                text = r.recognize_google(audio_data)
                self.conversation.append({"role": "user", "content": "You have to strictly follow these instructions while generating a response  : 1) Response should be concise 2) When asked to perform a task which can be done using windows command prompt, Only respond with the commands required to do so and no explaination or steps or expected output. Each command should start with `* and end with *`. Generated commands will be executed on users computer and output if any will be given to you by user. If given, use that output to inform user about status of completion of given task. For all other prompts respond as you would normally. Prompt : " + text})
                self.text.config(text="User : " + text)
                response = openai.ChatCompletion.create(
                    model=model_engine,
                    messages=self.conversation,
                    max_tokens=512,
                    temperature=0.7
                )
                self.answer = response['choices'][0]['message']['content']
                self.conversation.append(
                    {"role": "assistant", "content": self.answer})
                self.text.config(text=self.text.cget(
                    "text") + "\nGPT: " + self.answer)

                engine.say(self.answer)

                commands = []
                start_idx = 0
                while start_idx < len(self.answer):
                    start_idx = self.answer.find("*", start_idx)
                    if start_idx == -1:
                        break
                    end_idx = self.answer.find("*", start_idx + 1)
                    if end_idx == -1:
                        break
                    command = self.answer[start_idx+1:end_idx]
                    commands.append(command)
                    start_idx = end_idx + 1

                if (len(commands) != 0):
                    cmdoutput = ""
                    for command in commands:
                        print("Executing command: " + command)
                        result = subprocess.run(
                            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                        output = result.stdout.decode("utf-8").strip()
                        print("Output of execution: " + output)
                        if (len(output) != 0):
                            cmdoutput += (output + "\n\n")

                    if (len(cmdoutput) != 0):
                        # add the output as a separate message in the conversation history
                        self.conversation.append(
                            {"role": "user", "content": "CMD OUTPUT: " + cmdoutput})

                        # display the output in the GUI
                        self.text.config(text=self.text.cget(
                            "text") + "\nCMDOUT: " + cmdoutput)

                        response = openai.ChatCompletion.create(
                            model=model_engine,
                            messages=self.conversation,
                            max_tokens=512,
                            temperature=0.7
                        )
                        self.answer = response['choices'][0]['message']['content']
                        self.conversation.append(
                            {"role": "assistant", "content": self.answer})
                        self.text.config(text=self.text.cget(
                            "text") + "\nGPT: " + self.answer)
                        engine.say(self.answer)

                engine.runAndWait()
            except Exception:
                print(
                    'Error occured while converting speech to text and executing the command')


if __name__ == "__main__":
    GUI()
