from diffusers import FluxPipeline
import torch
from .source import DiffusionSource

class FluxDiffusionSource(DiffusionSource):
    """Flux diffusion model for generating images from text prompts."""

    def __init__(self):
        self.pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell",
            torch_dtype=torch.bfloat16
        )
        self.pipe = self.pipe.to("cuda")

    def generate_content(self, prompt: str, save_path: str) -> str:
        """
        Generate an image from a text prompt and save it.

        Args:
            prompt: Text description for image generation
            save_path: Path where the generated image will be saved

        Returns:
            Path to the saved image
        """
        image = self.pipe(
            prompt,
            guidance_scale=0.0,
            num_inference_steps=4,
            max_sequence_length=256,
            generator=torch.Generator("cuda").manual_seed(0)
        ).images[0]
        image.save(save_path)
        return save_path