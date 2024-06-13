# termBuddy

GPT wrappers in bash are fun and ChatGPT no longer tickles my wickle

`OPENAI_API_KEY` and `OPENAI_ASSISTANT_KEY` env variables must be set before using this

```sh
export OPENAI_API_KEY=<yourKeyHere>
export OPENAI_ASSISTANT_KEY=<yourKeyHere>

#optional, but helpful
alias chat="python3 <path-to-worker.py>"
```

I would add those to your `.zshrc` or `.bashrc` or whatever, but you do you

For single use, pass in your query as a command line arg like this 

```sh
python3 worker.py "what is the capital of michigan"

#if you set the alias
chat "what is the capital of michigan"
```

Or, if you just call `python3 worker.py` (just `chat` with the alias), you will continuously be prompted for queries until typing `exit` or `quit`
