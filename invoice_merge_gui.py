"""
发票合并助手 - 主GUI应用程序
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import List, Optional
import fitz
from PIL import Image, ImageTk

from core.models import InvoiceItem, LayoutConfig, CropConfig
from core.pdf_engine import PDFEngine
from core.cropper import Cropper
from core.merger import MergeExporter
from core.tasks import TaskRunner
from storage.persist import ConfigPersistence


class InvoiceMergeApp:
    """主应用程序窗口"""

    def __init__(self, root: tk.Tk):
        """初始化应用程序"""
        self.root = root
        self.root.title("发票合并助手")
        self.root.geometry("1000x700")

        # 数据
        self.items: List[InvoiceItem] = []
        self.selected_index: Optional[int] = None
        self.current_preview_image: Optional[ImageTk.PhotoImage] = None
        self.preview_mode: str = "single"  # "single" 或 "merged"

        # 配置
        self.layout_config = LayoutConfig()
        self.crop_config = CropConfig()

        # 组件
        self.engine = PDFEngine()
        self.cropper = Cropper(self.crop_config)
        self.task_runner = TaskRunner()

        # 构建UI
        self._build_ui()

    def _build_ui(self):
        """构建用户界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 左侧面板 - 文件列表
        self._build_file_list_panel(main_frame)

        # 右侧面板 - 预览和控制
        self._build_right_panel(main_frame)

    def _build_file_list_panel(self, parent):
        """构建文件列表面板"""
        left_frame = ttk.Frame(parent)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 3))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # 标题
        ttk.Label(left_frame, text="发票文件", font=("", 10, "bold")).pack(pady=(0, 3))

        # 列表框和滚动条
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self._on_file_select)
        scrollbar.config(command=self.file_listbox.yview)

        # 按钮
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=(3, 0), fill=tk.X)

        ttk.Button(btn_frame, text="添加", command=self._add_files, width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="删除", command=self._remove_file, width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="上移", command=self._move_up, width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_frame, text="下移", command=self._move_down, width=6).pack(side=tk.LEFT, padx=1)

    def _build_right_panel(self, parent):
        """构建右侧面板"""
        right_frame = ttk.Frame(parent)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(3, 0))
        parent.columnconfigure(1, weight=2)

        # 预览标题和模式切换
        preview_header = ttk.Frame(right_frame)
        preview_header.pack(fill=tk.X, pady=(0, 3))

        ttk.Label(preview_header, text="预览", font=("", 10, "bold")).pack(side=tk.LEFT)

        mode_frame = ttk.Frame(preview_header)
        mode_frame.pack(side=tk.RIGHT)
        ttk.Button(mode_frame, text="单页", command=lambda: self._switch_preview("single"), width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(mode_frame, text="合并", command=lambda: self._switch_preview("merged"), width=6).pack(side=tk.LEFT, padx=1)

        # 预览画布（带滚动条）
        canvas_frame = ttk.Frame(right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 画布
        self.preview_canvas = tk.Canvas(
            canvas_frame,
            width=600,
            height=400,
            bg="gray90",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 配置滚动条
        v_scrollbar.config(command=self.preview_canvas.yview)
        h_scrollbar.config(command=self.preview_canvas.xview)

        # 控制面板
        ctrl_frame = ttk.LabelFrame(right_frame, text="设置", padding="5")
        ctrl_frame.pack(fill=tk.X, pady=(5, 0))

        # 裁切模式
        ttk.Label(ctrl_frame, text="裁切:").grid(row=0, column=0, sticky=tk.W, padx=(0,3))
        self.crop_mode_var = tk.StringVar(value="auto")
        ttk.Radiobutton(ctrl_frame, text="自动", variable=self.crop_mode_var, value="auto").grid(row=0, column=1)
        ttk.Radiobutton(ctrl_frame, text="上半", variable=self.crop_mode_var, value="top").grid(row=0, column=2)
        ttk.Radiobutton(ctrl_frame, text="手动", variable=self.crop_mode_var, value="manual").grid(row=0, column=3)

        # 布局设置
        ttk.Label(ctrl_frame, text="行:").grid(row=1, column=0, sticky=tk.W, pady=(3, 0), padx=(0,3))
        self.rows_var = tk.IntVar(value=2)
        ttk.Spinbox(ctrl_frame, from_=1, to=5, textvariable=self.rows_var, width=8, command=self._on_layout_change).grid(row=1, column=1, pady=(3, 0))

        ttk.Label(ctrl_frame, text="列:").grid(row=1, column=2, sticky=tk.W, pady=(3, 0), padx=(5,3))
        self.cols_var = tk.IntVar(value=2)
        ttk.Spinbox(ctrl_frame, from_=1, to=5, textvariable=self.cols_var, width=8, command=self._on_layout_change).grid(row=1, column=3, pady=(3, 0))

        # 导出按钮
        ttk.Button(ctrl_frame, text="导出PDF", command=self._export_pdf).grid(row=2, column=0, columnspan=4, pady=(5, 0), sticky=(tk.W, tk.E))

    def _add_files(self):
        """Add PDF files to the list"""
        files = filedialog.askopenfilenames(
            title="Select PDF Files",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        for file_path in files:
            item = InvoiceItem(path=file_path)
            self.items.append(item)
            self.file_listbox.insert(tk.END, Path(file_path).name)

    def _remove_file(self):
        """Remove selected file"""
        selection = self.file_listbox.curselection()
        if selection:
            idx = selection[0]
            self.items.pop(idx)
            self.file_listbox.delete(idx)

    def _move_up(self):
        """Move selected file up"""
        selection = self.file_listbox.curselection()
        if selection and selection[0] > 0:
            idx = selection[0]
            self.items[idx], self.items[idx-1] = self.items[idx-1], self.items[idx]
            self._refresh_list()
            self.file_listbox.selection_set(idx-1)

    def _move_down(self):
        """Move selected file down"""
        selection = self.file_listbox.curselection()
        if selection and selection[0] < len(self.items) - 1:
            idx = selection[0]
            self.items[idx], self.items[idx+1] = self.items[idx+1], self.items[idx]
            self._refresh_list()
            self.file_listbox.selection_set(idx+1)

    def _refresh_list(self):
        """Refresh the file listbox"""
        self.file_listbox.delete(0, tk.END)
        for item in self.items:
            self.file_listbox.insert(tk.END, Path(item.path).name)

    def _on_file_select(self, event):
        """Handle file selection"""
        selection = self.file_listbox.curselection()
        if selection:
            self.selected_index = selection[0]
            self._update_preview()

    def _update_preview(self):
        """更新预览画布"""
        if self.preview_mode == "single":
            self._show_single_preview()
        else:
            self._show_merged_preview()

    def _show_single_preview(self):
        """显示单页预览"""
        if self.selected_index is None or self.selected_index >= len(self.items):
            return

        item = self.items[self.selected_index]
        try:
            doc = self.engine.open_document(item.path)
            page = self.engine.get_page(doc, item.page_index)
            img = self.engine.render_thumbnail(page, 600, 400)
            self.current_preview_image = ImageTk.PhotoImage(img)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.current_preview_image)

            # 更新滚动区域
            self.preview_canvas.config(scrollregion=(0, 0, img.width, img.height))
            doc.close()
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {str(e)}")

    def _show_merged_preview(self):
        """显示合并预览"""
        if not self.items:
            self.preview_canvas.delete("all")
            self.preview_canvas.config(scrollregion=(0, 0, 0, 0))
            return

        try:
            # 更新布局配置
            self.layout_config.rows = self.rows_var.get()
            self.layout_config.cols = self.cols_var.get()

            # 生成预览
            exporter = MergeExporter(self.layout_config)
            preview_doc = exporter.generate_preview_page(self.items)

            if preview_doc is None:
                messagebox.showerror("错误", "生成预览失败")
                return

            # 渲染预览
            page = preview_doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.current_preview_image = ImageTk.PhotoImage(img)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.current_preview_image)

            # 更新滚动区域
            self.preview_canvas.config(scrollregion=(0, 0, img.width, img.height))
            preview_doc.close()

        except Exception as e:
            messagebox.showerror("错误", f"合并预览失败: {str(e)}")

    def _switch_preview(self, mode: str):
        """切换预览模式"""
        self.preview_mode = mode
        self._update_preview()

    def _on_layout_change(self):
        """布局变化时更新预览"""
        if self.preview_mode == "merged":
            self._update_preview()

    def _export_pdf(self):
        """导出合并的PDF"""
        if not self.items:
            messagebox.showwarning("警告", "没有文件可导出")
            return

        output_path = filedialog.asksaveasfilename(
            title="保存合并PDF",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if not output_path:
            return

        # 更新布局配置
        self.layout_config.rows = self.rows_var.get()
        self.layout_config.cols = self.cols_var.get()

        # 创建导出器并运行合并
        exporter = MergeExporter(self.layout_config)
        try:
            success = exporter.merge_to_pdf(self.items, output_path)
            if success:
                messagebox.showinfo("成功", "PDF导出成功！")
            else:
                messagebox.showerror("错误", "PDF导出失败")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")


def main():
    """主入口"""
    root = tk.Tk()
    app = InvoiceMergeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
