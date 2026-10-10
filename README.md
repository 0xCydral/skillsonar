# skillsonar

Find the right agent skill for a task by describing the task, not by remembering the skill's name.

[![tests](https://github.com/0xCydral/skillsonar/actions/workflows/test.yml/badge.svg)](https://github.com/0xCydral/skillsonar/actions/workflows/test.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## The problem

Claude Code, OpenCode, Codex and similar agents load skills: folders with a `SKILL.md` that says
what the skill does. After a few months you have dozens, spread over several directories, and the
one you need is the one whose name you forgot. `skillsonar` indexes every `SKILL.md` it can find
and ranks them against a sentence like "my pod keeps restarting".

## Install

```bash
pipx install git+https://github.com/0xCydral/skillsonar
skillsonar build
skillsonar search "my pod keeps restarting"
```

Python 3.10 or newer. The core has no dependencies. Embeddings and rerank are optional and need a
service you run yourself (see "How it works").

## Usage

`build` scans these folders when they exist: `~/.claude/skills`, `~/.agents/skills`,
`~/.config/opencode/skills`, and `./.claude/skills` and `./.opencode/skills` in the current
directory. Use `--path DIR` (repeatable) or `SKILLSONAR_PATHS` to index other folders instead.

The examples below run against the 21 small skills in `tests/fixtures/skills`.

```console
$ skillsonar build --path tests/fixtures/skills --embed
indexed 21 skills from 1 folder(s) -> .demo/index.json
embedded 21 skills with bge-m3 -> .demo/embeddings.json

$ skillsonar search "my pod keeps restarting"
1. kubernetes-pod-debugging  (score 4)
   Diagnose Kubernetes pods that crash, restart repeatedly or stay Pending. Covers kubectl describe, logs, events...
   tests/fixtures/skills/kubernetes-pod-debugging
```

Keyword search matches words. When the task and the skill describe the same problem in different
words, add the embedding index. Here the query says "container got killed"; the Kubernetes skill
says "OOMKilled" and "pods", so keyword search returns only a memory-profiling skill, and hybrid
search puts the Kubernetes skill second:

```console
$ skillsonar search "container got killed for using too much memory" --top 3
1. memory-leak-profiling  (score 3)
   Find memory leaks in long-running Node.js and Python services. Take heap snapshots, compare them over time and...
   tests/fixtures/skills/memory-leak-profiling

$ skillsonar search "container got killed for using too much memory" --hybrid --top 3
1. memory-leak-profiling  (score 0.03252)
   Find memory leaks in long-running Node.js and Python services. Take heap snapshots, compare them over time and...
   tests/fixtures/skills/memory-leak-profiling
2. kubernetes-pod-debugging  (score 0.01639)
   Diagnose Kubernetes pods that crash, restart repeatedly or stay Pending. Covers kubectl describe, logs, events...
   tests/fixtures/skills/kubernetes-pod-debugging
3. api-rate-limiting  (score 0.01587)
   Add rate limiting to an HTTP API with token bucket or sliding window counters, return 429 with Retry-After, an...
   tests/fixtures/skills/api-rate-limiting
```

Scores from different modes are not comparable, and the third hybrid result is noise. Read the
descriptions: the output is a shortlist.

`--json` prints one object per result, for scripts and agents. The `path` is absolute (shortened
here):

```console
$ skillsonar search "my pod keeps restarting" --json --top 1
[
  {
    "name": "kubernetes-pod-debugging",
    "score": 4.0,
    "source": "tests/fixtures/skills",
    "path": "/home/you/skills/kubernetes-pod-debugging",
    "desc": "Diagnose Kubernetes pods that crash, restart repeatedly or stay Pending. Covers kubectl describe, logs, events, OOMKilled and CrashLoopBackOff."
  }
]
```

```console
$ skillsonar stats
index: .demo/index.json
built: 2026-10-10T13:18:07-0500
skills: 21
  tests/fixtures/skills: 21
embeddings: bge-m3, 21 vectors
```

Without an index, commands stop with a message that names the fix:

```console
$ skillsonar search "anything" --index nope
skillsonar: no index at nope\index.json. Build one first: skillsonar build (add --path DIR to choose skill folders)
```

## How it works

```
SKILL.md folders --> build --> index.json        stemmed tokens of name, description, trigger text
                        |
                        +-- --embed --> embeddings.json   one vector per skill (Ollama, bge-m3)

query --> keyword score ---------+
                                 +--> reciprocal rank fusion --> top N --> optional chat-model rerank
query --> embedding similarity --+
```

- **Keyword index.** Each skill becomes the set of stemmed words in its name, description and
  `when_to_use` text (or the first lines of the body when there is none). A query scores one point
  per shared word, plus two when a word is in the skill's name. Frontmatter block scalars
  (`description: |` and `description: >`) are parsed.
- **Embeddings (optional).** `build --embed` sends each skill's name, description, headings and
  opening prose to an Ollama embeddings model. `--semantic` ranks by cosine similarity. `--hybrid`
  fuses the keyword and embedding rankings with reciprocal rank fusion (k = 60).
- **Rerank (optional).** `--rerank` sends the first-stage shortlist (150 skills by default, name and
  150 characters of description each) to a chat model in one call and keeps the order it returns.
  It only reorders what the first stage found, so pair it with `--hybrid` on large catalogs. Rerank
  is covered by unit tests with a stub; it has not been measured here.

## Configuration

| Setting | Applies to | Default |
|---|---|---|
| `--path DIR` (repeatable) | `build`: folders to index. Other commands: only return skills under DIR | the folders listed under Usage |
| `SKILLSONAR_PATHS` | `build`: folders to index, separated by `:` (`;` on Windows). Replaces the defaults, like `--path` | unset |
| `--index DIR` | all commands: directory holding `index.json` and `embeddings.json` | `%LOCALAPPDATA%\skillsonar` on Windows, `$XDG_CACHE_HOME/skillsonar` or `~/.cache/skillsonar` elsewhere |
| `--top N` | `search` | 5 |
| `--json` | `search` | off |
| `--semantic` / `--hybrid` | `search`: embedding-only or fused ranking (need `build --embed`) | keyword |
| `--rerank`, `--pool N` | `search`: rerank the first `N` candidates with a chat model | off, 150 |
| `--k N`, `--mode keyword\|semantic\|hybrid` | `eval` | 5, keyword |
| `OLLAMA_HOST` | embeddings server | `http://127.0.0.1:11434` |
| `SKILLSONAR_EMBED_MODEL` | embeddings model | `bge-m3` |
| `SKILLSONAR_RERANK_BASE_URL` | OpenAI-compatible endpoint, for example `https://api.openai.com/v1` | none, required for `--rerank` |
| `SKILLSONAR_RERANK_MODEL` | chat model name | none, required for `--rerank` |
| `SKILLSONAR_RERANK_API_KEY` | bearer token, optional for local servers | unset |

## Evaluation

`skillsonar eval` reads a JSONL file with one `{"query": "...", "expected": ["skill-name"]}` object
per line and prints recall@k: for each query, the share of its expected skills found in the top
k, averaged over queries. It exits with an error if an expected name is not in the index.

`evals/queries.jsonl` holds 28 queries written as symptoms ("my pod keeps restarting") against the 21
fixture skills in `tests/fixtures/skills`. Measured on 2026-10-10, k = 5:

| Mode | recall@5 | top-1 correct |
|---|---|---|
| keyword | 0.857 | 18 of 28 |
| semantic (bge-m3) | 0.964 | 25 of 28 |
| hybrid | 1.000 | 21 of 28 |

Reproduce:

```bash
skillsonar build --path tests/fixtures/skills --index .demo --embed
skillsonar eval evals/queries.jsonl --index .demo --mode hybrid
```

The catalog is 21 skills, the author wrote both the queries and the skills, and each query has one
expected skill. The table compares the three modes on the same data. It does not predict recall on
a catalog of hundreds of real skills with overlapping descriptions. The semantic and hybrid rows
used bge-m3 through the default `OLLAMA_HOST`. The embedding rows used bge-m3 served through the
default `OLLAMA_HOST`. Point `eval` at your own index and your own queries for a number that
applies to you.

## Formerly opencode-router

skillsonar was `opencode-router` up to version 0.3.3. Version 0.4.0 removes the agent routing, task
orchestration and project memory, because the routing step did not pick the right agent often enough
to justify itself (first choice correct on 19 of 30 test queries), and keeps the skill search.

## Development

```bash
git clone https://github.com/0xCydral/skillsonar
cd skillsonar
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
```

## License

MIT. See [LICENSE](LICENSE). Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
