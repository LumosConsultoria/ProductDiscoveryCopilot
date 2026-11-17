import json
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from openai import OpenAI
from meeting import MeetingRecorder

from prompts import (
    DISCOVERY_SYSTEM_PROMPT,
    DISCOVERY_START_PROMPT,
    build_brief_prompt,
    build_prd_prompt,
    build_ost_prompt,
    MEETING_ANALYSIS_PROMPT,
    build_meeting_seed,
)
from storage import save_discovery, list_discoveries, load_discovery
from settings_store import get_api_key, set_api_key, load_settings, save_settings

APP_TITLE = "Product Discovery Copilot"

BG = "#F4F7FB"
PANEL = "#FFFFFF"
SIDEBAR = "#111827"
SIDEBAR_2 = "#1F2937"
TEXT = "#111827"
MUTED = "#667085"
BORDER = "#E5E7EB"
ACCENT = "#4F46E5"
ACCENT_LIGHT = "#EEF2FF"
SUCCESS = "#067647"
SUCCESS_BG = "#ECFDF3"
WARN = "#B54708"
WARN_BG = "#FFFAEB"
DANGER = "#B42318"
DANGER_BG = "#FEF3F2"
CYAN = "#0891B2"
CYAN_BG = "#ECFEFF"


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, first_run=False):
        super().__init__(parent)
        self.title("Configurações")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        settings = load_settings()

        frame = tk.Frame(self, bg=PANEL, padx=24, pady=22)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Configurações", font=("Segoe UI", 16, "bold"), bg=PANEL, fg=TEXT).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(frame, text="Sua chave fica protegida no Gerenciador de Credenciais do Windows.", font=("Segoe UI", 9), bg=PANEL, fg=MUTED).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 18))

        tk.Label(frame, text="Chave da API OpenAI", bg=PANEL, fg=TEXT, font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w")
        self.key_var = tk.StringVar(value=get_api_key())
        self.key_entry = ttk.Entry(frame, textvariable=self.key_var, width=56, show="•")
        self.key_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 8))

        self.show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Mostrar chave", variable=self.show_key, command=self.toggle_key).grid(row=4, column=0, sticky="w")

        tk.Label(frame, text="Modelo", bg=PANEL, fg=TEXT, font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=(18, 0))
        self.model_var = tk.StringVar(value=settings.get("model", "gpt-5.4"))
        ttk.Entry(frame, textvariable=self.model_var, width=35).grid(row=6, column=0, sticky="ew", pady=(5, 0), padx=(0, 8))

        tk.Label(frame, text="Profundidade", bg=PANEL, fg=TEXT, font=("Segoe UI", 9, "bold")).grid(row=5, column=1, sticky="w", pady=(18, 0))
        self.reasoning_var = tk.StringVar(value=settings.get("reasoning_effort", "low"))
        ttk.Combobox(frame, textvariable=self.reasoning_var, values=["none", "low", "medium", "high"], state="readonly", width=14).grid(row=6, column=1, sticky="ew", pady=(5, 0))

        buttons = tk.Frame(frame, bg=PANEL)
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(24, 0))
        if not first_run:
            ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Salvar", command=self.save).pack(side="left")

        frame.columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.on_close if first_run else self.destroy)
        self.key_entry.focus_set()
        self.wait_window(self)

    def toggle_key(self):
        self.key_entry.configure(show="" if self.show_key.get() else "•")

    def on_close(self):
        messagebox.showinfo("Configuração necessária", "Cadastre sua chave da API para usar o aplicativo.", parent=self)

    def save(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showerror("Chave necessária", "Informe sua chave da API OpenAI.", parent=self)
            return
        set_api_key(key)
        save_settings(self.model_var.get().strip() or "gpt-5.4", self.reasoning_var.get())
        self.destroy()


class MeetingReviewDialog(tk.Toplevel):
    def __init__(self, parent, analysis, transcript, on_use):
        super().__init__(parent)
        self.analysis = analysis
        self.transcript = transcript
        self.on_use = on_use
        self.title("Revisar reunião")
        self.geometry("1040x760")
        self.minsize(900, 650)
        self.configure(bg=BG)
        self.transient(parent)
        self.grab_set()

        header = tk.Frame(self, bg=PANEL, padx=24, pady=18, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")
        tk.Label(header, text="Revisar antes de usar no Discovery", font=("Segoe UI", 16, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(header, text="A IA organizou a conversa, mas você continua no controle do que vira contexto de produto.",
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self, bg=BG, padx=22, pady=18)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=16)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=16)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(left, text="Título sugerido", font=("Segoe UI", 9, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        self.title_var = tk.StringVar(value=analysis.get("title", ""))
        ttk.Entry(left, textvariable=self.title_var).pack(fill="x", pady=(5, 14))

        tk.Label(left, text="Problema / oportunidade", font=("Segoe UI", 9, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        self.problem_text = tk.Text(left, height=10, wrap="word", font=("Segoe UI", 9), relief="flat",
                                    highlightbackground=BORDER, highlightthickness=1, padx=9, pady=8)
        self.problem_text.insert("1.0", analysis.get("problem_opportunity", ""))
        self.problem_text.pack(fill="x", pady=(5, 14))

        tk.Label(left, text="Evidências", font=("Segoe UI", 9, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        self.evidence_text_review = tk.Text(left, height=13, wrap="word", font=("Segoe UI", 9), relief="flat",
                                            highlightbackground=BORDER, highlightthickness=1, padx=9, pady=8)
        ev_lines = []
        for item in analysis.get("evidence", []) or []:
            if isinstance(item, dict):
                ev_lines.append(f"• {item.get('text','')}  [confiança: {item.get('confidence','')}]")
            else:
                ev_lines.append(f"• {item}")
        self.evidence_text_review.insert("1.0", "\n".join(ev_lines))
        self.evidence_text_review.pack(fill="both", expand=True, pady=(5, 0))

        tk.Label(right, text="Outros sinais extraídos", font=("Segoe UI", 9, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        self.details_text = tk.Text(right, wrap="word", font=("Segoe UI", 9), relief="flat",
                                    highlightbackground=BORDER, highlightthickness=1, padx=10, pady=9)
        sections = [
            ("Usuários / segmentos", analysis.get("users_segments")),
            ("Hipóteses", analysis.get("hypotheses")),
            ("Soluções mencionadas", analysis.get("solutions_mentioned")),
            ("Métricas mencionadas", analysis.get("metrics_mentioned")),
            ("Decisões", analysis.get("decisions")),
            ("Questões em aberto", analysis.get("open_questions")),
        ]
        for name, values in sections:
            self.details_text.insert("end", name.upper() + "\n")
            for value in values or []:
                self.details_text.insert("end", f"• {value}\n")
            if not values:
                self.details_text.insert("end", "• Nenhum item identificado\n")
            self.details_text.insert("end", "\n")
        self.details_text.configure(state="disabled")
        self.details_text.pack(fill="both", expand=True, pady=(6, 0))

        footer = tk.Frame(self, bg=PANEL, padx=24, pady=14, highlightbackground=BORDER, highlightthickness=1)
        footer.pack(fill="x")
        tk.Button(footer, text="Cancelar", command=self.destroy, bg="#F9FAFB", fg=TEXT,
                  activebackground="#F3F4F6", relief="flat", bd=0, font=("Segoe UI", 9), padx=16, pady=9).pack(side="right")
        tk.Button(footer, text="Usar no Discovery →", command=self.use_in_discovery, bg=ACCENT, fg="white",
                  activebackground="#4338CA", activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 9, "bold"), padx=18, pady=9).pack(side="right", padx=(0, 8))

    def use_in_discovery(self):
        edited = dict(self.analysis)
        edited["title"] = self.title_var.get().strip()
        edited["problem_opportunity"] = self.problem_text.get("1.0", "end").strip()
        # Preserve edited evidence as review text, while keeping structured original too.
        edited["evidence_reviewed_text"] = self.evidence_text_review.get("1.0", "end").strip()
        self.on_use(edited, self.transcript)
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1380x860")
        self.minsize(1120, 700)
        self.configure(bg=BG)
        self.discovery_id = None
        self.messages = []
        self.history_items = []
        self.busy = False
        self.ost_data = None
        self.current_view = "home"
        self.recorder = MeetingRecorder()
        self.meeting_analysis = None
        self.meeting_transcript = ""
        self.meeting_seed = ""
        self._configure_styles()
        self._build_ui()
        self.after(150, self._first_run_check)

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except Exception:
            pass
        style.configure("TButton", font=("Segoe UI", 9), padding=(10, 6))
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 7))
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=(14, 7))

    def _first_run_check(self):
        if not get_api_key():
            SettingsDialog(self, first_run=True)
        self.refresh_history()
        self.update_dashboard()

    def _build_ui(self):
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=245)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=SIDEBAR, padx=18, pady=20)
        brand.pack(fill="x")
        tk.Label(brand, text="◆", font=("Segoe UI", 16, "bold"), bg=SIDEBAR, fg="#A5B4FC").pack(side="left")
        btxt = tk.Frame(brand, bg=SIDEBAR)
        btxt.pack(side="left", padx=(10, 0))
        tk.Label(btxt, text="Discovery Copilot", font=("Segoe UI", 12, "bold"), bg=SIDEBAR, fg="white").pack(anchor="w")
        tk.Label(btxt, text="Product Discovery Workspace", font=("Segoe UI", 8), bg=SIDEBAR, fg="#9CA3AF").pack(anchor="w")

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=16, pady=(0, 12))

        self.nav_buttons = {}
        for key, label in [
            ("home", "⌂  Início"),
            ("workspace", "▣  Discovery"),
            ("meeting", "●  Reunião"),
            ("tree", "⌘  Opportunity Tree"),
            ("docs", "▤  Documentação"),
        ]:
            btn = tk.Button(self.sidebar, text=label, anchor="w", relief="flat", bd=0,
                            bg=SIDEBAR, fg="#D1D5DB", activebackground=SIDEBAR_2,
                            activeforeground="white", font=("Segoe UI", 10, "bold"),
                            padx=18, pady=10, command=lambda k=key: self.switch_view(k))
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[key] = btn

        tk.Label(self.sidebar, text="DISCOVERIES", font=("Segoe UI", 8, "bold"), bg=SIDEBAR, fg="#6B7280").pack(anchor="w", padx=18, pady=(24, 6))
        self.history = tk.Listbox(self.sidebar, bg=SIDEBAR, fg="#D1D5DB", selectbackground=SIDEBAR_2,
                                  selectforeground="white", borderwidth=0, highlightthickness=0,
                                  font=("Segoe UI", 9), exportselection=False)
        self.history.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.history.bind("<<ListboxSelect>>", self.load_selected)

        side_bottom = tk.Frame(self.sidebar, bg=SIDEBAR, padx=12, pady=12)
        side_bottom.pack(fill="x", side="bottom")
        tk.Button(side_bottom, text="＋ Novo discovery", command=self.start_manual_discovery, bg=ACCENT, fg="white",
                  activebackground="#4338CA", activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 9, "bold"), padx=10, pady=9).pack(fill="x")
        tk.Button(side_bottom, text="⚙  Configurações", command=lambda: SettingsDialog(self), bg=SIDEBAR,
                  fg="#D1D5DB", activebackground=SIDEBAR_2, activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 9), padx=10, pady=8).pack(fill="x", pady=(6, 0))

        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)

        self.header = tk.Frame(self.main, bg=PANEL, padx=24, pady=14, highlightbackground=BORDER, highlightthickness=1)
        self.header.pack(fill="x")
        hleft = tk.Frame(self.header, bg=PANEL)
        hleft.pack(side="left")
        self.header_title = tk.Label(hleft, text="Workspace", font=("Segoe UI", 16, "bold"), bg=PANEL, fg=TEXT)
        self.header_title.pack(anchor="w")
        self.header_subtitle = tk.Label(hleft, text="Transforme incerteza em aprendizado e decisões melhores.", font=("Segoe UI", 9), bg=PANEL, fg=MUTED)
        self.header_subtitle.pack(anchor="w", pady=(2, 0))
        self.status_chip = tk.Label(self.header, text="● Pronto", font=("Segoe UI", 9, "bold"), bg=SUCCESS_BG, fg=SUCCESS, padx=10, pady=5)
        self.status_chip.pack(side="right")

        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=22, pady=18)

        self.home_view = tk.Frame(self.content, bg=BG)
        self.meeting_view = tk.Frame(self.content, bg=BG)
        self.workspace_view = tk.Frame(self.content, bg=BG)
        self.tree_view = tk.Frame(self.content, bg=BG)
        self.docs_view = tk.Frame(self.content, bg=BG)

        self._build_home_view()
        self._build_meeting_view()
        self._build_workspace_view()
        self._build_tree_view()
        self._build_docs_view()
        self.switch_view("home")

    def switch_view(self, key):
        self.current_view = key
        for frame in (self.home_view, self.meeting_view, self.workspace_view, self.tree_view, self.docs_view):
            frame.pack_forget()
        mapping = {
            "home": (self.home_view, "Product Discovery Copilot", "Escolha como quer começar: discovery manual ou reunião."),
            "workspace": (self.workspace_view, "Discovery Workspace", "Conduza o discovery e acompanhe a maturidade das evidências."),
            "meeting": (self.meeting_view, "Reunião", "Capture uma conversa e transforme-a em contexto revisável para discovery."),
            "tree": (self.tree_view, "Opportunity Solution Tree", "Visualize problema, oportunidades, soluções e experimentos."),
            "docs": (self.docs_view, "Documentação", "Consolide o aprendizado em artefatos reutilizáveis."),
        }
        frame, title, subtitle = mapping[key]
        frame.pack(fill="both", expand=True)
        self.header_title.config(text=title)
        self.header_subtitle.config(text=subtitle)
        for k, btn in self.nav_buttons.items():
            btn.config(bg=SIDEBAR_2 if k == key else SIDEBAR, fg="white" if k == key else "#D1D5DB")


    def _build_home_view(self):
        hero = tk.Frame(self.home_view, bg="#EEF2FF", highlightbackground="#C7D2FE", highlightthickness=1, padx=28, pady=24)
        hero.pack(fill="x", pady=(0, 16))
        tk.Label(hero, text="Comece do jeito que fizer sentido hoje", font=("Segoe UI", 18, "bold"),
                 bg="#EEF2FF", fg=TEXT).pack(anchor="w")
        tk.Label(hero, text="A reunião é opcional. Você pode iniciar um discovery manualmente a qualquer momento.",
                 font=("Segoe UI", 10), bg="#EEF2FF", fg=MUTED).pack(anchor="w", pady=(5, 0))

        actions = tk.Frame(self.home_view, bg=BG)
        actions.pack(fill="x")

        manual = tk.Frame(actions, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=22, pady=20)
        manual.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(manual, text="01", font=("Segoe UI", 9, "bold"), bg=ACCENT_LIGHT, fg=ACCENT, padx=8, pady=3).pack(anchor="w")
        tk.Label(manual, text="Novo Discovery", font=("Segoe UI", 15, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w", pady=(14, 4))
        tk.Label(manual, text="Comece com o problema, contexto e evidências que você já possui. Nenhuma reunião é necessária.",
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED, wraplength=430, justify="left").pack(anchor="w")
        tk.Button(manual, text="Começar manualmente →", command=self.start_manual_discovery, bg=ACCENT, fg="white",
                  activebackground="#4338CA", activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 9, "bold"), padx=14, pady=9).pack(anchor="w", pady=(18, 0))

        meeting = tk.Frame(actions, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=22, pady=20)
        meeting.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(meeting, text="02", font=("Segoe UI", 9, "bold"), bg=CYAN_BG, fg=CYAN, padx=8, pady=3).pack(anchor="w")
        tk.Label(meeting, text="Discovery a partir de reunião", font=("Segoe UI", 15, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w", pady=(14, 4))
        tk.Label(meeting, text="Grave uma conversa, revise a análise e use os achados para pré-preencher o mesmo Workspace.",
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED, wraplength=430, justify="left").pack(anchor="w")
        tk.Button(meeting, text="Abrir modo reunião →", command=lambda: self.switch_view("meeting"), bg="#0E7490", fg="white",
                  activebackground="#155E75", activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 9, "bold"), padx=14, pady=9).pack(anchor="w", pady=(18, 0))

        flow = tk.Frame(self.home_view, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=22, pady=18)
        flow.pack(fill="both", expand=True, pady=(16, 0))
        tk.Label(flow, text="Fluxo do produto", font=("Segoe UI", 11, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(flow, text="Discovery  →  Evidências  →  Hipóteses  →  Experimentos  →  Opportunity Tree  →  Brief / PRD",
                 font=("Segoe UI", 10, "bold"), bg=PANEL, fg=ACCENT).pack(anchor="w", pady=(10, 5))
        tk.Label(flow, text="A reunião é apenas uma porta de entrada adicional para esse mesmo fluxo.",
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED).pack(anchor="w")

    def _build_meeting_view(self):
        warning = tk.Frame(self.meeting_view, bg=WARN_BG, highlightbackground="#FEDF89", highlightthickness=1, padx=16, pady=12)
        warning.pack(fill="x", pady=(0, 14))
        tk.Label(warning, text="Privacidade e LGPD", font=("Segoe UI", 9, "bold"), bg=WARN_BG, fg=WARN).pack(anchor="w")
        tk.Label(
            warning,
            text=("Confirme que a gravação é permitida pela organização e pelos participantes. "
                  "Evite dados identificáveis de pacientes quando não forem necessários."),
            font=("Segoe UI", 8), bg=WARN_BG, fg=TEXT, wraplength=920, justify="left"
        ).pack(anchor="w", pady=(3, 0))

        panel = tk.Frame(self.meeting_view, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=24, pady=22)
        panel.pack(fill="x")
        top = tk.Frame(panel, bg=PANEL)
        top.pack(fill="x")
        tk.Label(top, text="Captura de reunião", font=("Segoe UI", 15, "bold"), bg=PANEL, fg=TEXT).pack(side="left")
        self.meeting_status = tk.StringVar(value="Pronto para iniciar")
        tk.Label(top, textvariable=self.meeting_status, font=("Segoe UI", 8, "bold"),
                 bg=SUCCESS_BG, fg=SUCCESS, padx=9, pady=4).pack(side="right")

        tk.Label(panel, text="Ao encerrar, o Copilot transcreve, organiza os sinais e abre uma revisão antes de preencher o Discovery.",
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED).pack(anchor="w", pady=(5, 18))

        controls = tk.Frame(panel, bg=PANEL)
        controls.pack(fill="x")
        self.meeting_start_btn = tk.Button(
            controls, text="▶  Iniciar reunião", command=self.start_meeting_recording,
            bg="#0E7490", fg="white", activebackground="#155E75", activeforeground="white",
            relief="flat", bd=0, font=("Segoe UI", 10, "bold"), padx=18, pady=11
        )
        self.meeting_start_btn.pack(side="left")
        self.meeting_pause_btn = tk.Button(
            controls, text="⏸  Pausar", command=self.pause_meeting_recording, state="disabled",
            bg="#F9FAFB", fg=TEXT, activebackground="#F3F4F6", relief="flat", bd=0,
            font=("Segoe UI", 9), padx=14, pady=11
        )
        self.meeting_pause_btn.pack(side="left", padx=8)
        self.meeting_stop_btn = tk.Button(
            controls, text="■  Encerrar e analisar", command=self.stop_and_analyze_meeting, state="disabled",
            bg="#F9FAFB", fg=TEXT, activebackground="#F3F4F6", relief="flat", bd=0,
            font=("Segoe UI", 9), padx=14, pady=11
        )
        self.meeting_stop_btn.pack(side="left")

        info = tk.Frame(self.meeting_view, bg=BG)
        info.pack(fill="both", expand=True, pady=(14, 0))

        left = tk.Frame(info, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=20, pady=18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 7))
        right = tk.Frame(info, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=20, pady=18)
        right.pack(side="left", fill="both", expand=True, padx=(7, 0))

        tk.Label(left, text="O que o Copilot procura", font=("Segoe UI", 11, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(left, text=("• problema / oportunidade\n• evidências e relatos\n• usuários / segmentos\n• hipóteses\n"
                             "• soluções sugeridas\n• métricas e decisões\n• questões em aberto"),
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", pady=(10, 0))

        tk.Label(right, text="Depois da reunião", font=("Segoe UI", 11, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(right, text=("1. Revise a interpretação\n2. Edite título, problema e evidências\n"
                              "3. Clique em “Usar no Discovery”\n4. Continue normalmente no Workspace"),
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", pady=(10, 0))

    def start_manual_discovery(self):
        self.new_discovery()
        self.switch_view("workspace")
        try:
            self.context_text.focus_set()
        except Exception:
            pass

    def start_meeting_recording(self):
        if self.busy:
            return
        try:
            self.recorder.start()
            self.meeting_status.set("● Gravando")
            self.meeting_start_btn.config(state="disabled")
            self.meeting_pause_btn.config(state="normal", text="⏸  Pausar")
            self.meeting_stop_btn.config(state="normal")
        except Exception as exc:
            messagebox.showerror("Microfone", f"Não foi possível iniciar a gravação:\n{exc}")

    def pause_meeting_recording(self):
        if not self.recorder.paused:
            self.recorder.pause()
            self.meeting_status.set("Ⅱ Pausada")
            self.meeting_pause_btn.config(text="▶  Retomar")
        else:
            self.recorder.resume()
            self.meeting_status.set("● Gravando")
            self.meeting_pause_btn.config(text="⏸  Pausar")

    def stop_and_analyze_meeting(self):
        self.recorder.stop()
        self.meeting_start_btn.config(state="normal")
        self.meeting_pause_btn.config(state="disabled", text="⏸  Pausar")
        self.meeting_stop_btn.config(state="disabled")
        if not self.recorder.has_audio():
            self.meeting_status.set("Sem áudio")
            messagebox.showwarning("Reunião", "Nenhum áudio foi capturado.")
            return
        self.meeting_status.set("Analisando…")
        self._set_busy(True, "Transcrevendo reunião…")

        def worker():
            try:
                wav_bytes = self.recorder.to_wav_bytes()
                transcript = self._transcribe_audio(wav_bytes)
                analysis = self._analyze_meeting(transcript)
                self.after(0, lambda: self._meeting_ready(analysis, transcript))
            except Exception as exc:
                self.after(0, lambda: self._meeting_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _transcribe_audio(self, wav_bytes):
        import io
        client = OpenAI(api_key=get_api_key())
        file_obj = io.BytesIO(wav_bytes)
        file_obj.name = "meeting.wav"
        result = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=file_obj,
            response_format="text",
        )
        return result if isinstance(result, str) else getattr(result, "text", str(result))

    def _analyze_meeting(self, transcript):
        settings = load_settings()
        client = OpenAI(api_key=get_api_key())
        response = client.responses.create(
            model=settings.get("model", "gpt-5.4"),
            reasoning={"effort": settings.get("reasoning_effort", "low")},
            store=False,
            input=[
                {"role": "system", "content": MEETING_ANALYSIS_PROMPT},
                {"role": "user", "content": transcript},
            ],
        )
        cleaned = response.output_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].lstrip()
        return json.loads(cleaned)

    def _meeting_ready(self, analysis, transcript):
        self._set_busy(False)
        self.meeting_status.set("✓ Análise concluída")
        self.meeting_analysis = analysis
        self.meeting_transcript = transcript
        MeetingReviewDialog(self, analysis, transcript, self.use_meeting_in_discovery)

    def _meeting_error(self, error):
        self._set_busy(False)
        self.meeting_status.set("Falha na análise")
        messagebox.showerror("Reunião", f"Não foi possível processar a reunião:\n{error}")

    def use_meeting_in_discovery(self, analysis, transcript):
        # Meeting is optional: when chosen, it creates a fresh discovery draft.
        self.discovery_id = None
        self.messages = []
        self.ost_data = None
        self.meeting_seed = ""
        self.meeting_seed = build_meeting_seed(analysis)

        self.title_var.set(analysis.get("title", ""))
        self.context_text.delete("1.0", "end")
        self.context_text.insert("1.0", analysis.get("problem_opportunity", ""))

        reviewed = analysis.get("evidence_reviewed_text", "").strip()
        if not reviewed:
            lines = []
            for item in analysis.get("evidence", []) or []:
                if isinstance(item, dict):
                    lines.append(f"• {item.get('text','')} [confiança: {item.get('confidence','')}]")
                else:
                    lines.append(f"• {item}")
            reviewed = "\n".join(lines)

        self.evidence_text.delete("1.0", "end")
        self.evidence_text.insert("1.0", reviewed)

        # Seed context is kept for the AI once the user clicks Iniciar discovery.
        self.render_chat()
        self.update_dashboard()
        self.switch_view("workspace")
        self.status_chip.config(text="● Reunião aplicada", bg=CYAN_BG, fg=CYAN)
        self.after(2200, lambda: self.status_chip.config(text="● Pronto", bg=SUCCESS_BG, fg=SUCCESS))

    def _card(self, parent, title, value, foot, fg=TEXT, bg=PANEL):
        card = tk.Frame(parent, bg=bg, highlightbackground=BORDER, highlightthickness=1, padx=15, pady=12)
        tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), bg=bg, fg=MUTED).pack(anchor="w")
        val = tk.Label(card, text=value, font=("Segoe UI", 18, "bold"), bg=bg, fg=fg)
        val.pack(anchor="w", pady=(4, 1))
        tk.Label(card, text=foot, font=("Segoe UI", 8), bg=bg, fg=MUTED, wraplength=230, justify="left").pack(anchor="w")
        return card, val

    def _build_workspace_view(self):
        cards = tk.Frame(self.workspace_view, bg=BG)
        cards.pack(fill="x", pady=(0, 12))
        for i in range(4): cards.columnconfigure(i, weight=1)
        c1, self.problem_card = self._card(cards, "PROBLEMA", "0%", "Comece descrevendo o problema, não a solução.", ACCENT)
        c2, self.evidence_card = self._card(cards, "EVIDÊNCIAS", "0", "Quantidade aproximada de sinais informados.", CYAN)
        c3, self.learning_card = self._card(cards, "APRENDIZADO", "0", "Rodadas de conversa realizadas no discovery.", SUCCESS)
        c4, self.stage_card = self._card(cards, "MATURIDADE", "Inicial", "Progresso heurístico do discovery.", WARN)
        for idx, card in enumerate((c1, c2, c3, c4)):
            card.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 6, 0 if idx == 3 else 6))

        body = tk.PanedWindow(self.workspace_view, orient="horizontal", bg=BG, bd=0, sashwidth=6, sashrelief="flat")
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=14)
        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=14)
        body.add(left, minsize=380, width=470)
        body.add(right, minsize=500)

        tk.Label(left, text="Definição do discovery", font=("Segoe UI", 11, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(left, text="Contexto inicial e evidências conhecidas.", font=("Segoe UI", 8), bg=PANEL, fg=MUTED).pack(anchor="w", pady=(2, 12))

        tk.Label(left, text="Título", font=("Segoe UI", 8, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        self.title_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.title_var).pack(fill="x", pady=(4, 10))

        tk.Label(left, text="Problema / oportunidade", font=("Segoe UI", 8, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        self.context_text = tk.Text(left, height=8, wrap="word", font=("Segoe UI", 9), relief="solid", bd=1, padx=8, pady=8)
        self.context_text.pack(fill="x", pady=(4, 10))
        self.context_text.bind("<KeyRelease>", lambda e: self.update_dashboard())

        tk.Label(left, text="Evidências existentes", font=("Segoe UI", 8, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        self.evidence_text = tk.Text(left, height=8, wrap="word", font=("Segoe UI", 9), relief="solid", bd=1, padx=8, pady=8)
        self.evidence_text.pack(fill="x", pady=(4, 10))
        self.evidence_text.bind("<KeyRelease>", lambda e: self.update_dashboard())

        actions = tk.Frame(left, bg=PANEL)
        actions.pack(fill="x", pady=(2, 0))
        self.start_btn = tk.Button(actions, text="Iniciar discovery", command=self.start_discovery,
                                   bg=ACCENT, fg="white", activebackground="#4338CA", activeforeground="white",
                                   relief="flat", bd=0, font=("Segoe UI", 9, "bold"), padx=12, pady=8)
        self.start_btn.pack(side="left")
        tk.Button(actions, text="Salvar", command=self.save_current, bg="#F9FAFB", fg=TEXT,
                  relief="flat", bd=1, font=("Segoe UI", 9), padx=12, pady=8).pack(side="left", padx=(8, 0))

        top = tk.Frame(right, bg=PANEL)
        top.pack(fill="x")
        tk.Label(top, text="Discovery coach", font=("Segoe UI", 11, "bold"), bg=PANEL, fg=TEXT).pack(side="left")
        self.round_label = tk.Label(top, text="0 rodadas", font=("Segoe UI", 8, "bold"), bg=ACCENT_LIGHT, fg=ACCENT, padx=8, pady=4)
        self.round_label.pack(side="right")
        tk.Label(right, text="O copilot questiona premissas e prioriza as incertezas mais importantes.", font=("Segoe UI", 8), bg=PANEL, fg=MUTED).pack(anchor="w", pady=(2, 10))

        self.chat = tk.Text(right, wrap="word", state="disabled", font=("Segoe UI", 9), padx=10, pady=10,
                            relief="solid", bd=1, bg="#FBFCFE")
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_configure("user_head", font=("Segoe UI", 9, "bold"), foreground=ACCENT)
        self.chat.tag_configure("assistant_head", font=("Segoe UI", 9, "bold"), foreground=SUCCESS)
        self.chat.tag_configure("body", spacing3=8)

        send = tk.Frame(right, bg=PANEL)
        send.pack(fill="x", pady=(10, 0))
        self.message_var = tk.StringVar()
        entry = ttk.Entry(send, textvariable=self.message_var)
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        entry.bind("<Return>", lambda e: self.send_message())
        self.send_btn = tk.Button(send, text="Enviar", command=self.send_message, bg=ACCENT, fg="white",
                                  activebackground="#4338CA", activeforeground="white", relief="flat", bd=0,
                                  font=("Segoe UI", 9, "bold"), padx=14, pady=7)
        self.send_btn.pack(side="left", padx=(8, 0))

    def _build_tree_view(self):
        toolbar = tk.Frame(self.tree_view, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))
        self.tree_hint = tk.Label(toolbar, text="O mapa usa apenas o conteúdo do discovery atual.", font=("Segoe UI", 9), bg=BG, fg=MUTED)
        self.tree_hint.pack(side="left")
        self.tree_btn = tk.Button(toolbar, text="Atualizar mapa", command=self.generate_ost, bg=ACCENT, fg="white",
                                  activebackground="#4338CA", activeforeground="white", relief="flat", bd=0,
                                  font=("Segoe UI", 9, "bold"), padx=12, pady=8)
        self.tree_btn.pack(side="right")

        risks = tk.Frame(self.tree_view, bg=BG)
        risks.pack(fill="x", pady=(0, 10))
        self.risk_labels = {}
        for i, (key, label) in enumerate([("value", "Valor"), ("usability", "Usabilidade"), ("feasibility", "Viabilidade técnica"), ("business", "Negócio")]):
            risks.columnconfigure(i, weight=1)
            box = tk.Frame(risks, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=9)
            box.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            tk.Label(box, text=label, font=("Segoe UI", 8, "bold"), bg=PANEL, fg=MUTED).pack(anchor="w")
            value = tk.Label(box, text="Incerto", font=("Segoe UI", 11, "bold"), bg=PANEL, fg=WARN)
            value.pack(anchor="w", pady=(3, 0))
            self.risk_labels[key] = value

        tree_panel = tk.Frame(self.tree_view, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tree_panel.pack(fill="both", expand=True)
        self.tree_canvas = tk.Canvas(tree_panel, bg=PANEL, highlightthickness=0)
        xbar = ttk.Scrollbar(tree_panel, orient="horizontal", command=self.tree_canvas.xview)
        ybar = ttk.Scrollbar(tree_panel, orient="vertical", command=self.tree_canvas.yview)
        self.tree_canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.tree_canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        tree_panel.rowconfigure(0, weight=1)
        tree_panel.columnconfigure(0, weight=1)
        self._draw_empty_tree()

        self.next_step_var = tk.StringVar(value="Próximo passo aparecerá aqui após atualizar o mapa.")
        next_box = tk.Frame(self.tree_view, bg=ACCENT_LIGHT, padx=13, pady=10)
        next_box.pack(fill="x", pady=(10, 0))
        tk.Label(next_box, text="PRÓXIMO PASSO", font=("Segoe UI", 8, "bold"), bg=ACCENT_LIGHT, fg=ACCENT).pack(anchor="w")
        tk.Label(next_box, textvariable=self.next_step_var, font=("Segoe UI", 9), bg=ACCENT_LIGHT, fg=TEXT, wraplength=1000, justify="left").pack(anchor="w", pady=(2, 0))

    def _build_docs_view(self):
        toolbar = tk.Frame(self.docs_view, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))
        tk.Button(toolbar, text="Gerar Discovery Brief", command=lambda: self.generate_document("brief"),
                  bg=ACCENT, fg="white", activebackground="#4338CA", activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 9, "bold"), padx=12, pady=8).pack(side="left")
        tk.Button(toolbar, text="Gerar PRD", command=lambda: self.generate_document("prd"),
                  bg="#F9FAFB", fg=TEXT, relief="flat", bd=1, font=("Segoe UI", 9), padx=12, pady=8).pack(side="left", padx=(8, 0))
        tk.Button(toolbar, text="Exportar .md", command=self.export_document,
                  bg="#F9FAFB", fg=TEXT, relief="flat", bd=1, font=("Segoe UI", 9), padx=12, pady=8).pack(side="right")

        self.doc_text = tk.Text(self.docs_view, wrap="word", font=("Consolas", 10), padx=14, pady=14,
                                relief="solid", bd=1, bg=PANEL)
        self.doc_text.pack(fill="both", expand=True)

    def _set_busy(self, value, text=""):
        self.busy = value
        state = "disabled" if value else "normal"
        for widget in (self.start_btn, self.send_btn, self.tree_btn):
            widget.configure(state=state)
        if value:
            self.status_chip.config(text=f"● {text or 'Processando'}", bg=WARN_BG, fg=WARN)
        else:
            self.status_chip.config(text="● Pronto", bg=SUCCESS_BG, fg=SUCCESS)
        self.update_idletasks()

    def _api_call(self, user_content, callback, system_prompt=DISCOVERY_SYSTEM_PROMPT):
        key = get_api_key()
        if not key:
            SettingsDialog(self, first_run=True)
            key = get_api_key()
            if not key:
                return
        settings = load_settings()
        model = settings.get("model", "gpt-5.4")
        effort = settings.get("reasoning_effort", "low")
        self._set_busy(True, f"Consultando {model}...")

        def worker():
            try:
                client = OpenAI(api_key=key)
                kwargs = {"model": model, "instructions": system_prompt, "input": user_content, "store": False}
                if effort != "none":
                    kwargs["reasoning"] = {"effort": effort}
                response = client.responses.create(**kwargs)
                self.after(0, lambda: self._api_success(response.output_text, callback))
            except Exception as exc:
                self.after(0, lambda: self._api_error(str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _api_success(self, result, callback):
        self._set_busy(False)
        callback(result)

    def _api_error(self, error):
        self._set_busy(False)
        self.status_chip.config(text="● Erro", bg=DANGER_BG, fg=DANGER)
        messagebox.showerror("Erro ao consultar a OpenAI", error)

    def _conversation_text(self):
        return "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in self.messages)

    def start_discovery(self):
        if self.busy: return
        context = self.context_text.get("1.0", "end").strip()
        evidence = self.evidence_text.get("1.0", "end").strip()
        title = self.title_var.get().strip() or "Discovery sem título"
        if not context:
            messagebox.showwarning("Problema necessário", "Descreva o problema ou oportunidade.")
            return
        prompt = DISCOVERY_START_PROMPT.format(title=title, context=context, evidence=evidence or "Nenhuma evidência fornecida.")
        if self.meeting_seed:
            prompt += "\n\n" + self.meeting_seed
        self.messages = [{"role": "user", "content": prompt}]
        self.render_chat()
        self.update_dashboard()
        self._api_call(self._conversation_text(), self._after_discovery_answer)

    def send_message(self):
        if self.busy: return
        text = self.message_var.get().strip()
        if not text: return
        if not self.messages:
            messagebox.showinfo("Inicie o discovery", "Clique em 'Iniciar discovery' primeiro.")
            return
        self.message_var.set("")
        self.messages.append({"role": "user", "content": text})
        self.render_chat()
        self.update_dashboard()
        self._api_call(self._conversation_text(), self._after_discovery_answer)

    def _after_discovery_answer(self, result):
        self.messages.append({"role": "assistant", "content": result})
        self.render_chat()
        self.update_dashboard()
        self.save_current(silent=True)

    def render_chat(self):
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        for m in self.messages:
            content = m["content"]
            if m["role"] == "user" and "TÍTULO:" in content and "PROBLEMA / OPORTUNIDADE:" in content:
                continue
            if m["role"] == "user":
                self.chat.insert("end", "VOCÊ\n", "user_head")
            else:
                self.chat.insert("end", "COPILOT\n", "assistant_head")
            self.chat.insert("end", content + "\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _estimate_evidence_count(self, text):
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if not text.strip(): return 0
        bullets = [x for x in lines if x.startswith(("-", "•", "*", "1.", "2.", "3."))]
        if bullets: return len(bullets)
        return max(1, min(9, len([s for s in text.replace(";", ".").split(".") if len(s.strip()) > 12])))

    def update_dashboard(self):
        context = self.context_text.get("1.0", "end").strip() if hasattr(self, "context_text") else ""
        evidence = self.evidence_text.get("1.0", "end").strip() if hasattr(self, "evidence_text") else ""
        rounds = sum(1 for m in self.messages if m.get("role") == "assistant")
        evidence_count = self._estimate_evidence_count(evidence)
        problem_score = 0
        if len(context) >= 40: problem_score += 35
        if len(context) >= 120: problem_score += 25
        if evidence_count: problem_score += 20
        if rounds >= 2: problem_score += 20
        problem_score = min(problem_score, 100)

        if rounds == 0: stage = "Inicial"
        elif rounds < 3: stage = "Explorando"
        elif rounds < 6: stage = "Validando"
        else: stage = "Maturando"

        self.problem_card.config(text=f"{problem_score}%")
        self.evidence_card.config(text=str(evidence_count))
        self.learning_card.config(text=str(rounds))
        self.stage_card.config(text=stage)
        self.round_label.config(text=f"{rounds} rodada{'s' if rounds != 1 else ''}")

    def save_current(self, silent=False):
        title = self.title_var.get().strip() or "Discovery sem título"
        context = self.context_text.get("1.0", "end").strip()
        evidence = self.evidence_text.get("1.0", "end").strip()
        payload = save_discovery(title, context, evidence, self.messages, discovery_id=self.discovery_id)
        self.discovery_id = payload["id"]
        self.refresh_history()
        if not silent:
            self.status_chip.config(text="● Salvo", bg=SUCCESS_BG, fg=SUCCESS)
            self.after(1600, lambda: self.status_chip.config(text="● Pronto", bg=SUCCESS_BG, fg=SUCCESS))

    def refresh_history(self):
        self.history.delete(0, "end")
        self.history_items = list_discoveries()
        for item in self.history_items:
            self.history.insert("end", "  " + (item.get("title") or item.get("id"))[:31])

    def load_selected(self, event=None):
        sel = self.history.curselection()
        if not sel: return
        item = self.history_items[sel[0]]
        loaded = load_discovery(item["id"])
        if not loaded: return
        self.discovery_id = loaded.get("id")
        self.title_var.set(loaded.get("title", ""))
        self.context_text.delete("1.0", "end"); self.context_text.insert("1.0", loaded.get("context", ""))
        self.evidence_text.delete("1.0", "end"); self.evidence_text.insert("1.0", loaded.get("evidence", ""))
        self.messages = loaded.get("messages", [])
        self.ost_data = None
        self.render_chat()
        self.update_dashboard()
        self._draw_empty_tree("Clique em “Atualizar mapa” para reconstruir a árvore deste discovery.")
        self.switch_view("workspace")

    def new_discovery(self):
        if self.messages or self.context_text.get("1.0", "end").strip():
            if not messagebox.askyesno("Novo discovery", "Começar um novo discovery? O atual pode ser salvo antes."):
                return
        self.discovery_id = None
        self.messages = []
        self.ost_data = None
        self.meeting_seed = ""
        self.title_var.set("")
        self.context_text.delete("1.0", "end")
        self.evidence_text.delete("1.0", "end")
        self.doc_text.delete("1.0", "end")
        self.render_chat()
        self.update_dashboard()
        self._draw_empty_tree()
        self.next_step_var.set("Próximo passo aparecerá aqui após atualizar o mapa.")
        self.switch_view("workspace")

    def generate_document(self, kind):
        if self.busy: return
        if not self.messages:
            messagebox.showinfo("Sem discovery", "Inicie ou carregue um discovery primeiro.")
            return
        prompt = build_brief_prompt(self.messages) if kind == "brief" else build_prd_prompt(self.messages)
        self._api_call(prompt, lambda result: self._show_document(result, kind))

    def _show_document(self, result, kind):
        self.doc_text.delete("1.0", "end")
        self.doc_text.insert("1.0", result)
        self.switch_view("docs")
        self.status_chip.config(text="● Documento gerado", bg=SUCCESS_BG, fg=SUCCESS)

    def export_document(self):
        content = self.doc_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Nada para exportar", "Gere um Brief ou PRD primeiro.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md"), ("Texto", "*.txt")])
        if path:
            Path(path).write_text(content, encoding="utf-8")
            self.status_chip.config(text="● Exportado", bg=SUCCESS_BG, fg=SUCCESS)

    def generate_ost(self):
        if self.busy: return
        if not self.messages:
            messagebox.showinfo("Sem discovery", "Inicie ou carregue um discovery primeiro.")
            return
        prompt = build_ost_prompt(self.messages)
        self._api_call(prompt, self._receive_ost, system_prompt="Responda estritamente no formato solicitado e não invente informações.")

    def _receive_ost(self, result):
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].lstrip()
            self.ost_data = json.loads(cleaned)
        except Exception:
            messagebox.showerror("Mapa inválido", "A IA não retornou JSON válido. Tente atualizar novamente.")
            return
        self._update_risks()
        self._draw_ost()
        self.next_step_var.set(self.ost_data.get("next_step") or "Evidência insuficiente para sugerir próximo passo.")
        self.switch_view("tree")

    def _risk_style(self, value):
        v = (value or "incerto").lower()
        if v == "baixo": return SUCCESS, SUCCESS_BG
        if v == "médio": return WARN, WARN_BG
        if v == "alto": return DANGER, DANGER_BG
        return MUTED, "#F2F4F7"

    def _update_risks(self):
        risks = (self.ost_data or {}).get("risks", {})
        for key, label in self.risk_labels.items():
            raw = risks.get(key, "incerto")
            fg, bg = self._risk_style(raw)
            label.config(text=str(raw).capitalize(), fg=fg, bg=bg)
            label.master.config(bg=bg)
            for child in label.master.winfo_children():
                if child is not label:
                    child.config(bg=bg)

    def _draw_empty_tree(self, text="Inicie um discovery e clique em “Atualizar mapa” para visualizar a árvore."):
        if not hasattr(self, "tree_canvas"): return
        self.tree_canvas.delete("all")
        self.tree_canvas.create_text(470, 230, text=text, fill=MUTED, font=("Segoe UI", 11), width=620, justify="center")
        self.tree_canvas.configure(scrollregion=(0, 0, 940, 460))

    def _wrap(self, text, limit=26):
        words = str(text or "").split()
        lines, line = [], []
        for word in words:
            if len(" ".join(line + [word])) > limit and line:
                lines.append(" ".join(line)); line = [word]
            else:
                line.append(word)
        if line: lines.append(" ".join(line))
        return "\n".join(lines[:5])

    def _node(self, x, y, w, h, text, fill, outline, title=None):
        self.tree_canvas.create_rectangle(x, y, x+w, y+h, fill=fill, outline=outline, width=1)
        if title:
            self.tree_canvas.create_text(x+10, y+10, text=title.upper(), anchor="nw", fill=MUTED, font=("Segoe UI", 7, "bold"))
            ty = y+28
        else:
            ty = y+h/2
        self.tree_canvas.create_text(x+w/2, ty if title else ty, text=self._wrap(text, 28), anchor="n" if title else "center", fill=TEXT, font=("Segoe UI", 9, "bold" if title else "normal"), width=w-18, justify="center")
        return (x, y, x+w, y+h)

    def _connect(self, a, b):
        ax = a[2]; ay = (a[1]+a[3])/2
        bx = b[0]; by = (b[1]+b[3])/2
        mid = (ax+bx)/2
        self.tree_canvas.create_line(ax, ay, mid, ay, mid, by, bx, by, fill="#CBD5E1", width=2, smooth=False)

    def _draw_ost(self):
        self.tree_canvas.delete("all")
        data = self.ost_data or {}
        problem = data.get("problem") or "Problema não definido"
        opportunities = data.get("opportunities") or []

        x_problem, x_opp, x_sol, x_exp = 30, 300, 590, 865
        gap_y = 22
        node_h = 88
        node_w = 220
        current_y = 30

        # Estimate height for each opportunity branch.
        branch_specs = []
        for opp in opportunities[:4]:
            sols = opp.get("solutions") or []
            rows = max(1, sum(max(1, len((s.get("experiments") or []))) for s in sols) if sols else 1)
            branch_h = max(node_h, rows * (node_h + gap_y))
            branch_specs.append((opp, branch_h))
        total_h = max(420, sum(h for _, h in branch_specs) + max(0, len(branch_specs)-1)*25 + 50)
        problem_y = total_h/2 - node_h/2
        pbox = self._node(x_problem, problem_y, node_w, node_h, problem, ACCENT_LIGHT, "#C7D2FE", "Problema")

        if not opportunities:
            self.tree_canvas.create_text(420, problem_y+120, text="Nenhuma oportunidade suficientemente clara ainda.", fill=MUTED, font=("Segoe UI", 10))
            self.tree_canvas.configure(scrollregion=(0,0,1150,total_h))
            return

        y = 30
        for opp, branch_h in branch_specs:
            oy = y + branch_h/2 - node_h/2
            level = opp.get("evidence_level", "insuficiente")
            label_text = f"{opp.get('text','')}\n\nEvidência: {level}"
            obox = self._node(x_opp, oy, node_w, node_h, label_text, CYAN_BG, "#A5F3FC", "Oportunidade")
            self._connect(pbox, obox)

            sols = opp.get("solutions") or []
            if not sols:
                y += branch_h + 25
                continue

            row_y = y
            for sol in sols[:3]:
                exps = (sol.get("experiments") or [])[:2]
                used_rows = max(1, len(exps))
                sy = row_y + used_rows*(node_h+gap_y)/2 - node_h/2 - gap_y/2
                sbox = self._node(x_sol, sy, node_w, node_h, sol.get("text") or "Hipótese de solução", WARN_BG, "#FDE68A", "Solução")
                self._connect(obox, sbox)
                if exps:
                    for exp in exps:
                        ebox = self._node(x_exp, row_y, node_w, node_h, exp, SUCCESS_BG, "#A7F3D0", "Experimento")
                        self._connect(sbox, ebox)
                        row_y += node_h + gap_y
                else:
                    row_y += node_h + gap_y
            y += branch_h + 25

        self.tree_canvas.configure(scrollregion=(0, 0, 1130, max(total_h, y+30)))


if __name__ == "__main__":
    App().mainloop()
