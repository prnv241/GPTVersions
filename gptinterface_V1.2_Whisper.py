import tkinter as tk
import threading
import pyaudio
import wave
import speech_recognition as sr
import openai
import pyttsx3
import subprocess
from tkinter import scrolledtext
from time import sleep


openai.api_key = ""
# Change this to the GPT-3.5 Turbo model you want to use
model_engine = "gpt-4"


class GUI:

    def __init__(self):

        self.root = tk.Tk()
        self.root.title("JAMES: AI Personal Assistant")
        self.root.geometry("500x600")

        # Create UI elements
        self.conversation = scrolledtext.ScrolledText(self.root, wrap="word")
        self.conversation.configure(
            font=("Calibri", 12), bg="#F7F7F7", fg="#000000", padx=10, pady=10)
        self.conversation.pack(side="top", fill="both", expand=True)
        # Configure the tag for right alignment
        self.conversation.tag_config("right", justify='right')
        self.conversation.tag_config("left", justify='left')

        self.speak_button = tk.Button(
            self.root, text="Speak", command=self.toggle_recording)
        self.speak_button.configure(
            font=("Arial", 14), bg="#4CAF50", fg="#FFFFFF")
        self.speak_button.pack(side="bottom", pady=10)

        # Recording related
        self.recording = False
        self.frames = []
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.filename = "recording.wav"
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.event = threading.Event()

        self.conversationHistory = [
            {"role": "system", "content": "You are JAMES, an AI personal assistant. You have to strictly follow these instructions while generating response. Response should concise and accurate. Only when asked to perform a task which can be done using windows command prompt follow further intructions else respond as you would normally. Respond with commands required to perform the task without any explaination. Each command should start with `* and end with *` and should not contain any new lines or quotes. Generated commands will be executed in new cmd window on users computer automatically by a program monitoring your responses. Output if any will be given to you by the program as CMD OUTPUT: <output>. Use that output to inform user about status of completion of given task. If task completion can be verified by issuing further commands, ask the user if you can do so. Dont forget to include a command for navigating to working directory everytime you issue commands."}]
        self.first_Prompt = True

        self.root.mainloop()

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.start_recording()
            self.speak_button.config(text="Stop")
            self.speak_button.configure(
                font=("Arial", 14), bg="#FF0000", fg="#FFFFFF")
        else:
            self.stop_recording()
            self.speak_button.config(text="Record")
            self.speak_button.configure(
                font=("Arial", 14), bg="#4CAF50", fg="#FFFFFF")

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
        try:
            self.stream.stop_stream()
            self.event.set()
            self.save_recording()
            self.convert_to_text()
            threading.Thread(target=self.converse_with_chatgpt).start()

        except Exception as e:
            print(
                'Error occured while converting speech to text and executing the command. More info : ' + str(e))

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

    def remove_code_from_response(self):
        temp_answer = self.answer
        for command in self.commands:
            temp_answer = str(temp_answer).replace("*" + command + "*", "")
        print("filtered response: " + temp_answer)
        return temp_answer

    def get_commands_from_response(self):
        self.commands = []
        start_idx = 0
        while start_idx < len(self.answer):
            start_idx = self.answer.find("*", start_idx)
            if start_idx == -1:
                break
            end_idx = self.answer.find("*", start_idx + 1)
            if end_idx == -1:
                break
            command = self.answer[start_idx+1:end_idx]
            self.commands.append(command)
            start_idx = end_idx + 1

    def execute_commands_in_cmd_window_and_get_output(self):
        self.cmdoutput = ""
        process = subprocess.run(
            ' & '.join(self.commands), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = process.stdout.decode('utf-8')
        if (len(output) != 0):
            self.cmdoutput = output

        print("Generated output: " + self.cmdoutput)

    def get_gpt_response_for_conversation(self):
        response = openai.ChatCompletion.create(
            model=model_engine,
            messages=self.conversationHistory,
            max_tokens=512,
            temperature=0.7
        )
        self.answer = response['choices'][0]['message']['content']

    def gui_print_user_first_prompt(self):
        if (self.first_Prompt == True):
            self.first_Prompt = False
        else:
            self.conversation.insert(
                tk.END, "\n--------------------------------------------------------------------------------------------", "left")

        self.conversation.insert(tk.END, "\nUser : " + self.text, "right")
        self.conversation.see(tk.END)

    def gui_print_gpt_first_response(self):
        self.conversation.insert(
            tk.END, "\n--------------------------------------------------------------------------------------------", "left")
        self.conversation.insert(
            tk.END, "\nGPT: " + self.answer, "left")
        self.conversation.see(tk.END)

    def gui_print_cmd_first_response(self):
        self.conversation.insert(
            tk.END, "\n--------------------------------------------------------------------------------------------", "left")
        self.conversation.insert(
            tk.END, "\nCMD OUTPUT: " + self.cmdoutput, "right")
        self.conversation.see(tk.END)

    def convert_to_text(self):
        audio_file = open("recording.wav", "rb")
        transcript = openai.Audio.translate("whisper-1", audio_file)
        self.text = transcript['text']

    def converse_with_chatgpt(self):
        # Initialize Text to speechW
        engine = pyttsx3.init()

        # AI Instructions and user prompt
        self.conversationHistory.append({"role": "user", "content": self.text})

        # Print users prompt in GUI
        self.gui_print_user_first_prompt()

        # Get response from gpt for users prompt
        self.get_gpt_response_for_conversation()

        # Append response in conversation history
        self.conversationHistory.append(
            {"role": "assistant", "content": self.answer})

        # print gpt first response on GUI
        self.gui_print_gpt_first_response()

        # Extract commands from GPT response
        self.get_commands_from_response()

        # Play GPT's response using text to speech
        engine.say(self.remove_code_from_response())

        if (len(self.commands) != 0):

            # Execute the commands in cmd window
            self.execute_commands_in_cmd_window_and_get_output()

            # add the output as a separate message in the conversation history
            self.conversationHistory.append(
                {"role": "user", "content": "CMD OUTPUT: " + self.cmdoutput})

            # display the CMD output in the GUI
            self.gui_print_cmd_first_response()

            # Get GPT second response for conversation
            self.get_gpt_response_for_conversation()

            # Append GPT second response
            self.conversationHistory.append(
                {"role": "assistant", "content": self.answer})

            # print second response on gui window
            self.gui_print_gpt_first_response()

            # Get commands for the reponse and remove those commands from text to speech
            self.get_commands_from_response()
            engine.say(self.remove_code_from_response())

        engine.runAndWait()


if __name__ == "__main__":
    GUI()
