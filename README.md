# Job Agent

A resume-aware job search bot that pulls listings from public job feeds and company ATS boards, scores them against your resume, and writes ranked reports each run.

Works for any field or role type — just configure `config/search.yaml` with your target titles and keywords.

## What It Does

- Parses your resume from `pdf`, `docx`, `txt`, or `md`
- Pulls jobs from:
  - `Remotive`
  - `Remote OK`
  - `Greenhouse` public boards
  - `Lever` public postings
  - `Ashby` public job boards
- Filters for fully remote jobs (and optionally a target city)
- Scores and ranks matches against your resume content and configured preferences
- Tracks which listings are new since the last run
- Writes reports to the `output/` folder:
  - `output/top_matches.md` — best matches, highest score first
  - `output/new_matches.md` — newly discovered listings since the previous run
  - `output/top_matches.csv` — spreadsheet-friendly export
  - `output/top_matches.json` — structured full results

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Place your resume in the `data/` folder:

```bash
mkdir -p data
cp /path/to/your_resume.pdf data/resume.pdf
```

Supported formats: `.pdf`, `.docx`, `.txt`, `.md`

## Configure

Edit `config/search.yaml` to set your target titles, boost keywords, industry preferences, and location settings. The file is fully commented — it should be self-explanatory.

Edit `config/company_boards.yaml` to add specific companies you want to monitor. The bot will pull all open roles from each company's ATS directly.

To find a company's ATS slug, visit their job board:
- Greenhouse: `boards.greenhouse.io/<slug>`
- Lever: `jobs.lever.co/<slug>`
- Ashby: `jobs.ashbyhq.com/<slug>`

## Run

```bash
job-agent --resume data/resume.pdf
```

With explicit config paths or a custom result limit:

```bash
job-agent \
  --resume data/resume.pdf \
  --search-config config/search.yaml \
  --company-config config/company_boards.yaml \
  --limit 100
```

## GUI

Launch the desktop interface:

```bash
job-agent-gui
```

The GUI lets you browse and sort ranked results in a table, view job details and match reasons, open listings directly in your browser, and access generated reports — no terminal required after setup.

## Outputs

| File | Description |
|------|-------------|
| `output/top_matches.md` | Best matches ranked by score |
| `output/new_matches.md` | Jobs new since last run |
| `output/top_matches.csv` | Full results as a spreadsheet |
| `output/top_matches.json` | Full results as JSON |
| `data/job_agent.sqlite3` | Seen-job state (used to detect new listings) |

## Notes

- The bot uses public ATS APIs — no browser automation, no scraping fragility.
- Adding companies to `config/company_boards.yaml` significantly improves coverage for your specific target employers.
- Run it on a schedule (e.g. daily cron) to get a fresh `new_matches.md` each morning.
- The `data/` folder is gitignored — your resume and job database stay local.
