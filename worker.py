from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import os
import sys

client = OpenAI()

#file to hold the threadID of the current machines thread
session_file = os.path.expanduser('~/.codeHelperSession')

vectorStore = client.beta.vector_stores.retrieve(vector_store_id="vs_VYKgsv07Be311LWb0CuLnSzn")

def addFileToVectorStore(path):
    file = client.files.create(
        file=open(path, "rb"),
        purpose="assistants"
    )
    vectorStoreFile = client.beta.vector_stores.files.create(
        vector_store_id="vs_VYKgsv07Be311LWb0CuLnSzn",
        file_id=file.id
    )
    print(vectorStoreFile)

def getOAIassistants():
    my_assistants = client.beta.assistants.list(
        order="desc",
        limit="20",
    )
    print(my_assistants.data)


def executeRun():
    with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=os.getenv("OPENAI_ASSISTANT_KEY"),
            event_handler=EventHandler(),
            ) as stream:
        stream.until_done()
    print('\n')

#appends messages as they come in to the log file
def appendToHelperFile(text):
    with open(session_file, 'a') as f:
        f.write(text)

#if no thread exists for this machine, create it and add the threadID to a file
#so that it can be retrieved in future sessions
if not os.path.exists(session_file):
    thread = client.beta.threads.create()

    with open(session_file, 'w') as f:
        f.write(thread.id + '\n')

#if the file exists, read the ID and use that to retrieve the thread
else:
    with open(session_file) as f:
        session_id = f.readline().strip()
    thread = client.beta.threads.retrieve(thread_id=session_id)

print("\nThread ID: " + thread.id)

#potentially make a config file to create the assistant with custom settings
#instead of forcefully using my assistant instance
asstID = os.getenv("OPENAI_ASSISTANT_ID")

#adds a message to the thread but does not execute the run
#(executing a run sends the whole thread to the assistant and returns output)
def addMessage(msg):
    message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=msg
            )


