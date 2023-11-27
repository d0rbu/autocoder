from abc import ABC, abstractmethod
from typing import Any, Callable
from warnings import warn


class ModelWrapper(ABC):
    def __init__(self, **default_generate_config: dict[str, Any]) -> None:
        self.default_generate_config = self.DEFAULT_CONFIG.copy()
        if default_generate_config is not None:
            self.default_generate_config.update(default_generate_config)
    
    @property
    @abstractmethod
    def DEFAULT_CONFIG(self) -> dict[str, Any]:
        """
        The default configuration for the model.
        """
        return {}
    
    def __call__(
        self,
        model_input: Any,
        max_retries: int = 1,
        process_response_fn: Callable[[str], str] | None = None,
        **kwargs,
    ) -> str:
        """
        Generate a completion for the given input.

        Args:
            **kwargs: Keyword arguments to pass to the API.
        
        Returns:
            str: The generated text.
        """
        for _ in range(max_retries):
            try:
                generation: str = self.generate(model_input, **kwargs)
                if process_response_fn is None:
                    return generation
                
                return process_response_fn(generation)
            except Exception as e:
                warn(f"Exception encountered while generating text: {e}")
        
        raise RuntimeError("Failed to generate text.")
    
    @abstractmethod
    def generate(
        self,
        model_input: Any,
        **kwargs,
    ) -> Any:
        """
        Generate a completion for the given input.

        Args:
            model_input: The input to generate a completion for.
            **kwargs: Keyword arguments to pass to the API.
        
        Returns:
            Any: The generated output.
        """
