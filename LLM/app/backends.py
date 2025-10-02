
import os
from typing import Iterable, List, Dict
from huggingface_hub import InferenceClient

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
    import torch
except Exception:
    AutoModelForCausalLM = None
    AutoTokenizer = None
    TextIteratorStreamer = None
    torch = None

class ChatBackend:
    def generate(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, stream: bool) -> Iterable[str]:
        raise NotImplementedError

class HFClientBackend(ChatBackend):
    def __init__(self, model: str, base_url: str = None, api_key: str = None):
        if base_url or api_key:
            self.client = InferenceClient(base_url=base_url, token=api_key)
            self.model = model
        else:
            self.client = InferenceClient(model)
            self.model = model

    def generate(self, messages, max_tokens, temperature, stream):
        if stream:
            for ev in self.client.chat_completion(
                messages, model=self.model, max_tokens=max_tokens, temperature=temperature, stream=True
            ):
                delta = ev.choices[0].delta.content or ""
                if delta:
                    yield delta
        else:
            out = self.client.chat_completion(
                messages, model=self.model, max_tokens=max_tokens, temperature=temperature
            )
            yield out.choices[0].message.content

class LocalTransformersBackend(ChatBackend):
    def __init__(self, model_name: str = "gpt2"):
        assert AutoModelForCausalLM is not None, "Install transformers to use local backend"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        if torch and torch.cuda.is_available():
            self.model.to("cuda")
        self.model.eval()

    def _format_prompt(self, messages):
        parts = []
        for m in messages:
            if m["role"] == "system":
                parts.append(f"[System]\n{m['content']}\n")
            elif m["role"] == "user":
                parts.append(f"[User]\n{m['content']}\n")
            else:
                parts.append(f"[Assistant]\n{m['content']}\n")
        parts.append("[Assistant]\n")
        return "\n".join(parts)

    def generate(self, messages, max_tokens, temperature, stream):
        prompt = self._format_prompt(messages)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        gen_cfg = dict(
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        if stream and TextIteratorStreamer is not None:
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            import threading
            def _gen():
                self.model.generate(**inputs, streamer=streamer, **gen_cfg)
            t = threading.Thread(target=_gen)
            t.start()
            for text in streamer:
                yield text
            t.join()
        else:
            output_ids = self.model.generate(**inputs, **gen_cfg)
            text = self.tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            yield text