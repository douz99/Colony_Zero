"""Small Tk widget adapters retaining English source text for live retranslation."""

import tkinter as tk
from tkinter import font as tkfont


class LocalizedText:
    def __init__(self, master, translator, **options):
        self.translator = translator
        self.source_text = options.get("text", "")
        options["text"] = translator(self.source_text)
        super().__init__(master, **options)
        self.original_font = self.cget("font")

    def configure(self, cnf=None, **options):
        if isinstance(cnf, dict):
            options = {**cnf, **options}
            cnf = None
        if "text" in options:
            self.source_text = options["text"]
            options["text"] = self.translator(self.source_text)
        return super().configure(cnf, **options)

    config = configure

    def retranslate(self):
        super().configure(text=self.translator(self.source_text))

    def set_font_family(self, family=None):
        if family is None:
            super().configure(font=self.original_font)
            return
        original = tkfont.Font(root=self, font=self.original_font).actual()
        styles = tuple(name for name, enabled in (("bold", original["weight"] == "bold"),
                                                  ("italic", original["slant"] == "italic")) if enabled)
        super().configure(font=(family, original["size"], *styles))


class LocalizedLabel(LocalizedText, tk.Label):
    pass


class LocalizedButton(LocalizedText, tk.Button):
    pass


class LocalizedRadio(LocalizedText, tk.Radiobutton):
    pass
