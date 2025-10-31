## 🎯 Pin-It-Down — Simple Pinterest downloader

Lightweight CLI to fetch the best-quality image or video from a Pinterest pin (no login required). Clean, fast, and made for quick one-off saves.

✨ Highlights

- No account or login required
- Picks the best-quality asset it can find (images or videos)
- Batch input supported (paste multiple links)
- Minimal dependencies — pure Python

Quick start

1. Open a terminal in the project folder.
2. Run:

```bash
python3 main.py
```

Use the interactive menu to download a single link or paste multiple links for batch downloads.

Try it

- Paste a single pin URL like `https://www.pinterest.com/pin/<PIN_ID>/` and choose the download option.
- For batch mode, paste many links separated by newlines or commas.

Where files go

- Default folder: `downloads/` (created automatically)

Quick tips

- If a page doesn't contain a detectable asset the tool will report "No downloadable asset found." and skip it.
- The tool uses a heuristic to prefer original / large images and MP4 for videos.
- SSL verification may be disabled in this build for compatibility on some systems — only use on trusted networks.

License

MIT — see `LICENSE`.

Contributing

Small fixes or suggestions welcome. Open an issue or PR with a short description.

Have fun! 🚀
