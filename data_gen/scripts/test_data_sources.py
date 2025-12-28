import os
from data_gen.types.diffusion_flux import FluxDiffusionSource
from data_gen.types.web_scraper import WikipediaImageScraper
from data_gen.types.huggingface_dataset import HuggingFaceDatasetSource

def test_diffusion_source(prompts, output_dir):
    try:
        print("Initializing Flux diffusion model...")
        diffusion = FluxDiffusionSource()
        
        os.makedirs(output_dir, exist_ok=True)

        for idx, prompt in enumerate(prompts, 1):
            print(f"[{idx}/{len(prompts)}] Generating image for: '{prompt}'")
            save_path = os.path.join(output_dir, f"diffusion_{idx}.png")

            result_path = diffusion.generate_content(prompt, save_path)
            print(f"Image saved to: {result_path}")

    except Exception as e:
        print(f"Error in diffusion source test: {str(e)}")
        import traceback
        traceback.print_exc()


def test_web_scraper_source(queries, output_dir):
    try:
        print("Initializing Wikipedia image scraper...")
        scraper = WikipediaImageScraper()

        os.makedirs(output_dir, exist_ok=True)

        for idx, query in enumerate(queries, 1):
            print(f"[{idx}/{len(queries)}] Scraping image for: '{query}'")
            save_path = os.path.join(output_dir, f"scraped_{query.lower()}.png")

            try:
                result_path = scraper.generate_content(query, save_path)
                print(f"Image saved to: {result_path}")
            except Exception as e:
                print(f"Failed to scrape '{query}': {str(e)}")
                continue

    except Exception as e:
        print(f"Error in web scraper test: {str(e)}")
        import traceback
        traceback.print_exc()


def test_huggingface_source(dataset_queries, output_dir):
    try:
        print("Initializing HuggingFace dataset source...")
        hf_source = HuggingFaceDatasetSource()

        os.makedirs(output_dir, exist_ok=True)

        for idx, query in enumerate(dataset_queries, 1):
            print(f"[{idx}/{len(dataset_queries)}] Downloading dataset: '{query}'")
            # Create filename from dataset query
            dataset_name = query.split(':')[0].replace('/', '_')
            save_path = os.path.join(output_dir, f"dataset_{dataset_name}.csv")

            try:
                result_path = hf_source.generate_content(query, save_path)
                print(f"Dataset saved to: {result_path}")
            except Exception as e:
                print(f"Failed to download '{query}': {str(e)}")
                continue

    except Exception as e:
        print(f"Error in HuggingFace source test: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    output_dir = "data_gen/playground/travel"

    # Test 1: Diffusion Source
    prompts = [
        "A beautiful beach resort with palm trees and turquoise water",
    ]
    test_diffusion_source(prompts, output_dir)

    # Test 2: Web Scraper Source
    queries = [
        "Paris",
    ]
    test_web_scraper_source(queries, output_dir)

    # Test 3: HuggingFace Dataset Source
    dataset_queries = [
        "imdb:train",
    ]
    test_huggingface_source(dataset_queries, output_dir)