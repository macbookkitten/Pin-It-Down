# Pin-It-Down – Pinterest Downloader

Download the best-quality image or video from Pinterest links. No login required. Supports single or multiple links with an interactive menu.

## Features

- Interactive CLI with clear prompts
- Single or multiple links (paste list)
- Picks the highest quality asset:
  - Videos: prefers MP4 and higher resolution URLs
  - Images: prefers `originals` or largest `<Wx>/` size; JPEG/PNG prioritized
- Predictable filenames based on the Pin ID; avoids overwrites
- No third-party dependencies (pure Python standard library)

## Requirements

# Pin-It-Down

Pin-It-Down is a lightweight command-line utility for downloading the highest-quality image or video from Pinterest pin pages. It requires no login and uses only the Python standard library.

## Highlights

- Interactive CLI for single or batch downloads
- Attempts to select the highest-quality asset available (prefers videos)
- Predictable filenames derived from the pin ID; files are auto-de-duplicated
- No external dependencies required for basic usage

## Requirements

- Python 3.8 or later
- Network access to fetch Pinterest pages and CDN-hosted assets

## Quickstart

1. Open a terminal in the repository root.
2. Run:

```bash
python3 main.py
```

3. Follow the interactive menu to download a single link, paste multiple links, or change the output directory.

By default, downloaded files are stored in a `downloads/` folder created inside the project root.

## Usage notes

- Batch input accepts links separated by newlines, commas, or spaces.
- If a page exposes both an image and a video, the tool will download the video.
- Filenames are constructed from the pin ID when possible, and existing filenames are not overwritten — a numeric suffix is added instead.

## Examples

Download a single pin (interactive):

```bash
python3 main.py

# In the menu select: 1
# Paste: https://www.pinterest.com/pin/123456789012345678/

# Example output lines (informational):
# - Fetching page: https://www.pinterest.com/pin/123456789012345678/
#   Found image: https://i.pinimg.com/originals/..../image.jpg
# Downloaded image -> downloads/pin-123456789012345678.jpg
```

Batch download (paste multiple links in option 2):

```text
# Paste a list of pin URLs (one per line or separated by commas)
# The tool will attempt each link and summarize results.
```

## Troubleshooting

- SSL / certificate errors: Some systems lack a local root CA bundle. This tool currently disables SSL verification to avoid failures on such systems. Disabling verification reduces security; run only on trusted networks.
- "No downloadable asset found": Ensure you provided a direct pin URL (for example `https://www.pinterest.com/pin/<PIN_ID>/`). Boards and profiles do not contain a single downloadable asset.
- Network/DNS failures: Verify your network and DNS configuration.

## Development

- This repository includes minimal dev tooling configuration (`pyproject.toml`, `.editorconfig`, `.vscode/tasks.json`) to help with formatting and linting.
- Recommended (optional): create and activate a virtual environment, then install dev tools:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

Run the VS Code tasks or call `black`/`ruff` directly to format and lint the codebase.

## Security & Legal

This project is provided for personal utilities and experimentation. Respect copyright and Pinterest's terms of service. Only download content you are authorized to save.

## Contributing

Bug reports and pull requests are welcome. Please include a short description of the issue and a minimal reproduction when relevant.

## License

This repository is provided "as-is". Add a LICENSE file to specify reuse terms.
