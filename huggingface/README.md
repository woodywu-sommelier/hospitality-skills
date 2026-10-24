# Hugging Face dataset

The example wine lists and the known-facts reference are mirrored to the Hugging Face dataset `woodywu-sommelier/hospitality-skills-examples`. Code stays on GitHub.

- `dataset-card.md` becomes the dataset's `README.md` (its card).
- `build_dataset.py` assembles the upload folder in `dist/hf-dataset/` from the files in this repository, so the dataset never drifts from the source.

Build, then upload with the Hugging Face CLI (requires `pip install huggingface_hub` and `huggingface-cli login` with a write token; the token is never stored in this repository):

```
python3 huggingface/build_dataset.py
huggingface-cli upload woodywu-sommelier/hospitality-skills-examples dist/hf-dataset . --repo-type dataset
```
