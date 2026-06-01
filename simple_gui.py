#!/usr/bin/env python3
"""简单启动脚本 - 直接启动主界面"""

import tkinter as tk
from tkinter import ttk, messagebox

# 静态测试数据
MOCK_CANDIDATES = [
    {"content": "理解您的顾虑，价格确实是家长最关心的问题之一。我们这边先不催您定，如果您方便的话，我把孩子试听时的课堂表现整理发给您。", "style": "温和共情型"},
    {"content": "这个价格包含了全套课程服务。建议先安排一节深度试听课，让孩子完整体验教学模式。", "style": "专业自信型"},
    {"content": "建议先带孩子体验一周正课，感受教学氛围和老师风格，再谈报名事宜。", "style": "行动推动型"},
    {"content": "如果您担心孩子跟不上，我可以先给您发一份分层学习安排，方便您评估是否适合。", "style": "信息补充型"},
    {"content": "我们也可以先从一次轻量试听开始，边体验边决定，不着急一次性定下来。", "style": "柔和推进型"},
]

SCENES = ["问价格", "问课程", "问师资", "问时间"]
STAGES = ["初次接触", "试听前", "试听后", "报名前"]

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("快捷回复助手 - 访客模式")
        self.root.geometry("600x400")
        
        # 输入框
        tk.Label(self.root, text="家长问题：").pack(pady=5)
        self.query = tk.Entry(self.root, width=50)
        self.query.pack(pady=5)
        
        # 场景选择
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        tk.Label(frame, text="场景：").pack(side=tk.LEFT)
        self.scene = ttk.Combobox(frame, values=SCENES, state="readonly", width=10)
        self.scene.current(0)
        self.scene.pack(side=tk.LEFT, padx=5)
        tk.Label(frame, text="阶段：").pack(side=tk.LEFT)
        self.stage = ttk.Combobox(frame, values=STAGES, state="readonly", width=10)
        self.stage.current(0)
        self.stage.pack(side=tk.LEFT, padx=5)
        
        # 生成按钮
        tk.Button(self.root, text="生成回复", command=self.generate, width=20).pack(pady=10)
        
        # 结果显示
        tk.Label(self.root, text="候选回复：").pack(pady=5)
        self.result = tk.Text(self.root, height=12, width=60)
        self.result.pack(pady=5)
        
        # 复制按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        for idx in range(len(MOCK_CANDIDATES)):
            tk.Button(btn_frame, text=f"复制候选{idx + 1}", command=lambda i=idx: self.copy(i)).pack(side=tk.LEFT, padx=5)
        
        # 状态
        self.status = tk.Label(self.root, text="访客模式 - 使用测试数据")
        self.status.pack(pady=5)
    
    def generate(self):
        query = self.query.get()
        if not query:
            messagebox.showwarning("提示", "请输入问题")
            return
        
        self.result.delete('1.0', tk.END)
        for i, c in enumerate(MOCK_CANDIDATES):
            self.result.insert(tk.END, f"【候选{i + 1}】（{c['style']}）\n{c['content']}\n\n")
        self.status.config(text=f"已生成{len(MOCK_CANDIDATES)}条候选回复")
    
    def copy(self, idx):
        if idx < len(MOCK_CANDIDATES):
            self.root.clipboard_clear()
            self.root.clipboard_append(MOCK_CANDIDATES[idx]['content'])
            self.status.config(text=f"已复制候选{idx+1}")
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = App()
    app.run()
