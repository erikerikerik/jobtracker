from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from job_agent.runner import JobRunResult, run_job_search


class JobAgentGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Job Agent")
        self.root.geometry("1180x760")
        self.root.minsize(980, 640)

        self.resume_var = tk.StringVar(value="data/resume.pdf")
        self.search_config_var = tk.StringVar(value="config/search.yaml")
        self.company_config_var = tk.StringVar(value="config/company_boards.yaml")
        self.limit_var = tk.StringVar(value="100")
        self.status_var = tk.StringVar(value="Choose a resume and run the search.")
        self.summary_var = tk.StringVar(value="No search has been run yet.")
        self.current_output_dir = Path("output")

        self.run_button: ttk.Button | None = None
        self.tree: ttk.Treeview | None = None
        self.details_text: ScrolledText | None = None
        self.log_text: ScrolledText | None = None

        self._results_by_row: dict[str, dict[str, str]] = {}
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._build_ui()
        self.root.after(150, self._poll_queue)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.root, padding=12)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        self._build_path_row(controls, 0, "Resume", self.resume_var, [("PDF", "*.pdf"), ("Word", "*.docx"), ("Text", "*.txt"), ("Markdown", "*.md"), ("All files", "*.*")])
        self._build_path_row(controls, 1, "Search Config", self.search_config_var, [("YAML", "*.yaml"), ("YML", "*.yml"), ("All files", "*.*")])
        self._build_path_row(controls, 2, "Company Config", self.company_config_var, [("YAML", "*.yaml"), ("YML", "*.yml"), ("All files", "*.*")])

        ttk.Label(controls, text="Limit").grid(row=3, column=0, sticky="w", pady=(10, 0))
        limit_entry = ttk.Entry(controls, textvariable=self.limit_var, width=12)
        limit_entry.grid(row=3, column=1, sticky="w", pady=(10, 0))

        button_row = ttk.Frame(controls)
        button_row.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self.run_button = ttk.Button(button_row, text="Run Search", command=self._run_search)
        self.run_button.pack(side="left")
        ttk.Button(button_row, text="Open Output Folder", command=self._open_output_folder).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Open Top Matches", command=lambda: self._open_report("top_matches.md")).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Open New Matches", command=lambda: self._open_report("new_matches.md")).pack(side="left", padx=(8, 0))

        ttk.Label(controls, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Label(controls, textvariable=self.summary_var).grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))

        body = ttk.Panedwindow(self.root, orient="vertical")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        top_panel = ttk.Frame(body, padding=(0, 8, 0, 0))
        top_panel.columnconfigure(0, weight=1)
        top_panel.rowconfigure(0, weight=1)
        body.add(top_panel, weight=4)

        columns = ("score", "new", "title", "company", "location", "source")
        self.tree = ttk.Treeview(top_panel, columns=columns, show="headings", selectmode="browse")
        headings = {
            "score": "Score",
            "new": "New",
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "source": "Source",
        }
        widths = {"score": 70, "new": 55, "title": 270, "company": 180, "location": 220, "source": 100}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], stretch=column in {"title", "location"})
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._open_selected_url)

        tree_scroll = ttk.Scrollbar(top_panel, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        bottom_panel = ttk.Panedwindow(body, orient="horizontal")
        body.add(bottom_panel, weight=2)

        details_frame = ttk.Labelframe(bottom_panel, text="Selection Details", padding=8)
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        self.details_text = ScrolledText(details_frame, wrap="word", height=12)
        self.details_text.grid(row=0, column=0, sticky="nsew")
        self.details_text.configure(state="disabled")
        bottom_panel.add(details_frame, weight=1)

        log_frame = ttk.Labelframe(bottom_panel, text="Run Log", padding=8)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = ScrolledText(log_frame, wrap="word", height=12)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.configure(state="disabled")
        bottom_panel.add(log_frame, weight=1)

    def _build_path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        filetypes: list[tuple[str, str]],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(0 if row == 0 else 10, 0))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=(0 if row == 0 else 10, 0), padx=(8, 8))
        ttk.Button(
            parent,
            text="Browse",
            command=lambda: self._choose_file(variable, filetypes),
        ).grid(row=row, column=2, sticky="e", pady=(0 if row == 0 else 10, 0))

    def _choose_file(self, variable: tk.StringVar, filetypes: list[tuple[str, str]]) -> None:
        chosen = filedialog.askopenfilename(filetypes=filetypes)
        if chosen:
            variable.set(chosen)

    def _run_search(self) -> None:
        resume_path = Path(self.resume_var.get().strip())
        search_config_path = Path(self.search_config_var.get().strip())
        company_config_path = Path(self.company_config_var.get().strip())

        if not resume_path.exists():
            messagebox.showerror("Missing Resume", f"Resume file not found:\n{resume_path}")
            return
        if not search_config_path.exists():
            messagebox.showerror("Missing Search Config", f"Search config not found:\n{search_config_path}")
            return
        if not company_config_path.exists():
            messagebox.showerror("Missing Company Config", f"Company config not found:\n{company_config_path}")
            return

        limit_text = self.limit_var.get().strip()
        limit: int | None = None
        if limit_text:
            try:
                limit = int(limit_text)
            except ValueError:
                messagebox.showerror("Invalid Limit", "Limit must be a whole number.")
                return

        self._set_running(True)
        self.status_var.set("Running search. This may take a little while if job feeds are slow.")
        self._append_log("Starting job search run...")

        thread = threading.Thread(
            target=self._run_search_worker,
            args=(resume_path, search_config_path, company_config_path, limit),
            daemon=True,
        )
        thread.start()

    def _run_search_worker(
        self,
        resume_path: Path,
        search_config_path: Path,
        company_config_path: Path,
        limit: int | None,
    ) -> None:
        try:
            result = run_job_search(
                resume_path=resume_path,
                search_config_path=search_config_path,
                company_config_path=company_config_path,
                limit=limit,
            )
            self._queue.put(("success", result))
        except Exception as exc:
            self._queue.put(("error", exc))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "success":
                    self._handle_success(payload)  # type: ignore[arg-type]
                else:
                    self._handle_error(payload)  # type: ignore[arg-type]
        except queue.Empty:
            pass
        finally:
            self.root.after(150, self._poll_queue)

    def _handle_success(self, result: JobRunResult) -> None:
        self._set_running(False)
        self.current_output_dir = result.app_config.runtime.output_dir
        new_count = len([job for job in result.ranked_jobs if job.is_new])
        self.status_var.set("Search complete.")
        self.summary_var.set(
            f"Processed {result.raw_job_count} raw jobs. Ranked {len(result.ranked_jobs)} matches. New this run: {new_count}."
        )
        self._append_log(f"Search complete. Raw jobs: {result.raw_job_count}. Ranked: {len(result.ranked_jobs)}. New: {new_count}.")
        if result.warnings:
            for warning in result.warnings:
                self._append_log(f"Warning: {warning}")
        self._populate_results(result)

    def _handle_error(self, exc: Exception) -> None:
        self._set_running(False)
        self.status_var.set("Search failed.")
        self._append_log(f"Search failed: {exc}")
        messagebox.showerror("Search Failed", str(exc))

    def _populate_results(self, result: JobRunResult) -> None:
        if self.tree is None:
            return
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        self._results_by_row.clear()

        for item in result.ranked_jobs:
            listing = item.listing
            row_id = self.tree.insert(
                "",
                "end",
                values=(
                    item.score,
                    "Yes" if item.is_new else "",
                    listing.title,
                    listing.company,
                    listing.location or "Unknown",
                    listing.source,
                ),
            )
            self._results_by_row[row_id] = {
                "title": listing.title,
                "company": listing.company,
                "location": listing.location or "Unknown",
                "source": listing.source,
                "score": str(item.score),
                "url": listing.url,
                "posted": listing.posted_at.date().isoformat() if listing.posted_at else "Unknown",
                "salary": listing.salary or "Unknown",
                "remote": "Yes" if listing.remote else "No",
                "reasons": "; ".join(item.reasons) if item.reasons else "General resume fit",
                "description": listing.description or "No description captured.",
            }

        if result.ranked_jobs:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self._show_details(first)
        else:
            self._set_details("No matching jobs were found for the current configuration.")

    def _on_select(self, _event: object) -> None:
        if self.tree is None:
            return
        selection = self.tree.selection()
        if selection:
            self._show_details(selection[0])

    def _show_details(self, row_id: str) -> None:
        item = self._results_by_row.get(row_id)
        if item is None:
            self._set_details("")
            return
        text = "\n".join(
            [
                f"Title: {item['title']}",
                f"Company: {item['company']}",
                f"Score: {item['score']}",
                f"Location: {item['location']}",
                f"Remote: {item['remote']}",
                f"Source: {item['source']}",
                f"Posted: {item['posted']}",
                f"Salary: {item['salary']}",
                f"URL: {item['url']}",
                "",
                f"Reasons: {item['reasons']}",
                "",
                item["description"],
            ]
        )
        self._set_details(text)

    def _set_details(self, text: str) -> None:
        if self.details_text is None:
            return
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", text)
        self.details_text.configure(state="disabled")

    def _append_log(self, line: str) -> None:
        if self.log_text is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{line}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _open_selected_url(self, _event: object | None = None) -> None:
        if self.tree is None:
            return
        selection = self.tree.selection()
        if not selection:
            return
        item = self._results_by_row.get(selection[0])
        if item and item["url"]:
            webbrowser.open(item["url"])

    def _open_output_folder(self) -> None:
        output_dir = self.current_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(output_dir)

    def _open_report(self, name: str) -> None:
        self._open_path(self.current_output_dir / name)

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showinfo("Not Found", f"Path does not exist yet:\n{path}")
            return
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            elif sys.platform.startswith("win"):
                subprocess.Popen(["cmd", "/c", "start", "", str(path)], shell=False)
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Open Failed", str(exc))

    def _set_running(self, is_running: bool) -> None:
        if self.run_button is not None:
            self.run_button.configure(state="disabled" if is_running else "normal")


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    JobAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
