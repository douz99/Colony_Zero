"""Styled, scrollable game readers and confirmations; never system message boxes."""
import tkinter as tk

BG='#101f30'
PANEL='#1c3448'
TEXT='#e7eff5'
ACCENT='#83ded0'


class GameWindow(tk.Toplevel):
    def __init__(self, title, message, parent, close_label='Close', confirm_label=None,
                 cancel_label='Back', font_family='Segoe UI'):
        super().__init__(parent, bg=BG)
        self.result=False
        self.parent=parent
        self.title(title)
        self.transient(parent)
        self.minsize(420,300)
        width=min(760,max(420,self.winfo_screenwidth()-80))
        height=min(580,max(300,self.winfo_screenheight()-100))
        x=max(0,min(parent.winfo_rootx()+80,self.winfo_screenwidth()-width-20))
        y=max(0,min(parent.winfo_rooty()+60,self.winfo_screenheight()-height-40))
        self.geometry(f'{width}x{height}+{x}+{y}')
        tk.Label(self,text=title,bg=BG,fg=ACCENT,font=(font_family,16,'bold'),
                 anchor='w',padx=20,pady=16).pack(fill='x')
        footer=tk.Frame(self,bg=BG,padx=16,pady=12)
        footer.pack(side='bottom',fill='x')
        self.close_button=tk.Button(footer,text=cancel_label if confirm_label else close_label,
                    command=self.close,bg=PANEL,fg=TEXT,relief='flat',padx=18,pady=8)
        self.close_button.pack(side='right')
        self.confirm_button=None
        if confirm_label:
            self.confirm_button=tk.Button(footer,text=confirm_label,command=self.accept,
                bg='#286e68',fg='white',relief='flat',padx=18,pady=8)
            self.confirm_button.pack(side='right',padx=(0,8))
        content=tk.Frame(self,bg=PANEL)
        content.pack(fill='both',expand=True,padx=18)
        scroll=tk.Scrollbar(content)
        scroll.pack(side='right',fill='y')
        self.body=tk.Text(content,bg=PANEL,fg=TEXT,insertbackground=TEXT,relief='flat',
                 wrap='word',padx=16,pady=12,font=(font_family,11),yscrollcommand=scroll.set)
        self.body.pack(fill='both',expand=True)
        scroll.configure(command=self.body.yview)
        self.set_message(message)
        self.bind('<Escape>',lambda event:self.close())
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.close_button.focus_set()

    def set_message(self,message):
        self.body.configure(state='normal')
        self.body.delete('1.0','end')
        self.body.insert('end',message)
        self.body.configure(state='disabled')

    def accept(self):
        self.result=True
        self.close()

    def close(self):
        if self.winfo_exists():
            try:self.grab_release()
            except tk.TclError:pass
            self.destroy()
        if self.parent.winfo_exists():self.parent.focus_set()


def show_info(title,message,*,parent,close_label='Close',font_family='Segoe UI'):
    readers=getattr(parent,'_colony_readers',{})
    parent._colony_readers=readers
    current=readers.get(title)
    if current is not None and current.winfo_exists():
        current.set_message(message);current.lift();return current
    reader=GameWindow(title,message,parent,close_label=close_label,font_family=font_family)
    readers[title]=reader
    return reader


def ask_yes_no(title,message,*,parent,confirm_label='Confirm',cancel_label='Back',font_family='Segoe UI'):
    window=GameWindow(title,message,parent,confirm_label=confirm_label,
                      cancel_label=cancel_label,font_family=font_family)
    window.wait_visibility()
    window.grab_set()
    parent.wait_window(window)
    return window.result


def close_readers(parent):
    for window in getattr(parent,'_colony_readers',{}).values():
        if window.winfo_exists():window.close()
    parent._colony_readers={}


class HelpTip:
    """Mouse and keyboard explanation; no action, resource or simulation changes."""
    def __init__(self,widget,text):
        self.widget=widget;self.text=text;self.job=None;self.window=None
        for event in ('<Enter>','<FocusIn>'):widget.bind(event,self.queue,add='+')
        for event in ('<Leave>','<FocusOut>','<ButtonPress>'):widget.bind(event,self.dismiss,add='+')

    def queue(self,event=None):
        self.dismiss()
        self.job=self.widget.after(250,self.show)

    def show(self):
        self.job=None
        if not self.widget.winfo_exists():return
        self.window=tk.Toplevel(self.widget,bg=PANEL)
        self.window.overrideredirect(True)
        label=tk.Label(self.window,text=self.text(),bg=PANEL,fg=TEXT,padx=12,pady=10,
                       justify='left',wraplength=380,font=('Segoe UI',10))
        label.pack()
        self.window.update_idletasks()
        x=max(0,min(self.widget.winfo_rootx()-180,self.widget.winfo_screenwidth()-self.window.winfo_width()-20))
        y=max(0,self.widget.winfo_rooty()-self.window.winfo_height()-8)
        self.window.geometry(f'+{x}+{y}')

    def dismiss(self,event=None):
        if self.job is not None:self.widget.after_cancel(self.job);self.job=None
        if self.window is not None:
            self.window.destroy();self.window=None
