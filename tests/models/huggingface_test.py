import pytest
from autocoder.models.huggingface import HuggingfaceWrapper


@pytest.fixture()
def deepseek_7b_wrapper():
    return HuggingfaceWrapper(model="deepseek-ai/deepseek-coder-6.7b-instruct", model_init_kwargs={ "device_map": "auto", "offload_folder": "offload_tmp" })

def test_wrapper_generate(deepseek_7b_wrapper):
    expected_output = "Hello, world!\n"

    output = deepseek_7b_wrapper(model_input=[
        {
            "role": "user",
            "content": "Please reply with 'Hello, world!', nothing else."
        }
    ], do_sample=False)

    assert output == expected_output
