from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
import os

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

#test message
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="what is the exact value of e^4 to 5 decimal places"
)

#default EventHandler override from OAI Assistants docs
class EventHandler(AssistantEventHandler):    
  @override
  def on_text_created(self, text) -> None:
    print(f"\nassistant > ", end="", flush=True)
      
  @override
  def on_text_delta(self, delta, snapshot):
    print(delta.value, end="", flush=True)
      
  def on_tool_call_created(self, tool_call):
    print(f"\nassistant > {tool_call.type}\n", flush=True)
  
  def on_tool_call_delta(self, delta, snapshot):
    if delta.type == 'code_interpreter':
      if delta.code_interpreter.input:
        print(delta.code_interpreter.input, end="", flush=True)
      if delta.code_interpreter.outputs:
        print(f"\n\noutput >", flush=True)
        for output in delta.code_interpreter.outputs:
          if output.type == "logs":
            print(f"\n{output.logs}", flush=True)

with client.beta.threads.runs.stream(
  thread_id=thread.id,
  assistant_id=asstID,
  event_handler=EventHandler(),
) as stream:
  stream.until_done()
  print('\n')

