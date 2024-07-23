from openai import OpenAI
client = OpenAI()

for fileObject in client.files.list().data:
    client.files.delete(fileObject.id)

