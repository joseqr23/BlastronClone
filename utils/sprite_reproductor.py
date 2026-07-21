import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk


class SpriteViewer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Visor de Sprites")
        self.geometry("700x600")

        self.sprite = None
        self.frames = []
        self.frame_actual = 0

        self.frame_w = tk.IntVar(value=60)
        self.frame_h = tk.IntVar(value=90)
        self.fps = tk.IntVar(value=6)
        self.zoom = tk.IntVar(value=4)   # Zoom (4x por defecto)

        controles = tk.Frame(self)
        controles.pack(pady=5)

        tk.Button(controles, text="Abrir Sprite", command=self.abrir).grid(row=0, column=0, padx=5)

        tk.Label(controles, text="Ancho").grid(row=0, column=1)
        tk.Entry(controles, textvariable=self.frame_w, width=5).grid(row=0, column=2)

        tk.Label(controles, text="Alto").grid(row=0, column=3)
        tk.Entry(controles, textvariable=self.frame_h, width=5).grid(row=0, column=4)

        tk.Label(controles, text="FPS").grid(row=0, column=5)
        tk.Entry(controles, textvariable=self.fps, width=5).grid(row=0, column=6)

        tk.Label(controles, text="Zoom").grid(row=0, column=7)
        tk.Entry(controles, textvariable=self.zoom, width=5).grid(row=0, column=8)

        tk.Button(controles, text="Recargar", command=self.extraer_frames).grid(row=0, column=9, padx=5)

        self.lbl = tk.Label(self)
        self.lbl.pack(expand=True)

        self.animar()

    def abrir(self):
        archivo = filedialog.askopenfilename(
            filetypes=[("Imagen", "*.png *.bmp *.jpg")]
        )

        if not archivo:
            return

        self.sprite = Image.open(archivo).convert("RGBA")
        self.extraer_frames()

    def extraer_frames(self):
        if self.sprite is None:
            return

        self.frames.clear()

        w = self.frame_w.get()
        h = self.frame_h.get()
        zoom = max(1, self.zoom.get())

        columnas = self.sprite.width // w
        filas = self.sprite.height // h

        for y in range(filas):
            for x in range(columnas):
                frame = self.sprite.crop((
                    x * w,
                    y * h,
                    (x + 1) * w,
                    (y + 1) * h
                ))

                # Aplicar zoom sin suavizado
                frame = frame.resize(
                    (w * zoom, h * zoom),
                    Image.Resampling.NEAREST
                )

                self.frames.append(ImageTk.PhotoImage(frame))

        self.frame_actual = 0

    def animar(self):
        if self.frames:
            self.lbl.configure(image=self.frames[self.frame_actual])
            self.frame_actual = (self.frame_actual + 1) % len(self.frames)

        self.after(int(1000 / max(1, self.fps.get())), self.animar)


SpriteViewer().mainloop()