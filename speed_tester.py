import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import requests
import time

# 初始 CDN 节点列表，包含分类
NODES = [
    {"node": "gcore.jsdelivr.net", "description": "Gcore 节点", "availability": "高", "category": "GitHub CDN"},
    {"node": "testingcf.jsdelivr.net", "description": "Cloudflare 节点", "availability": "高", "category": "GitHub CDN"},
    {"node": "quantil.jsdelivr.net", "description": "Quantil 节点", "availability": "一般", "category": "GitHub CDN"},
    {"node": "fastly.jsdelivr.net", "description": "Fastly 节点", "availability": "一般", "category": "GitHub CDN"},
    {"node": "originfastly.jsdelivr.net", "description": "Fastly 节点", "availability": "低", "category": "GitHub CDN"},
    {"node": "test1.jsdelivr.net", "description": "Cloudflare 节点", "availability": "低", "category": "GitHub CDN"},
    {"node": "cdn.jsdelivr.net", "description": "通用节点", "availability": "低", "category": "GitHub CDN"},
    # 第三方节点
    {"node": "jsd.cdn.zzko.cn", "description": "国内CDN", "availability": "未知", "category": "Other CDN"},
    {"node": "jsd.onmicrosoft.cn", "description": "国内CDN", "availability": "未知", "category": "Other CDN"},
    {"node": "jsdelivr.b-cdn.net", "description": "台湾CDN", "availability": "未知", "category": "Other CDN"},
    {"node": "cdn.jsdelivr.us", "description": "美国CDN", "availability": "未知", "category": "Other CDN"},
]

class SpeedTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("jsDelivr 节点速度测试工具")
        self.create_widgets()
        self.lock = threading.Lock()
        self.testing_in_progress = False  # 防止重复测试
        self.sort_by = None  # 当前排序列
        self.sort_ascending = True  # 排序顺序

    def create_widgets(self):
        # 顶部框架：输入和测试按钮
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="相对路径:").pack(side=tk.LEFT, padx=(0, 5))
        self.path_var = tk.StringVar()
        self.entry = ttk.Entry(top_frame, textvariable=self.path_var, width=50)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.insert(0, "gh/huanxueshengmou/picture-host/bil.svg")

        self.test_button = ttk.Button(top_frame, text="测试速度", command=self.start_test)
        self.test_button.pack(side=tk.LEFT)

        # 复选框框架
        checkbox_frame = ttk.Frame(self.root, padding="10")
        checkbox_frame.pack(fill=tk.X)

        self.github_var = tk.BooleanVar(value=True)
        self.other_var = tk.BooleanVar(value=True)
        self.github_cb = ttk.Checkbutton(checkbox_frame, text="测试 GitHub CDN", variable=self.github_var)
        self.github_cb.pack(side=tk.LEFT, padx=(0, 10))
        self.other_cb = ttk.Checkbutton(checkbox_frame, text="测试其他 CDN", variable=self.other_var)
        self.other_cb.pack(side=tk.LEFT, padx=(0, 10))

        # 管理 CDN 节点框架
        manage_frame = ttk.LabelFrame(self.root, text="管理 CDN 节点", padding="10")
        manage_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(manage_frame, text="节点:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.E)
        self.new_node_var = tk.StringVar()
        self.new_node_entry = ttk.Entry(manage_frame, textvariable=self.new_node_var, width=30)
        self.new_node_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(manage_frame, text="描述:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.E)
        self.new_desc_var = tk.StringVar()
        self.new_desc_entry = ttk.Entry(manage_frame, textvariable=self.new_desc_var, width=30)
        self.new_desc_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(manage_frame, text="可用性:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.E)
        self.new_availability_var = tk.StringVar()
        self.availability_combo = ttk.Combobox(manage_frame, textvariable=self.new_availability_var, state='readonly')
        self.availability_combo['values'] = ("高", "一般", "低", "未知")
        self.availability_combo.current(3)  # 默认 "未知"
        self.availability_combo.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(manage_frame, text="分类:").grid(row=1, column=2, padx=5, pady=2, sticky=tk.E)
        self.new_category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(manage_frame, textvariable=self.new_category_var, state='readonly')
        self.category_combo['values'] = ("GitHub CDN", "Other CDN")
        self.category_combo.current(0)
        self.category_combo.grid(row=1, column=3, padx=5, pady=2)

        self.add_button = ttk.Button(manage_frame, text="添加节点", command=self.add_node)
        self.add_button.grid(row=2, column=1, padx=5, pady=5)

        self.delete_button = ttk.Button(manage_frame, text="删除选中节点", command=self.delete_node)
        self.delete_button.grid(row=2, column=3, padx=5, pady=5)

        # 排序按钮框架
        sort_frame = ttk.Frame(self.root, padding="10")
        sort_frame.pack(fill=tk.X)

        self.sort_button = ttk.Button(sort_frame, text="排序 ↑", command=self.sort_results)
        self.sort_button.pack(side=tk.LEFT)

        # 结果显示 Treeview
        self.tree = ttk.Treeview(
            self.root,
            columns=("Node", "Description", "Availability", "Speed (ms)", "Status"),
            show="headings",
        )
        self.tree.heading("Node", text="节点")
        self.tree.heading("Description", text="描述")
        self.tree.heading("Availability", text="可用性")
        self.tree.heading("Speed (ms)", text="速度 (毫秒)")
        self.tree.heading("Status", text="状态")
        self.tree.column("Node", width=150)
        self.tree.column("Description", width=150)
        self.tree.column("Availability", width=100)
        self.tree.column("Speed (ms)", width=100, anchor="center")
        self.tree.column("Status", width=100, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 滚动条
        scrollbar = ttk.Scrollbar(self.tree, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def add_node(self):
        node = self.new_node_var.get().strip()
        desc = self.new_desc_var.get().strip()
        availability = self.new_availability_var.get().strip()
        category = self.new_category_var.get().strip()

        if not node or not desc or not availability or not category:
            messagebox.showwarning("输入错误", "请填写所有字段以添加新的 CDN 节点。")
            return

        # 检查重复节点
        for existing in NODES:
            if existing["node"] == node:
                messagebox.showwarning("重复节点", "该节点已存在。")
                return

        # 添加到 NODES
        new_node = {
            "node": node,
            "description": desc,
            "availability": availability,
            "category": category
        }
        NODES.append(new_node)
        messagebox.showinfo("成功", f"节点 {node} 已添加。")

        # 清空输入字段
        self.new_node_var.set("")
        self.new_desc_var.set("")
        self.availability_combo.current(3)  # 重置为 "未知"
        self.category_combo.current(0)

    def delete_node(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("未选择", "请先选择要删除的节点。")
            return

        # 获取选中节点
        item = self.tree.item(selected[0])
        node = item['values'][0]

        # 确认删除
        confirm = messagebox.askyesno("确认删除", f"是否确认删除节点 {node}？")
        if not confirm:
            return

        # 从 NODES 中移除
        global NODES
        NODES = [n for n in NODES if n["node"] != node]

        # 从 Treeview 中移除
        self.tree.delete(selected[0])
        messagebox.showinfo("已删除", f"节点 {node} 已被删除。")

    def start_test(self):
        if self.testing_in_progress:
            messagebox.showwarning("正在测试", "请等待当前测试完成后再开始新测试。")
            return

        relative_path = self.path_var.get().strip()
        if not relative_path:
            messagebox.showwarning("输入错误", "请输入有效的相对路径。")
            return

        # 根据复选框选择确定测试的分类
        selected_categories = []
        if self.github_var.get():
            selected_categories.append("GitHub CDN")
        if self.other_var.get():
            selected_categories.append("Other CDN")
        if not selected_categories:
            messagebox.showwarning("选择错误", "请至少选择一个 CDN 类型进行测试。")
            return

        # 根据选择的分类过滤节点
        self.test_nodes = [node for node in NODES if node["category"] in selected_categories]
        if not self.test_nodes:
            messagebox.showwarning("无节点", "根据选择的类型，没有可测试的 CDN 节点。")
            return

        # 清空之前的结果
        self.clear_results()

        # 禁用测试按钮
        self.test_button.config(state=tk.DISABLED)
        self.testing_in_progress = True

        # 在 Treeview 中插入待测试的节点
        for node_info in self.test_nodes:
            self.tree.insert(
                "", tk.END,
                values=(node_info["node"], node_info["description"], node_info["availability"], "—", "待测")
            )

        # 为每个节点启动一个线程进行测试
        for node_info in self.test_nodes:
            threading.Thread(target=self.test_node_speed, args=(node_info, relative_path), daemon=True).start()

    def clear_results(self):
        # 清空 Treeview 中的所有项目
        for item in self.tree.get_children():
            self.tree.delete(item)

    def test_node_speed(self, node_info, relative_path):
        node = node_info["node"]
        url = f"https://{node}/{relative_path}"
        start_time = time.time()
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            end_time = time.time()
            speed = round((end_time - start_time) * 1000, 2)  # 毫秒
            status = "成功"
        except requests.RequestException as e:
            speed = "—"
            status = "失败"

        # 更新 Treeview 中的结果
        self.update_tree(node, speed, status)

    def update_tree(self, node, speed, status):
        with self.lock:
            for child in self.tree.get_children():
                values = self.tree.item(child)["values"]
                if values[0] == node:
                    self.tree.item(child, values=(values[0], values[1], values[2], speed, status))
                    break

        # 检查是否所有测试已完成
        all_done = True
        for child in self.tree.get_children():
            if self.tree.item(child)["values"][4] == "待测":
                all_done = False
                break

        if all_done:
            self.test_button.config(state=tk.NORMAL)
            self.testing_in_progress = False
            messagebox.showinfo("测试完成", "所有节点的速度测试已完成。")

    def sort_results(self):
        # 按速度排序，"—" 视为无穷大
        items = []
        for child in self.tree.get_children():
            values = self.tree.item(child)["values"]
            speed = values[3]
            if speed == "—":
                speed_val = float('inf')
            else:
                try:
                    speed_val = float(speed)
                except ValueError:
                    speed_val = float('inf')
            items.append((speed_val, child))

        # 切换排序顺序
        self.sort_ascending = not self.sort_ascending

        # 排序项目
        items.sort(reverse=not self.sort_ascending)

        # 重新排列 Treeview 中的项目
        for index, (speed, child) in enumerate(items):
            self.tree.move(child, '', index)

        # 更新排序按钮文本以指示排序方向
        if self.sort_ascending:
            self.sort_button.config(text="排序 ↑")
        else:
            self.sort_button.config(text="排序 ↓")

def main():
    root = tk.Tk()
    app = SpeedTesterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