#OpenAI Streaming SDK to handle model output in real time
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.codeBlock = False
        self.codeBlockEncountered = False

        #use this buffer to detect markdown since delimiters can be
        #split between deltas
        self.buffer = ""

        #for the pretty lines
        self.terminalWidth = os.get_terminal_size().columns

    @override
    def on_text_created(self, text) -> None:
        print(f"\n\033[0mgpt-4o-mini > ", end="", flush=True)
        appendToHelperFile("\n\ngpt-4o-mini > ")

    #just a final check to make sure everything gets output
    @override
    def on_text_done(self, text):
        print(self.buffer, end="", flush=True)
        appendToHelperFile(self.buffer)

        print(f"\033[0m", end="", flush=True)


    #prints a pretty line before and after code blocks
    def printPrettyLine(self):
        print('-' * self.terminalWidth, end="", flush=True)
        appendToHelperFile('-' * self.terminalWidth)

    #sends buffer to stdout, appends it to the helper file and flushes buffer
    def clearBuffer(self):
        print(self.buffer, end="", flush=True)
        appendToHelperFile(self.buffer)
        self.buffer = ""

    #output is placed into an intermediate buffer before being output to process text rendering like markdown and code blocks
    def processBuffer(self):
        #handle code blocks and bold markdown.... fuck bold markdown if('`' in self.buffer):
        #detected a code block delimiter
        if('```' in self.buffer):
            #toggle the codeBlock boolean and use that to disable
            #other formatting for the time being
            self.codeBlock = not self.codeBlock

            #if this is the beginning of a code block, change the text color
            #but wait until the newline to print the pretty line
            if self.codeBlock:
                print(f"\n\033[92m", end="", flush=True)

                #don't actually print the ```
                self.buffer = ""

                self.codeBlockEncountered = True

            #if its the end of one print another pretty line and reset the terminal color
            else:
                print()
                appendToHelperFile('\n')
                self.printPrettyLine()
                print()
                appendToHelperFile('\n')
                #print('\n' + ('-' * self.terminalWidth), flush=True)
                self.buffer = ""
                print(f"\033[0m", flush=True)                

        #handles `inline` code blocks
        elif(self.buffer.count('`') == 2 and '``' not in self.buffer):
            #append it to the file before applying the styles
            appendToHelperFile(self.buffer)

            #replace the opening delimeter with the color code
            self.buffer = self.buffer.replace('`', f"\033[93m", 1)
            #replace the closing delimeter with the reset code
            self.buffer = self.buffer.replace('`', f"\033[0m")

            print(self.buffer, end="", flush=True)
            self.buffer = ""

        #handle markdown headers
        elif('###' in self.buffer and not self.codeBlock):
            print(f"\n\n\033[94m", end="", flush=True)
            appendToHelperFile(self.buffer)
            self.buffer = ""
        elif('##' in self.buffer and not self.codeBlock):
            print(f"\n\n\033[95m", end="", flush=True)
            appendToHelperFile(self.buffer)
            self.buffer = ""
        elif('#' in self.buffer and not self.codeBlock):
            print(f"\n\n\033[96m", end="", flush=True)
            appendToHelperFile(self.buffer)
            self.buffer = ""

        #handle bold and italic (underline)
        elif('*' in self.buffer):
            if(self.buffer.count('**') == 2 and self.buffer.count('*') % 2 == 0):
                appendToHelperFile(self.buffer)
                self.buffer = self.buffer.replace('**', f"\033[1m", 1)
                self.buffer = self.buffer.replace('**', f"\033[0m")

                #in case of nested bold and italic elements
                if(self.buffer.count('*') == 0):
                    print(self.buffer, end="", flush=True)
                    self.buffer = ""
            elif(self.buffer.count('*') == 2 and '**' not in self.buffer):
                appendToHelperFile(self.buffer)
                self.buffer = self.buffer.replace('*', f"\033[4m", 1)
                self.buffer = self.buffer.replace('*', f"\033[0m") 
                if(self.buffer.count('*') == 0):
                    print(self.buffer, end="", flush=True)
                    self.buffer = ""

        #reset terminal color to default   
        elif('\n' in self.buffer and not self.codeBlock):
            print(f"\033[0m" + self.buffer, end="", flush=True)
            appendToHelperFile(self.buffer)
            self.buffer = ""

        #this is solely to make sure the language of the code block is
        #printed above the code block instead of inside it, in the same color 
        elif('\n' in self.buffer and self.codeBlockEncountered):
            self.clearBuffer()
            appendToHelperFile(self.buffer)
            self.printPrettyLine()
            print('\n')
            self.codeBlockEncountered = False

        #handle all normal text
        else:
            self.clearBuffer()

    #as response text is received, add to buffer and processBuffer() will
    #handle formatting accordingly 
    @override
    def on_text_delta(self, delta, snapshot):
        self.buffer += delta.value
        self.processBuffer()

    def on_tool_call_created(self, tool_call):
        print(f"\n\n\033[94m{tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(f"\033[94m" + delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\033[0m\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)

import xml.etree.ElementTree as ET

#the file 'mapping.xml' contains a shitton of unicode mappings including latex
#this function returns a dictionary of latex/unicode pairs in the format '\\Sigma': 'Σ'
def parseLatexMappings(inFile):
    tree = ET.parse(inFile)
    root = tree.getroot()
    texUnicode = {}

    for character in root.findall(".//character"):
        tex = character.find(".//latex")
        dec = character.get('dec')
        if tex is not None and dec is not None:
            try:
                unicodeChar = chr(int(dec))
                #maps the latex cmd (like \Sum) to its corresponding unicode char
                texUnicode[tex.text.strip()] = unicodeChar
            except ValueError:
                continue
    return texUnicode

#sends the thread in its current state to the LLM
#and prints/streams the response neatly in real time

#define strings that will quit
quitStrs = ['exit', 'quit']

from prompt_toolkit import prompt

#if no cmd line arguments are passed in, infinite loop getting input from the user
#and evaluating it
if len(sys.argv) == 1:
    userIn = ''
    while True:
       userIn = prompt("ask away: ")
       if(userIn.lower() in quitStrs):
           exit(0)
       addMessage(userIn)
       executeRun()
#also accepts a singular string argument that gets evaluated by the LLM
#and then exits
else:
    addFileToVectorStore("worker.py")
