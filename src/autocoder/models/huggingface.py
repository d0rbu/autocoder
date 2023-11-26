from typing import Any
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
from .wrapper import ModelWrapper


class HuggingfaceWrapper(ModelWrapper):
    """
    Huggingface wrapper
    """

    DEFAULT_CONFIG = {
        "max_length": 4096,
        "temperature": 0.1,
        "top_p": 0.3,
    }

    def __init__(self, model: str, **default_generate_config: dict[str, Any]):
        super().__init__(default_generate_config)
        
        self.model = AutoModelForCausalLM.from_pretrained(model)
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
        generate_config = GenerationConfig(**generate_config)

        model_input = self.tokenizer(model_input, return_tensors="pt")

        model_output = self.model.generate(**model_input, generation_config=generate_config)
        model_output = self.tokenizer.batch_decode(model_output, skip_special_tokens=True)

        return model_output
