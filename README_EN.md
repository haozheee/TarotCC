English | [中文](README.md)

# TarotCC — Tarot Readings in Claude Code

A Rider-Waite tarot reading system built for [Claude Code](https://claude.ai/claude-code). Just say "give me a reading" in conversation and Claude becomes your tarot reader — recommending spreads, drawing cards, displaying card images, and interpreting meanings, all without leaving your terminal.

![Three Card Spread Demo](assets/demo_three.png)

## Quick Start: Global `/tarot` Command

**Read tarot from any directory** — this is the recommended way to use TarotCC. Copy the slash command to your Claude Code global commands directory:

```bash
git clone https://github.com/haozheee/TarotCC.git
cd TarotCC
./install.sh
```

The install script automatically creates the conda environment, installs dependencies, and sets up the global `/tarot` command in `~/.claude/commands/` (paths are resolved automatically — no manual editing needed).

Once configured, launch Claude Code from **any directory** and type:

```
/tarot What does my career look like?
```

Claude will automatically enter the reading flow — recommend a spread, draw cards, show images, and interpret the results. Supports both Chinese and English — Claude switches language based on your input.

## How It Works

The core idea: **a custom slash command teaches Claude Code how to do tarot readings**.

The project includes a Python CLI tool (`tarot.py`) that handles card drawing and image rendering. The file `commands/tarot.md` defines the complete reading workflow — once installed as a global command, Claude reads these instructions when you type `/tarot`:

```
You: "/tarot I've been stressed about work, what does my career look like?"

Claude: Analyzes your question, recommends the Career spread
  ↓
You: Confirm the Career spread
  ↓
Claude: Runs tarot.py to draw cards, pops up card image window
  ↓
Claude: Interprets each card as a professional tarot reader
  ↓
You: Ask about a specific card, try a different question, or draw again
```

It's like chatting with a tarot reader — except this one lives in your terminal.

## Features

- **Global `/tarot` command** — read tarot from any project directory
- **Bilingual support** — Claude auto-detects your language; `--lang zh/en` controls CLI output
- **Full 78-card Rider-Waite deck** — 22 Major Arcana + 56 Minor Arcana with meanings
- **7 classic spreads** — Single, Yes/No, Three-Card, Celtic Cross, Horseshoe, Love, Career
- **Original Rider-Waite card images** — auto-downloaded and cached; reversed cards displayed upside down
- **Spread image rendering** — each spread laid out in its traditional pattern as a single PNG
- **Tkinter popup display** — card images pop up automatically, cross-platform

## Using Within the Project Directory

If you prefer not to set up the global command, you can use it directly from the project directory:

```bash
cd TarotCC
claude
```

The project's `CLAUDE.md` teaches Claude how to do readings automatically — just say "give me a tarot reading" without needing the `/tarot` command.

## CLI Usage

You can also skip Claude and use the CLI directly:

```bash
# Draw a single card
python tarot.py --lang en draw

# Three-card spread with a question
python tarot.py --lang en spread three -q "Where should I focus my energy?"

# Celtic Cross with image popup
python tarot.py --lang en spread cross -q "Deep analysis" -s

# List all spreads
python tarot.py spreads

# Look up a specific card
python tarot.py card "The Fool"
python tarot.py card "愚者"

# List all 78 cards
python tarot.py deck
```

**Options:**
- `--lang zh|en` — output language (default: Chinese)
- `-q` / `--question` — attach your question
- `-s` / `--show` — pop up tkinter window with card images

## Spreads

| Spread | Cards | Layout | Best For |
|--------|-------|--------|----------|
| `single` | 1 | Single card | Daily fortune, simple questions |
| `yesno` | 1 | Single card + tendency | Yes/no decisions |
| `three` | 3 | Past - Present - Future | Trends and development |
| `cross` | 10 | Celtic Cross + staff | Deep comprehensive analysis |
| `horseshoe` | 7 | U-shaped arc | General guidance |
| `love` | 6 | Heart-shaped symmetry | Love and relationships |
| `career` | 5 | Inverted pyramid | Career and professional growth |

## Project Structure

```
TarotCC/
├── CLAUDE.md          # Claude Code reading workflow instructions
├── install.sh         # One-step install script
├── tarot.py           # CLI tool (card drawing, image rendering, i18n)
├── commands/
│   └── tarot.md       # Global slash command template (paths resolved by install.sh)
├── data/
│   ├── cards.json     # 78 Rider-Waite tarot card data
│   └── img_cache/     # Card image cache (auto-downloaded)
├── assets/            # Demo images
└── README.md
```

## Technical Details

1. `tarot.py` loads full data for 78 cards from `data/cards.json`
2. Cards are drawn randomly, each with ~50% chance of being reversed
3. Pillow composites original Rider-Waite card images into spread layout PNGs
4. Card images are downloaded on first use and cached in `data/img_cache/`
5. The `--lang` flag controls CLI output and image rendering language (zh/en)
6. Claude Code reads the draw results and images, interpreting as a tarot reader

## Card Image Sources

Major Arcana images from [Wikimedia Commons](https://commons.wikimedia.org/) (public domain, 1909 first edition). Minor Arcana images from [tarot-json](https://github.com/metabismuth/tarot-json). All Rider-Waite tarot card images are in the public domain.

## License

MIT
