import torch as th
from typing import Any
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
from .wrapper import ModelWrapper


class HuggingfaceWrapper(ModelWrapper):
    """
    Huggingface wrapper
    """

    DEFAULT_CONFIG = {
        "max_length": 4096,
    }

    def __init__(self, model: str, model_init_kwargs: dict[str, Any] | None = None, **default_generate_config: dict[str, Any]):
        super().__init__(**default_generate_config)
        model_init_kwargs = model_init_kwargs or {}

        self.model = AutoModelForCausalLM.from_pretrained(model, **model_init_kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained(model)

    def generate(
        self,
        model_input: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate text from the given input.
        """

        generate_config = self.default_generate_config.copy()
        generate_config.update(kwargs)

        model_input = self.tokenizer.apply_chat_template(model_input, return_tensors="pt").to(self.model.device)

        model_output = self.model.generate(model_input, **generate_config)
        
        new_tokens = model_output[:, model_input.shape[-1]:]

        model_output = self.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)

        return model_output[0]
