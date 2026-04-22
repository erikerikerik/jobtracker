# JobTracker

A local job search management app with intelligent resume-based matching.

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Optional — pre-load your resume** (place a `.docx`, `.pdf`, or `.txt` in the data folder):
   ```bash
   mkdir -p data
   cp /path/to/your_resume.pdf data/resume.pdf
   ```
   Or upload directly via the UI after launch.

3. **Run:**
   ```bash
   python app.py
   ```

4. **Open in browser:** http://localhost:5001

---

## Features

### Job Management
- **Add jobs manually** — paste a URL to auto-fill title and description from any job posting
- **Import CSV** — bulk-import jobs from a CSV file
- **Status pipeline** — Interested → Applied → Interview → Offer / Rejected
- **Notes per job** — saved automatically on blur

### Board View
- Kanban-style view across all pipeline stages

### Intelligent Scoring
- Upload your resume (`.docx`, `.pdf`, or `.txt`) to enable content-based matching
- Scores based on keyword overlap between your resume and each job posting — works for any industry or role type
- Detects seniority alignment between your background and the job level
- Re-score all jobs any time you update your resume

### Sources
- **Greenhouse API** — add any company using Greenhouse (just use their company slug)
- **Lever API** — add any company using Lever
- **Ashby API** — add any company using Ashby
- **Direct scraper** — basic scrape of any career page URL
- Fetch one source at a time or batch-fetch all active sources
- Duplicate detection prevents re-importing jobs already in the database

### Adding New Job Sources
Many companies use Greenhouse, Lever, or Ashby for their job boards. To add one:
1. Go to **Sources → Add Source**
2. Select the ATS type (Greenhouse / Lever / Ashby)
3. Enter the company name and their ATS slug

To find a company's Greenhouse slug: try `https://boards-api.greenhouse.io/v1/boards/COMPANYNAME/jobs`

---

## Data
All data is stored in `data/jobs.db` (SQLite). Back it up anytime by copying that file.

## Keyboard Shortcuts
- `Escape` — close panels/modals
- `Cmd/Ctrl+K` — focus search
