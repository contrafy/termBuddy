from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import os
import sys

client = OpenAI()

#file to hold the threadID of the current machines thread
session_file = os.path.expanduser('~/.codeHelperSession')
#if no thread exists for this machine, create it and add the threadID to a file
#so that it can be retrieved in future sessions
if not os.path.exists(session_file):
    thread = client.beta.threads.create()

    with open(session_file, 'w') as f:
        f.write(thread.id)

#if the file exists, read the ID and use that to retrieve the thread
else:
    with open(session_file) as f:
        session_id = f.read().strip()
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
        print(f"\n\033[0massistant > ", end="", flush=True)

    #just a final check to make sure everything gets output
    @override
    def on_text_done(self, text):
        print(self.buffer, end="", flush=True)
        print(f"\033[0m", end="", flush=True)

    def processBuffer(self):
        #handle code blocks and bold markdown.... fuck bold markdown
        if('`' in self.buffer):
            #detected a code block delimiter
            if('```' in self.buffer):
                #toggle the codeBlock boolean and use that to disable
                #other formatting for the time being
                self.codeBlock = not self.codeBlock
                
                #if this is the beginning of a code block, change the text color
                #but wait until the newline to print the pretty line
                if self.codeBlock:
                    print(f"\n\033[92m", end="", flush=True)
                    self.buffer = ""

                    self.codeBlockEncountered = True

                #if its the end of one print another pretty line and reset the terminal color
                else:
                    print('-' * self.terminalWidth, flush=True)
                    self.buffer = ""
                    print(f"\033[0m", flush=True)                

            #handles `bold` markdown elements
            elif(self.buffer.count('`') == 2
                 and '``' not in self.buffer):
                #replace the opening delimeter with the color code
                self.buffer = self.buffer.replace('`', f"\033[93m", 1)
                #replace the closing delimeter with the reset code
                self.buffer = self.buffer.replace('`', f"\033[0m")

                print(self.buffer, end="", flush=True)
                self.buffer = ""

        #handle markdown headers
        elif('###' in self.buffer and not self.codeBlock):
            print(f"\n\n\033[94m", end="", flush=True)
            self.buffer = ""
        elif('##' in self.buffer and not self.codeBlock):
            print(f"\n\n\033[95m", end="", flush=True)
            self.buffer = ""
        elif('#' in self.buffer and not self.codeBlock):
            print(f"\n\n\033[96m", end="", flush=True)
            self.buffer = ""

        #reset terminal color to default   
        elif('\n' in self.buffer and not self.codeBlock):
            print(f"\033[0m" + self.buffer, end="", flush=True)
            self.buffer = ""

        #this is solely to make sure the language of the code block is
        #printed above the code block instead of inside it, in the same color 
        elif('\n' in self.buffer and self.codeBlockEncountered):
            print(self.buffer + ('-' * self.terminalWidth), flush=True)
            self.codeBlockEncountered = False
            self.buffer = ""
        
        #handle all normal text
        else:
            print(self.buffer, end="", flush=True)
            self.buffer = "" 

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
def executeRun():
  with client.beta.threads.runs.stream(
    thread_id=thread.id,
    assistant_id=os.getenv("OPENAI_ASSISTANT_KEY"),
    event_handler=EventHandler(),
  ) as stream:
    stream.until_done()
    print('\n')

#define strings that will quit
quitStrs = ['exit', 'quit']

#if no cmd line arguments are passed in, infinite loop getting input from the user
#and evaluating it
if len(sys.argv) == 1:
   userIn = ''
   while True:
      userIn = input("ask away: ")
      if(userIn.lower() in quitStrs):
          exit(0)
      addMessage(userIn)
      executeRun()
#also accepts a singular string argument that gets evaluated by the LLM
#and then exits
else:
  addMessage(sys.argv[1])
  executeRun()
