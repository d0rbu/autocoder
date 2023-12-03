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
        max_tries: int = 2,
        process_response_fn: Callable[[Any], Any] | None = None,
        **kwargs,
    ) -> str:
        """
        Generate a completion for the given input.

        Args:
            model_input: The input to generate a completion for.
            max_tries: The maximum number of times to try generating text.
            process_response_fn: A function to process the response. Defaults to the class's `process_response` method.
            **kwargs: Keyword arguments to pass to the API.
        
        Returns:
            str: The generated text.
        """
        if process_response_fn is None:
            process_response_fn = self.process_response

        for _ in range(max_tries):
            try:
                generation: Any = self.generate(model_input, **kwargs)
                
                return process_response_fn(generation)
            except Exception as e:
                warn(f"Exception encountered while generating text: {e}")
        
        raise RuntimeError("Failed to generate text.")
    
    def process_response(self, response: Any) -> Any:
        """
        Process the response from the API.

        Args:
            response: The response from the API.
        
        Returns:
            Any: The processed response.
        """
        return response
    
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
