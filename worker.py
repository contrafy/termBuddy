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


#default EventHandler override from OAI Assistants docs
class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        #handling markdown like this for now, sets the color of terminal to a neon color
        #for headers, actual printing is all done in the final 'else' branch
        if('##' in delta.value):
            print(f"\033[95m", end="", flush=True)
        elif('#' in delta.value):
            print(f"\033[96m", end="", flush=True)

        #resets the terminal text color to default
        #might as well do it on every newline
        elif('\n' in delta.value):
            print(f"\033[0m", flush=True)
        else:
            print(delta.value, end="", flush=True)

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

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
