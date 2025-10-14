import json
import subprocess

data = json.load(open("./data/one.json"))[0]
qid = data["question_id"]

prompt = (
    f"Read the following multi-session conversation and answer the question.\n\n"
    f"Question: {data['question']}\n\n"
    f"Conversation sessions:\n"
)
for i, sess in enumerate(data["haystack_sessions"], 1):
    print(f"...adding session {i}, {len(sess)} msg", flush=True)
    prompt += f"\nSession {i}\n"
    for msg in sess:
        role = msg["role"].capitalize()
        prompt += f"{role}: {msg['content']}\n"

prompt += "\nFinal answer:"

result = subprocess.run(
    ["ollama", "run", "llama3.2"],
    input=prompt.encode(),
    capture_output=True,
)
answer = result.stdout.decode().strip()

out = {"question_id": qid, "hypothesis": answer}
with open("one_out.jsonl", "w") as f:
    f.write(json.dumps(out) + "\n")

print(f"done {out}")
